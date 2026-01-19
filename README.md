# ncore-tracker

A lightweight, self-hosted Python application that monitors **nCore** for recommended torrents and sends instant **Telegram notifications** when new ones appear.

## Why use it?

If you often check the "Recommended" (Ajánlott) section on nCore but don't want to manually refresh the page, this tool does it for you. It remembers which torrents you've already seen and only alerts you about the brand new additions.

## How to use it

### 1. Prerequisites
- An active nCore account (2FA must be disabled).
- A Telegram Bot (see below).
- Docker and Docker Compose installed.

### 2. Manual Setup (Clone Repo)
1. **Clone/Download** this repository.
2. **Configure**: Open `docker-compose.yml` and fill in your credentials.
3. **Run**: `docker compose up -d`

### 3. Quick Start (Portainer / Docker Compose)
If you don't want to clone the repository, just copy this content into a `docker-compose.yml` file or a Portainer stack:

```yaml
services:
  ncore-tracker:
    image: ntwritecode/ncore-notifier:latest
    container_name: ncore-tracker
    restart: unless-stopped
    environment:
      - NCORE_USER=your_username
      - NCORE_PASS=your_password
      - NCORE_TYPES=HD_HUN,HDSER_HUN
      - CRON_INTERVAL=60
      - TELEGRAM_TOKEN=your_bot_token
      - TELEGRAM_CHAT_ID=your_chat_id
      - SILENT_FIRST_RUN=True
      - ONLY_RECENT_YEARS=True
      - NOTIFICATION_LINK_TYPE=both
    volumes:
      - ./data:/app/data
```

### 4. Configuration Details
Fill in your credentials as follows:
   - `NCORE_USER`: Your nCore username.
   - `NCORE_PASS`: Your nCore password.
   - `NCORE_TYPES`: What you are interested in (e.g., `HD_HUN,HDSER_HUN`).
   - `TELEGRAM_TOKEN`: Your bot's token from [@BotFather](https://t.me/BotFather).
   - `TELEGRAM_CHAT_ID`: Your chat ID (you can get it from [@userinfobot](https://t.me/userinfobot)).
   - `SILENT_FIRST_RUN`: (Optional) `True` to skip notifications for existing torrents on first start.
   - `ONLY_RECENT_YEARS`: (Optional) `True` to only notify about torrents from this or the previous year.
   - `NOTIFICATION_LINK_TYPE`: (Optional) `both`, `url` (details), or `download`.
3. **Run**:
   Choose one of the methods below:

   **Method B: Local Execution (for testing)**
   If you want to run it without Docker using `uv`:
   1. Copy the example config: `cp .env.example .env`
   2. Edit `.env` with your real data.
   3. Run:
      ```bash
      uv pip install -r requirements.txt
      uv run python main.py
      ```

### 5. Wishlist Feature (Targeted Search)
If you are looking for something specific (e.g. a specific movie that isn't currently "recommended"), you can create a `wishlist.json` file in your `./data` directory. The app will search for these patterns on every run.

**wishlist.json Example:**
```json
[
  {
    "pattern": "Forrest Gump",
    "type": ["HD_HUN", "HD"],
    "sort_by": "SEEDERS",
    "sort_order": "DECREASING"
  },
  {
    "pattern": "Inception",
    "type": "HD_HUN"
  }
]
```
*When an item is found and notified, the app will automatically add `"notified": true` to that item in the JSON so it doesn't alert you again.*

### 6. Category & Parameter Reference
These values apply to both the global `NCORE_TYPES` configuration and the `wishlist.json` fields.

#### Available Categories (`type`)
| Type | Description | Type | Description |
| :--- | :--- | :--- | :--- |
| `HD_HUN` | HD Movies (HU) | `HD` | HD Movies (EN) |
| `HDSER_HUN` | HD Series (HU) | `HDSER` | HD Series (EN) |
| `SD_HUN` | SD Movies (HU) | `SD` | SD Movies (EN) |
| `SDSER_HUN` | SD Series (HU) | `SDSER` | SD Series (EN) |
| `DVD_HUN` | DVD (HU) | `DVD` | DVD (EN) |
| `DVD9_HUN` | DVD9 (HU) | `DVD9` | DVD9 (EN) |
| `DVDSER_HUN` | DVD Series (HU) | `DVDSER` | DVD Series (EN) |
| `GAME_ISO` | PC Games (ISO) | `GAME_RIP` | PC Games (RIP) |
| `CONSOLE` | Console Games | `ISO` | Other ISO |
| `EBOOK_HUN` | E-book (HU) | `EBOOK` | E-book (EN) |
| `MP3_HUN` | MP3 (HU) | `MP3` | MP3 (EN) |
| `LOSSLESS_HUN` | Lossless (HU) | `LOSSLESS` | Lossless (EN) |
| `CLIP` | Music Video | `MOBIL` | Mobile |
| `MISC` | Misc | `ISO` | Other ISO |
| `XXX_HD` | Adult HD | `XXX_DVD` | Adult DVD |
| `XXX_SD` | Adult SD | `XXX_IMG` | Adult Image |
| `ALL_OWN` | All (Own) | | |

#### Sorting Options (`sort_by`)
| Value | Description |
| :--- | :--- |
| `NAME` | Sort by title |
| `UPLOAD` | Sort by upload date |
| `SIZE` | Sort by file size |
| `TIMES_COMPLETED` | Sort by download count |
| `SEEDERS` | Sort by active seeders |
| `LEECHERS` | Sort by active leechers |

#### Sort Order (`sort_order`)
| Value | Description |
| :--- | :--- |
| `INCREASING` | Ascending order (A-Z, oldest first) |
| `DECREASING` | Descending order (Z-A, newest first) |

## Technical Info
- **Environment Variables**:
  - `CRON_INTERVAL`: Frequency of checks in minutes (default is 60).
  - `TELEGRAM_TOKEN`: Your bot's token.
  - `TELEGRAM_CHAT_ID`: Your Telegram chat ID.
  - `SILENT_FIRST_RUN`: `True` to skip notifications for existing torrents on first start.
  - `ONLY_RECENT_YEARS`: `True` to only notify about torrents from this or the previous year.
  - `NOTIFICATION_LINK_TYPE`: `both`, `url` (details), or `download`.
- **Persistence**: 
  - In Docker: Data is stored in the mounted volume (typically `./data`).
  - Locally: The app automatically detects it's not in a container and uses `./data` in your current folder.

### Tips & Tricks
- **Testing without notifications**: If you leave `TELEGRAM_TOKEN` empty, the app will just print the new torrents to your terminal.
- **Immediate Check**: The app always runs a check immediately when it starts, then waits for the `CRON_INTERVAL`.
- **Session Reuse**: If you see "Reusing existing session cookies" in the logs, it means the app is successfully avoiding unnecessary logins.

---
Built with ❤️ by [NtWriteCode](https://github.com/NtWriteCode)
