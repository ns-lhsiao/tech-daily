# GitHub Actions Workflows

## Daily Tech Tips Workflow

This workflow automatically generates and sends daily tech tips about web technologies and React to your Slack channel.

### Setup Instructions

#### 1. Create a Slack Webhook

1. Go to [Slack API Apps](https://api.slack.com/apps)
2. Click "Create New App" → "From scratch"
3. Name your app (e.g., "Tech Daily Bot") and select your workspace
4. Go to "Incoming Webhooks" in the left sidebar
5. Toggle "Activate Incoming Webhooks" to ON
6. Click "Add New Webhook to Workspace"
7. Select the channel where you want to receive daily tips (e.g., `#tech-daily`)
8. Copy the webhook URL (it will be a long URL starting with `https://hooks.slack.com/services/`)

#### 2. Add GitHub Secrets

1. Go to your GitHub repository
2. Navigate to **Settings** → **Secrets and variables** → **Actions**
3. Click **New repository secret**
4. Add the following secrets:

   - **Name:** `SLACK_WEBHOOK_URL`
     - **Value:** Your Slack webhook URL from step 1
   
   - **Name:** `CURSOR_API_KEY`
     - **Value:** Your Cursor API key (if you have one, otherwise the workflow will use a fallback)

#### 3. Configure Schedule (Optional)

The workflow runs daily at 9:00 AM UTC by default. To change the schedule:

1. Edit `.github/workflows/tech-daily.yaml`
2. Modify the cron expression in the `schedule` section:
   ```yaml
   schedule:
     - cron: '0 9 * * *'  # 9 AM UTC daily
   ```
   
   Cron format: `minute hour day month weekday`
   - Example: `'0 14 * * *'` = 2:00 PM UTC daily
   - Example: `'0 9 * * 1-5'` = 9:00 AM UTC, weekdays only

#### 4. Manual Trigger

You can manually trigger the workflow:
1. Go to **Actions** tab in your GitHub repository
2. Select "Daily Tech Tips" workflow
3. Click "Run workflow"

### Workflow Features

- ✅ Runs daily automatically
- ✅ Generates tech tips focused on web technologies and React
- ✅ Maximum 200 words per tip
- ✅ Formatted Slack message with date and branding
- ✅ Fallback tip if Cursor Agent fails
- ✅ Manual trigger option

### Troubleshooting

**Workflow not running:**
- Check that the schedule is correct (GitHub Actions uses UTC time)
- Verify secrets are properly configured
- Check workflow permissions in repository settings

**Slack message not received:**
- Verify `SLACK_WEBHOOK_URL` secret is correct
- Test the webhook URL manually with curl:
  ```bash
  curl -X POST -H 'Content-type: application/json' \
    --data '{"text":"Test message"}' \
    YOUR_WEBHOOK_URL
  ```
- Check Slack channel permissions

**Cursor Agent errors:**
- The workflow includes a fallback tip, so it will still send a message
- Verify `CURSOR_API_KEY` secret if you want to use Cursor Agent
- Check Cursor CLI installation in workflow logs

### Customization

To customize the tech tip prompt or format:

1. Edit `.github/workflows/tech-daily.yaml`
2. Modify the `PROMPT` variable in the "Generate Tech Tip" step
3. Adjust the Slack message format in the "Format and Send to Slack" step

