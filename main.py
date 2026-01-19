import os
import json
import time
import logging
import schedule
import requests
import html
import html
import datetime
from dotenv import load_dotenv
from ncoreparser import Client, SearchParamType

# Load environment variables from .env file (if it exists)
load_dotenv()

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration
NCORE_USER = os.environ.get("NCORE_USER")
NCORE_PASS = os.environ.get("NCORE_PASS")
NCORE_TYPES_STR = os.environ.get("NCORE_TYPES", "HD_HUN")
CRON_INTERVAL = int(os.environ.get("CRON_INTERVAL", "60"))
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

# New Features Configuration
def str_to_bool(val):
    return str(val).lower() in ("true", "1", "yes", "on")

SILENT_FIRST_RUN = str_to_bool(os.environ.get("SILENT_FIRST_RUN", "True"))
ONLY_RECENT_YEARS = str_to_bool(os.environ.get("ONLY_RECENT_YEARS", "True"))
# Options: 'download', 'url', 'both'
NOTIFICATION_LINK_TYPE = os.environ.get("NOTIFICATION_LINK_TYPE", "both").lower()

# Dynamic data directory: /app/data in Docker, ./data locally
DATA_DIR = "/app/data" if os.path.exists("/.dockerenv") else "./data"
SEEN_FILE = os.path.join(DATA_DIR, "seen.json")
COOKIE_FILE = os.path.join(DATA_DIR, "cookies.json")

def send_telegram_notification(message):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        logger.warning("Telegram notification skipped: Token or Chat ID not configured.")
        return

    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "HTML"
    }
    try:
        response = requests.post(url, json=payload)
        if response.status_code != 200:
            logger.error(f"Telegram API Error: {response.text}")
        response.raise_for_status()
    except Exception as e:
        logger.error(f"Failed to send Telegram notification: {e}")

def load_json(filepath, default):
    if os.path.exists(filepath):
        try:
            with open(filepath, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading {filepath}: {e}")
    return default

def save_json(filepath, data):
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    try:
        with open(filepath, 'w') as f:
            json.dump(data, f)
    except Exception as e:
        logger.error(f"Error saving {filepath}: {e}")

def get_ncore_client():
    cookies = load_json(COOKIE_FILE, None)
    client = Client(cookies=cookies)
    
    # Check if we are actually logged in (internal hack based on example)
    # The example suggests client._logged_in is the way to check.
    if not getattr(client, "_logged_in", False):
        if not NCORE_USER or not NCORE_PASS:
            logger.error("Not logged in and NCORE_USER/NCORE_PASS not provided!")
            return None
        
        logger.info("Logging in to ncore...")
        try:
            cookies = client.login(NCORE_USER, NCORE_PASS)
            save_json(COOKIE_FILE, cookies)
            logger.info("Login successful, cookies saved.")
        except Exception as e:
            logger.error(f"Login failed: {e}")
            return None
    else:
        logger.info("Reusing existing session cookies.")
    
    return client

def check_for_new_torrents():
    logger.info("Checking for new torrents...")
    client = get_ncore_client()
    if not client:
        return

    seen_file_exists = os.path.exists(SEEN_FILE)
    seen_ids = set(load_json(SEEN_FILE, []))
    new_seen_ids = set(seen_ids)
    
    types_to_check = {t.strip().lower() for t in NCORE_TYPES_STR.split(",")}
    new_found_count = 0
    notifications_sent = 0

    try:
        # Fetch all recommended torrents once to avoid multiple requests
        logger.info("Fetching all recommended torrents...")
        all_recommended = client.get_recommended()
        
        current_year = datetime.datetime.now().year
        allowed_years = [current_year, current_year - 1]

        for torrent in all_recommended:
            t_id = str(torrent['id'])
            
            # 1. Filter by category
            t_type_val = torrent['type'].value if hasattr(torrent['type'], 'value') else str(torrent['type'])
            if t_type_val.lower() not in types_to_check:
                continue
                
            # 2. Filter by date (if enabled)
            if ONLY_RECENT_YEARS and hasattr(torrent['date'], 'year'):
                if torrent['date'].year not in allowed_years:
                    continue

            # 3. Check if new
            if t_id not in seen_ids:
                new_seen_ids.add(t_id)
                new_found_count += 1
                
                # If this is the first run and silent mode is on, just record the IDs
                if not seen_file_exists and SILENT_FIRST_RUN:
                    continue

                logger.info(f"New torrent found: {torrent['title']}")
                
                # Format links
                links = []
                if NOTIFICATION_LINK_TYPE in ('url', 'both'):
                    links.append(f"<a href='{torrent['url']}'>🔗 Details</a>")
                if NOTIFICATION_LINK_TYPE in ('download', 'both'):
                    links.append(f"<a href='{torrent['download']}'>⬇️ Download</a>")
                
                links_str = " | ".join(links)

                message = (
                    f"🌟 <b>New Recommended Torrent!</b>\n\n"
                    f"📌 <b>Title:</b> {html.escape(str(torrent['title']))}\n"
                    f"📂 <b>Type:</b> {html.escape(str(torrent['type']))}\n"
                    f"⚖️ <b>Size:</b> {html.escape(str(torrent['size']))}\n"
                    f"� <b>Date:</b> {torrent['date'].strftime('%Y-%m-%d %H:%M') if hasattr(torrent['date'], 'strftime') else 'Unknown'}\n\n"
                    f"{links_str}"
                )
                send_telegram_notification(message)
                notifications_sent += 1
                
    except Exception as e:
        logger.error(f"Error during check: {e}")
        import traceback
        logger.error(traceback.format_exc())

    if new_found_count > 0:
        save_json(SEEN_FILE, list(new_seen_ids))
        if not seen_file_exists and SILENT_FIRST_RUN:
            logger.info(f"Initial run completed silently. Marked {new_found_count} torrents as seen.")
        else:
            logger.info(f"Finished check. Found {new_found_count} new torrents, sent {notifications_sent} notifications.")
    else:
        logger.info("No new torrents found.")

def main():
    logger.info("Starting ncore-tracker...")
    
    # Run once at startup
    check_for_new_torrents()
    
    # Schedule periodic runs
    schedule.every(CRON_INTERVAL).minutes.do(check_for_new_torrents)
    
    while True:
        schedule.run_pending()
        time.sleep(1)

if __name__ == "__main__":
    main()
