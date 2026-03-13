#!/usr/bin/env python3
"""Helpers for daily tech tip generation and Slack payload formatting."""

import argparse
import json
import os
import random
import re
import textwrap
from datetime import UTC, datetime
from urllib.request import Request, urlopen

RULES_API = "https://api.github.com/repos/vercel-labs/agent-skills/contents/skills/react-best-practices/rules"
RULES_WEB_BASE = "https://github.com/vercel-labs/agent-skills/blob/main/skills/react-best-practices/rules"


def fetch_json(url: str):
    req = Request(url, headers={"User-Agent": "tech-daily-workflow"})
    with urlopen(req, timeout=20) as response:
        return json.loads(response.read().decode("utf-8"))


def fetch_text(url: str) -> str:
    req = Request(url, headers={"User-Agent": "tech-daily-workflow"})
    with urlopen(req, timeout=20) as response:
        return response.read().decode("utf-8", errors="replace")


def _extract_title(markdown_text: str, lines):
    frontmatter_title = re.search(r"^title:\s*(.+)$", markdown_text, flags=re.MULTILINE)
    if frontmatter_title:
        return frontmatter_title.group(1).strip().strip('"')

    for line in lines:
        if re.match(r"^#{1,6}\s+", line):
            return re.sub(r"^#{1,6}\s+", "", line).strip()

    return None


def _extract_bullets(lines):
    bullets = []
    in_code = False

    for line in lines:
        stripped = line.strip()
        if stripped.startswith("```"):
            in_code = not in_code
            continue
        if in_code:
            continue
        if stripped.startswith("- ") or stripped.startswith("* "):
            bullets.append(re.sub(r"^[-*]\s+", "", stripped))

    return bullets


def _extract_summary_paragraph(lines):
    cleaned = []
    in_code = False

    for line in lines:
        stripped = line.strip()
        if stripped.startswith("```"):
            in_code = not in_code
            continue
        if in_code or not stripped:
            continue
        if stripped.startswith("#") or stripped.startswith("-") or stripped.startswith("*"):
            continue
        cleaned.append(stripped)

    if not cleaned:
        return ""

    return " ".join(cleaned)


def summarize_rule(markdown_text: str):
    lines = markdown_text.splitlines()
    title = _extract_title(markdown_text, lines)
    bullets = _extract_bullets(lines)
    paragraph = _extract_summary_paragraph(lines)

    if bullets:
        summary_items = bullets[:3]
        summary = "\n".join([f"- {item}" for item in summary_items])
    elif paragraph:
        short = textwrap.shorten(paragraph, width=380, placeholder="...")
        summary = f"- {short}"
    else:
        summary = "- Follow this rule to improve readability, maintainability, and runtime behavior in React components."

    return title, summary


def _collect_example_labels(markdown_text: str):
    label_pattern = re.compile(
        r"(?im)^\s*(?:\*\*(?P<bold>[^*\n]+)\*\*|#{1,6}\s*(?P<heading>[^\n]+))\s*$"
    )

    labels = []
    for match in label_pattern.finditer(markdown_text):
        raw = (match.group("bold") or match.group("heading") or "").strip().lower()
        if "incorrect" in raw:
            labels.append((match.start(), "incorrect"))
        elif "correct" in raw:
            labels.append((match.start(), "correct"))

    labels.sort(key=lambda item: item[0])
    return labels


def _label_for_position(labels, position):
    section = ""
    for label_pos, label in labels:
        if label_pos < position:
            section = label
        else:
            break
    return section


def _collect_example_samples(markdown_text: str, labels):
    code_pattern = re.compile(r"(?s)```(?P<lang>[^\n`]*)\n(?P<code>.*?)\n```")
    samples = {"incorrect": None, "correct": None}

    for code_match in code_pattern.finditer(markdown_text):
        section = _label_for_position(labels, code_match.start())
        if section not in samples or samples[section]:
            continue

        lang = (code_match.group("lang") or "tsx").strip() or "tsx"
        code = (code_match.group("code") or "").strip()
        if not code:
            continue

        samples[section] = {"lang": lang, "code": code}
        if samples["incorrect"] and samples["correct"]:
            break

    return samples


def extract_examples(markdown_text: str):
    """Extract first Incorrect/Correct code samples from markdown headings."""
    labels = _collect_example_labels(markdown_text)
    samples = _collect_example_samples(markdown_text, labels)
    return samples["incorrect"], samples["correct"]


