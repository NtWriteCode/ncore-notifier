import os
import json
import time
import logging
import schedule
import requests
import html
import datetime
import traceback
from dotenv import load_dotenv
from ncoreparser import Client, SearchParamType

# Load environment variables
load_dotenv()

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Configuration Helper
def get_env(key, default=None, type_cast=str):
    val = os.environ.get(key, default)
    if type_cast == bool:
        return str(val).lower() in ("true", "1", "yes", "on")
    return type_cast(val) if val is not None else default

# Settings
CONFIG = {
    "USER": get_env("NCORE_USER"),
    "PASS": get_env("NCORE_PASS"),
    "TYPES": {t.strip().lower() for t in get_env("NCORE_TYPES", "HD_HUN").split(",")},
    "INTERVAL": get_env("CRON_INTERVAL", 60, int),
    "TG_TOKEN": get_env("TELEGRAM_TOKEN"),
    "TG_CHAT": get_env("TELEGRAM_CHAT_ID"),
    "SILENT_START": get_env("SILENT_FIRST_RUN", True, bool),
    "ONLY_RECENT": get_env("ONLY_RECENT_YEARS", True, bool),
    "LINK_TYPE": get_env("NOTIFICATION_LINK_TYPE", "both").lower()
}

DATA_DIR = "/app/data" if os.path.exists("/.dockerenv") else "./data"
SEEN_FILE = os.path.join(DATA_DIR, "seen.json")
COOKIE_FILE = os.path.join(DATA_DIR, "cookies.json")

def json_io(path, data=None):
    try:
        if data is None: # Load mode
            if not os.path.exists(path): return []
            with open(path, 'r') as f: return json.load(f)
        # Save mode
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w') as f: json.dump(data, f, indent=2)
    except Exception as e:
        logger.error(f"IO Error on {path}: {e}")
    return [] if data is None else None

def send_tg(message):
    if not CONFIG["TG_TOKEN"] or not CONFIG["TG_CHAT"]:
        return logger.warning("Telegram not configured.")
    
    try:
        res = requests.post(
            f"https://api.telegram.org/bot{CONFIG['TG_TOKEN']}/sendMessage",
            json={"chat_id": CONFIG["TG_CHAT"], "text": message, "parse_mode": "HTML"}
        )
        if res.status_code != 200:
            logger.error(f"Telegram API Error: {res.text}")
    except Exception as e:
        logger.error(f"Telegram notification failed: {e}")

def get_client():
    client = Client(cookies=json_io(COOKIE_FILE))
    if not getattr(client, "_logged_in", False):
        if not CONFIG["USER"] or not CONFIG["PASS"]:
            return logger.error("Missing nCore credentials!")
        
        logger.info("Logging in to nCore...")
        try:
            cookies = client.login(CONFIG["USER"], CONFIG["PASS"])
            json_io(COOKIE_FILE, cookies)
        except Exception as e:
            return logger.error(f"Login failed: {e}")
    return client

def run_tracker():
    logger.info("Starting check for new torrents...")
    client = get_client()
    if not client: return

    seen_exists = os.path.exists(SEEN_FILE)
    seen_ids = set(json_io(SEEN_FILE))
    new_seen_ids = set(seen_ids)
    
    stats = {"total": 0, "seen": 0, "wrong_cat": 0, "old": 0, "silent": 0, "sent": 0}
    allowed_years = [datetime.datetime.now().year, datetime.datetime.now().year - 1]

    try:
        for torrent in client.get_recommended():
            stats["total"] += 1
            t_id = str(torrent['id'])
            
            if t_id in seen_ids:
                stats["seen"] += 1
                continue
            
            new_seen_ids.add(t_id)
            
            if not seen_exists and CONFIG["SILENT_START"]:
                stats["silent"] += 1
                continue

            # Heavy lazy-loading starts here
            t_type = torrent['type'].value if hasattr(torrent['type'], 'value') else str(torrent['type'])
            if t_type.lower() not in CONFIG["TYPES"]:
                stats["wrong_cat"] += 1
                continue
                
            if CONFIG["ONLY_RECENT"] and getattr(torrent.get('date'), 'year', 0) not in allowed_years:
                stats["old"] += 1
                continue

            logger.info(f"New torrent found: {torrent['title']}")
            
            links = []
            if CONFIG["LINK_TYPE"] in ('url', 'both'):
                links.append(f"<a href='{torrent['url']}'>🔗 Details</a>")
            if CONFIG["LINK_TYPE"] in ('download', 'both'):
                links.append(f"<a href='{torrent['download']}'>⬇️ Download</a>")

            msg = (
                f"🌟 <b>New Recommended Torrent!</b>\n\n"
                f"📌 <b>Title:</b> {html.escape(str(torrent['title']))}\n"
                f"📂 <b>Type:</b> {html.escape(str(torrent['type']))}\n"
                f"⚖️ <b>Size:</b> {html.escape(str(torrent['size']))}\n"
                f"📅 <b>Date:</b> {torrent['date'].strftime('%Y-%m-%d %H:%M') if hasattr(torrent['date'], 'strftime') else 'Unknown'}\n\n"
                f"{' | '.join(links)}"
            )
            send_tg(msg)
            stats["sent"] += 1
                
    except Exception:
        logger.error(f"Tracker error: {traceback.format_exc()}")

    logger.info(
        f"Check finished. Total: {stats['total']} | Already seen: {stats['seen']} | "
        f"New: {stats['total'] - stats['seen']} (Notified: {stats['sent']}, "
        f"Wrong Category: {stats['wrong_cat']}, Too Old: {stats['old']}"
        f"{', Silent: ' + str(stats['silent']) if stats['silent'] else ''})"
    )

    if len(new_seen_ids) > len(seen_ids):
        json_io(SEEN_FILE, list(new_seen_ids))

if __name__ == "__main__":
    run_tracker() # Initial run
    schedule.every(CONFIG["INTERVAL"]).minutes.do(run_tracker)
    while True:
        schedule.run_pending()
        time.sleep(1)
