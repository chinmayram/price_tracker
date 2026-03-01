"""
Amazon Price Tracker with Slack Notifications
Uses ScraperAPI to bypass Amazon bot detection.
Designed to run as a single-run GitHub Actions job.
"""

import json
import os
import time
import random
import requests
from datetime import datetime
from bs4 import BeautifulSoup

# ─────────────────────────────────────────────
# CONFIGURATION — edit these values
# ─────────────────────────────────────────────

# Read from GitHub Secrets (never hardcode these)
SLACK_WEBHOOK_URL = os.environ.get("SLACK_WEBHOOK_URL")
SCRAPER_API_KEY   = os.environ.get("SCRAPER_API_KEY")

PRODUCTS = [
    {
        "name": "Apple Mac Mini M4",
        "url": "https://www.amazon.in/dp/B0DLCNVB5J",
        "target_price": 54000.00,   # alert if price drops below this
    },
    # Add more products here:
    # {
    #     "name": "Product Name",
    #     "url": "https://www.amazon.com/dp/ASIN",
    #     "target_price": 99.99,
    # },
]

PRICE_HISTORY_FILE = "price_history.json"

# ─────────────────────────────────────────────


def load_price_history() -> dict:
    if os.path.exists(PRICE_HISTORY_FILE):
        with open(PRICE_HISTORY_FILE, "r") as f:
            return json.load(f)
    return {}


def save_price_history(history: dict):
    with open(PRICE_HISTORY_FILE, "w") as f:
        json.dump(history, f, indent=2)


def get_amazon_price(url: str) -> float | None:
    """Fetch Amazon product price via ScraperAPI (bypasses bot detection)."""
    try:
        scraper_url = "https://api.scraperapi.com/"
        params = {
            "api_key": SCRAPER_API_KEY,
            "url": url,
            "country_code": "us",   # scrape from US region
        }

        print(f"  📡 Fetching via ScraperAPI...")
        response = requests.get(scraper_url, params=params, timeout=60)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")

        # Try multiple price selectors (Amazon changes their HTML often)
        selectors = [
            ("span", {"class": "a-price-whole"}),
            ("span", {"id": "priceblock_ourprice"}),
            ("span", {"id": "priceblock_dealprice"}),
            ("span", {"class": "a-offscreen"}),
        ]

        for tag, attrs in selectors:
            el = soup.find(tag, attrs)
            if el:
                raw = el.get_text().strip().replace(",", "").replace("$", "").split(".")[0]
                frac_el = soup.find("span", {"class": "a-price-fraction"})
                frac = frac_el.get_text().strip() if frac_el else "00"
                price = float(f"{raw}.{frac}")
                return price

        print(f"  [!] Could not find price on page.")
        return None

    except Exception as e:
        print(f"  [!] Error fetching price: {e}")
        return None


def send_slack_message(product: dict, current_price: float, previous_price: float | None):
    """Send a Slack notification about a price drop."""
    if not SLACK_WEBHOOK_URL or "YOUR/WEBHOOK" in SLACK_WEBHOOK_URL:
        print("  [!] SLACK_WEBHOOK_URL not configured. Skipping notification.")
        return

    drop_amount = (previous_price - current_price) if previous_price else 0
    drop_pct    = (drop_amount / previous_price * 100) if previous_price else 0

    message = {
        "text": f"🚨 Price Drop Alert! — {product['name']}",
        "blocks": [
            {
                "type": "header",
                "text": {"type": "plain_text", "text": "🚨 Price Drop Alert!"}
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": (
                        f"*{product['name']}*\n"
                        f"🔗 <{product['url']}|View on Amazon>\n\n"
                        f"💰 *Current Price:* ${current_price:.2f}\n"
                        + (f"📉 *Previous Price:* ${previous_price:.2f}\n"
                           f"✅ *You Save:* ${drop_amount:.2f} ({drop_pct:.1f}% off)\n"
                           if previous_price else "")
                        + f"🎯 *Your Target:* ${product['target_price']:.2f}\n"
                        f"🕐 *Checked at:* {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} UTC"
                    ),
                },
            },
            {
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "Buy Now 🛒"},
                        "url": product["url"],
                        "style": "primary",
                    }
                ],
            },
        ],
    }

    try:
        resp = requests.post(SLACK_WEBHOOK_URL, json=message, timeout=10)
        if resp.status_code == 200:
            print(f"  ✅ Slack notification sent!")
        else:
            print(f"  [!] Slack error {resp.status_code}: {resp.text}")
    except Exception as e:
        print(f"  [!] Failed to send Slack message: {e}")


def check_product(product: dict, history: dict):
    url    = product["url"]
    name   = product["name"]
    target = product["target_price"]

    print(f"\n🔍 Checking: {name}")
    current_price = get_amazon_price(url)

    if current_price is None:
        print(f"  ⚠️  Skipping — could not retrieve price.")
        return

    print(f"  💲 Current price: ${current_price:.2f}  |  Target: ${target:.2f}")

    previous_price = history.get(url, {}).get("last_price")

    # Record price history
    if url not in history:
        history[url] = {"name": name, "prices": []}
    history[url]["prices"].append({"price": current_price, "ts": datetime.now().isoformat()})
    history[url]["last_price"] = current_price

    # Alert conditions
    price_dropped = previous_price and current_price < previous_price
    below_target  = current_price <= target

    if below_target or price_dropped:
        reason = []
        if below_target:
            reason.append(f"below your target of ${target:.2f}")
        if price_dropped:
            reason.append(f"dropped from ${previous_price:.2f}")
        print(f"  🎉 Alert! Price {' and '.join(reason)}. Sending Slack message...")
        send_slack_message(product, current_price, previous_price)
    else:
        print(f"  ℹ️  No drop. Previous: ${previous_price or 'first check'}")


def run():
    print("=" * 55)
    print("  Amazon Price Tracker — GitHub Actions Run")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} UTC")
    print("=" * 55)

    history = load_price_history()

    for product in PRODUCTS:
        check_product(product, history)
        time.sleep(random.uniform(2, 5))  # polite delay between products

    save_price_history(history)
    print("\n✅ Done.")


if __name__ == "__main__":
    run()