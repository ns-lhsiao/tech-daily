#!/usr/bin/env python3
"""Helpers for daily tech tip generation and Slack payload formatting."""

import argparse
import json
import os
import random
import re
import textwrap
from datetime import datetime
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


def summarize_rule(markdown_text: str):
    lines = markdown_text.splitlines()

    title = None
    for line in lines:
        if line.startswith("# "):
            title = line[2:].strip()
            break

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

    paragraph = ""
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
    if cleaned:
        paragraph = " ".join(cleaned)

    if bullets:
        summary_items = bullets[:3]
        summary = "\n".join([f"- {item}" for item in summary_items])
    elif paragraph:
        short = textwrap.shorten(paragraph, width=380, placeholder="...")
        summary = f"- {short}"
    else:
        summary = "- Follow this rule to improve readability, maintainability, and runtime behavior in React components."

    return title, summary


def get_date_context():
    now = datetime.utcnow()
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
        selected = random.choice(rule_files)
        rule_name = selected.get("name", "unknown-rule.md")
        rule_download_url = selected.get("download_url")
        rule_web_url = f"{RULES_WEB_BASE}/{rule_name}"
        if not rule_download_url:
            raise RuntimeError("Rule download URL is missing")

        markdown = fetch_text(rule_download_url)
        title, summary = summarize_rule(markdown)
        if not title:
            title = rule_name.replace(".md", "").replace("-", " ").title()

        return (
            f"React Best Practice of the Day ({date} - {day_name})\n\n"
            f"{title}\n"
            f"Source: <{rule_web_url}|{rule_name}>\n\n"
            f"Quick summary:\n{summary}"
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
    date = os.environ.get("DATE", datetime.utcnow().strftime("%Y-%m-%d"))

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
