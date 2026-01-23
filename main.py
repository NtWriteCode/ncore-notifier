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
from ncoreparser import Client, SearchParamType, ParamSort, ParamSeq

# Load environment variables
load_dotenv()

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Mute noisy external libraries
for noisy_logger in ["ncoreparser", "urllib3", "requests"]:
    logging.getLogger(noisy_logger).setLevel(logging.WARNING)

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
    "LINK_TYPE": get_env("NOTIFICATION_LINK_TYPE", "both").lower(),
    "RETENTION": get_env("RETENTION_MONTHS", 6, int)
}

DATA_DIR = "/app/data" if os.path.exists("/.dockerenv") else "./data"
SEEN_FILE = os.path.join(DATA_DIR, "seen.json")
COOKIE_FILE = os.path.join(DATA_DIR, "cookies.json")
WISHLIST_FILE = os.path.join(DATA_DIR, "wishlist.json")

def json_io(path, data=None):
    try:
        if data is None: # Load mode
            if not os.path.exists(path): return []
            with open(path, 'r') as f: return json.load(f)
        # Save mode
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w') as f: json.dump(data, f, separators=(',', ':'))
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

    # Load seen data
    seen_data = json_io(SEEN_FILE)
    if not isinstance(seen_data, dict):
        seen_data = {}
    
    seen_exists = os.path.exists(SEEN_FILE)
    updated_seen = False
    
    stats = {"total": 0, "seen": 0, "wrong_cat": 0, "old": 0, "silent": 0, "sent": 0}
    allowed_years = [datetime.datetime.now().year, datetime.datetime.now().year - 1]

    try:
        current_ts = int(time.time())
        for torrent in client.get_recommended():
            stats["total"] += 1
            t_id = str(torrent['id'])
            
            if t_id in seen_data:
                stats["seen"] += 1
                # Update timestamp so it stays "fresh" and won't be pruned
                seen_data[t_id] = current_ts
                continue
            
            # This is a new ID
            seen_data[t_id] = current_ts
            updated_seen = True
            
            if not seen_exists and CONFIG["SILENT_START"]:
                stats["silent"] += 1
                continue

            # Heavy lazy-loading starts here
            t_type = torrent['type'].value if hasattr(torrent['type'], 'value') else str(torrent['type'])
            if t_type.lower() not in CONFIG["TYPES"]:
                stats["wrong_cat"] += 1
                continue
                
            if CONFIG["ONLY_RECENT"] and getattr(torrent['date'], 'year', 0) not in allowed_years:
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

    if updated_seen:
        # Prune entries older than CONFIG["RETENTION"] months
        # Approximating a month as 30 days
        cutoff = current_ts - (CONFIG["RETENTION"] * 30 * 24 * 60 * 60)
        pruned = {k: v for k, v in seen_data.items() if v > cutoff}
        json_io(SEEN_FILE, pruned)

def run_wishlist():
    if not os.path.exists(WISHLIST_FILE):
        return

    logger.info("Checking wishlist...")
    client = get_client()
    if not client: return

    wishlist = json_io(WISHLIST_FILE)
    if not isinstance(wishlist, list):
        return logger.warning("Wishlist is not a valid JSON array!")

    changed = False
    for item in wishlist:
        if item.get("notified"):
            continue

        pattern = item.get("pattern")
        if not pattern:
            continue

        types = item.get("type", "ALL_OWN")
        if isinstance(types, str):
            types = [types]

        sort_by_str = item.get("sort_by", "SEEDERS").upper()
        sort_order_str = item.get("sort_order", "DECREASING").upper()
        
        try:
            sort_by = getattr(ParamSort, sort_by_str, ParamSort.SEEDERS)
            sort_order = getattr(ParamSeq, sort_order_str, ParamSeq.DECREASING)
        except Exception:
            sort_by = ParamSort.SEEDERS
            sort_order = ParamSeq.DECREASING

        found_torrent = None
        for t_type_str in types:
            try:
                t_type = getattr(SearchParamType, t_type_str.upper())
                results = client.search(
                    pattern=pattern,
                    type=t_type,
                    sort_by=sort_by,
                    sort_order=sort_order
                )
                if results.torrents:
                    found_torrent = results.torrents[0]
                    break
            except Exception as e:
                logger.error(f"Wishlist search error for {pattern} in {t_type_str}: {e}")

        if found_torrent:
            logger.info(f"🌟 Wishlist item found: {pattern} -> {found_torrent['title']}")
            
            links = []
            if CONFIG["LINK_TYPE"] in ('url', 'both'):
                links.append(f"<a href='{found_torrent['url']}'>🔗 Details</a>")
            if CONFIG["LINK_TYPE"] in ('download', 'both'):
                links.append(f"<a href='{found_torrent['download']}'>⬇️ Download</a>")

            msg = (
                f"🎯 <b>Wishlist Item Found!</b>\n\n"
                f"🔍 <b>Pattern:</b> {html.escape(pattern)}\n"
                f"📌 <b>Title:</b> {html.escape(str(found_torrent['title']))}\n"
                f"📂 <b>Type:</b> {html.escape(str(found_torrent['type']))}\n"
                f"⚖️ <b>Size:</b> {html.escape(str(found_torrent['size']))}\n\n"
                f"{' | '.join(links)}"
            )
            send_tg(msg)
            item["notified"] = True
            changed = True

    if changed:
        json_io(WISHLIST_FILE, wishlist)

def job():
    run_tracker()
    run_wishlist()

if __name__ == "__main__":
    job() # Initial run
    schedule.every(CONFIG["INTERVAL"]).minutes.do(job)
    while True:
        schedule.run_pending()
        time.sleep(1)
