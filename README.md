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

### 5. Available Categories (`NCORE_TYPES`)
You can mix and match these categories (comma-separated):

| Category | Description | Category | Description |
| :--- | :--- | :--- | :--- |
| `HD_HUN` | HD Movies (Hungarian) | `HD` | HD Movies (English) |
| `HDSER_HUN` | HD Series (Hungarian) | `HDSER` | HD Series (English) |
| `SD_HUN` | SD Movies (Hungarian) | `SD` | SD Movies (English) |
| `DVD_HUN` | DVD (Hungarian) | `GAME_ISO` | Game ISOs |
| `EBOOK_HUN` | E-books (Hungarian) | `LOSSLESS_HUN` | Lossless Music (HU) |

*(For a full list, see the documentation or source code.)*

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