def _pick_rule_with_examples(rule_files):
    chosen = None

    for candidate in rule_files:
        download_url = candidate.get("download_url")
        if not download_url:
            continue

        markdown = fetch_text(download_url)
        incorrect_sample, correct_sample = extract_examples(markdown)
        has_both_samples = bool(incorrect_sample and correct_sample)

        if has_both_samples:
            return candidate, markdown, incorrect_sample, correct_sample

        if chosen is None:
            chosen = (candidate, markdown, incorrect_sample, correct_sample)

    return chosen


def get_date_context():
    now = datetime.now(UTC)
    date = os.environ.get("DATE", now.strftime("%Y-%m-%d"))
    day_name = os.environ.get("DAY_NAME", now.strftime("%A"))
    day_of_year = int(os.environ.get("DAY_OF_YEAR", now.strftime("%j")))
    return date, day_name, day_of_year


def build_tip() -> str:
    date, day_name, day_of_year = get_date_context()

    try:
        entries = fetch_json(RULES_API)
        rule_files = [
            item for item in entries
            if item.get("type") == "file" and item.get("name", "").endswith(".md")
        ]
        if not rule_files:
            raise RuntimeError("No markdown rule files found")

        random.seed(day_of_year)
        random.shuffle(rule_files)

        chosen = _pick_rule_with_examples(rule_files)
        if chosen is None:
            raise RuntimeError("Could not fetch any valid rule markdown")

        selected, markdown, incorrect_sample, correct_sample = chosen
        rule_name = selected.get("name", "unknown-rule.md")
        rule_web_url = f"{RULES_WEB_BASE}/{rule_name}"
        title, summary = summarize_rule(markdown)
        if not title:
            title = rule_name.replace(".md", "").replace("-", " ").title()

        examples = ""
        if incorrect_sample or correct_sample:
            parts = []
            if incorrect_sample:
                parts.append(
                    "Incorrect:\n"
                    f"```{incorrect_sample['lang']}\n{incorrect_sample['code']}\n```"
                )
            if correct_sample:
                parts.append(
                    "Correct:\n"
                    f"```{correct_sample['lang']}\n{correct_sample['code']}\n```"
                )
            examples = "\n\nExamples:\n" + "\n\n".join(parts)

        return (
            f"React Best Practice of the Day ({date} - {day_name})\n\n"
            f"{title}\n"
            f"Source: <{rule_web_url}|{rule_name}>\n\n"
            f"Quick summary:\n{summary}"
            f"{examples}"
        )
    except Exception as exc:
        return (
            f"React Best Practice of the Day ({date} - {day_name})\n\n"
            "Prefer small, composable components\n"
            "Quick summary:\n"
            "- Keep components focused on one responsibility.\n"
            "- Extract repeated JSX into reusable pieces.\n"
            "- Lift state only when multiple components truly share it.\n\n"
            f"Fallback reason: {exc}"
        )


def write_tip_output(tip: str):
    output_path = os.environ.get("GITHUB_OUTPUT")
    if not output_path:
        raise RuntimeError("GITHUB_OUTPUT is not set")

    with open(output_path, "a", encoding="utf-8") as output:
        output.write("tip<<EOF\n")
        output.write(tip)
        output.write("\nEOF\n")


def write_slack_payload(output_file: str):
    tip = os.environ.get("TIP", "")
    date = os.environ.get("DATE", datetime.now(UTC).strftime("%Y-%m-%d"))

    message = {
        "text": f"Daily Tech Tip - {date}",
        "blocks": [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"Daily Tech Tip - {date}",
                },
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": tip,
                },
            },
            {
                "type": "divider",
            },
            {
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": "Generated by GitHub Actions | #tech-daily",
                    }
                ],
            },
        ],
    }

    with open(output_file, "w", encoding="utf-8") as file:
        json.dump(message, file, ensure_ascii=False)


def main():
    parser = argparse.ArgumentParser(description="Tech daily workflow helpers")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("generate-tip", help="Generate tip and write to GITHUB_OUTPUT")

    payload_parser = subparsers.add_parser("format-slack", help="Write Slack JSON payload")
    payload_parser.add_argument("--output", default="/tmp/slack_message.json", help="Output JSON path")

    args = parser.parse_args()

    if args.command == "generate-tip":
        tip = build_tip()
        write_tip_output(tip)
        return

    if args.command == "format-slack":
        write_slack_payload(args.output)
        return

    raise RuntimeError(f"Unsupported command: {args.command}")


if __name__ == "__main__":
    main()
