# Amazon Price Tracker + Slack Notifier

Tracks Amazon product prices and sends a Slack alert when the price drops or hits your target.

---

## Setup

### 1. Install dependencies
```bash
pip install -r requirements.txt
```

### 2. Create a Slack Incoming Webhook
1. Go to https://api.slack.com/apps → **Create New App** → From scratch
2. Choose a name + workspace, click **Create App**
3. Go to **Incoming Webhooks** → toggle **Activate Incoming Webhooks** ON
4. Click **Add New Webhook to Workspace** → pick a channel → **Allow**
5. Copy the webhook URL (looks like `https://hooks.slack.com/services/T.../B.../xxx`)

### 3. Configure `price_tracker.py`

Open `price_tracker.py` and edit the top section:

```python
SLACK_WEBHOOK_URL = "https://hooks.slack.com/services/YOUR/WEBHOOK/URL"

PRODUCTS = [
    {
        "name": "Sony WH-1000XM5 Headphones",
        "url": "https://www.amazon.com/dp/B09XS7JWHH",
        "target_price": 280.00,   # alert if price drops below this
    },
]

CHECK_INTERVAL_SECONDS = 3600  # check every hour
```

### 4. Run the tracker
```bash
python price_tracker.py
```

---

## How to get an Amazon product URL

1. Go to the Amazon product page
2. Copy the URL from your browser  
   e.g. `https://www.amazon.com/dp/B09XS7JWHH`
3. Paste it into `PRODUCTS`

---

## Alerts are sent when:
- 📉 Price **drops** from the last recorded price
- 🎯 Price goes **below your target price**

Price history is saved in `price_history.json` so it persists between runs.

---

## Run automatically (optional)

**Linux/macOS — cron job** (check every hour):
```bash
crontab -e
# Add this line:
0 * * * * /usr/bin/python3 /path/to/price_tracker.py >> /path/to/tracker.log 2>&1
```

**Windows — Task Scheduler:**
- Action: `python C:\path\to\price_tracker.py`
- Trigger: Daily, repeat every 1 hour

---

## Notes
- Amazon occasionally blocks scrapers. If prices aren't being fetched, try adding a delay or rotating your User-Agent.
- This is for personal use only — respect Amazon's Terms of Service.