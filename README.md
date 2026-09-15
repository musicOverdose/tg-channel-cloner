# ⚡ tg-channel-cloner

<p align="left">
  <img src="https://img.shields.io/badge/Made_by-Farzad_(@MusicOverdose)-indigo?style=for-the-badge" alt="Made by Farzad" />
</p>

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Docker Ready](https://img.shields.io/badge/Docker-Ready-2496ED?logo=docker&logoColor=white)](docker-compose.yml)
[![Portainer Ready](https://img.shields.io/badge/Portainer-Stack-13BEBB?logo=portainer&logoColor=white)](docker-compose.yml)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688?logo=fastapi&logoColor=white)](backend/)
[![Python 3.12+](https://img.shields.io/badge/Python-3.12+-3776AB?logo=python&logoColor=white)](Dockerfile)

A production-quality, self-hosted **Telegram Channel Cloner & Synchronizer** with a built-in persistent scheduler, timezone support, incremental cloning, multi-bot concurrency, encrypted secrets, and a modern web dashboard.

Engineered specifically for one-click deployment via **Portainer Git Stacks** and **Docker Compose**.

---

## 📑 Table of Contents

- [Features](#-features)
- [Portainer Deployment (Recommended)](#-portainer-deployment-recommended)
- [Docker Compose Deployment](#-docker-compose-deployment)
- [Environment Variables](#-environment-variables)
- [Channel & Bot Prerequisites](#-channel--bot-prerequisites)
- [Scheduling & Incremental Cloning](#-scheduling--incremental-cloning)
- [Backup and Restore](#-backup-and-restore)
- [Telegram API Limitations](#-telegram-api-limitations)
- [Author](#-author)
- [License](#-license)

---

## ✨ Features

- **🚀 Portainer & Docker Ready**: Push to GitHub, point Portainer to the repository, add environment variables, and deploy.
- **⏰ Zero Host Cron**: Internal persistent scheduler survives Docker container restarts, server reboots, and crashes.
- **🌍 Native Timezone Support**: Explicit IANA timezone per job (`Asia/Tehran`, `Europe/Berlin`, `America/New_York`, `UTC`) with full DST handling.
- **🔄 Incremental Sync**: Copies only new messages since the last successful run instead of re-copying existing history.
- **⚡ Bot API 7.0+ Batching**: High-speed batch copying via `copyMessages` with automatic single-message fallback for deleted posts/gaps.
- **🛡️ Isolated Rate Limiting**: Per-bot token bucket rate limiter with automated HTTP 429 `retry_after` backoff.
- **🔐 Encrypted Secrets**: Bot tokens encrypted at rest (AES-256 / Fernet) and masked in the UI.
- **📊 Real-time Dashboard**: Dark-mode Single Page Application with live WebSocket progress, permission probing, and logs.
- **💾 One-Click Backups**: Download point-in-time SQLite database snapshots directly from the UI.

---

## 🚢 Portainer Deployment (Recommended)

1. **Fork or push this repo to your GitHub account**:
   ```bash
   git remote add origin https://github.com/MusicOverdose/tg-channel-cloner.git
   git push -u origin main
   ```
2. **Open Portainer**:
   - Go to **Stacks** ➔ **+ Add stack** ➔ Select **Repository**.
   - **Name**: `tg-channel-cloner`
   - **Repository URL**: `https://github.com/MusicOverdose/tg-channel-cloner.git`
   - **Compose path**: `docker-compose.yml`
3. **Set Environment Variables**:

| Variable | Recommended Value | Description |
| :--- | :--- | :--- |
| `APP_PORT` | `8083` | Exposed port on host |
| `ADMIN_USERNAME` | `admin` | Web UI login username |
| `ADMIN_PASSWORD` | `YOUR_SECURE_PASSWORD` | Web UI login password |
| `SECRET_KEY` | *(Run `openssl rand -base64 32`)* | Key for token encryption & JWT |
| `MAX_CONCURRENT_JOBS` | `10` | Max simultaneous cloning jobs |
| `LOG_LEVEL` | `INFO` | Application log verbosity |

4. Click **Deploy the stack**.
5. Open `http://SERVER_IP:8083` and log in!

---

## 💻 Docker Compose Deployment

```bash
# Clone and enter repo
git clone https://github.com/MusicOverdose/tg-channel-cloner.git
cd tg-channel-cloner

# Configure environment
cp .env.example .env
nano .env

# Build and start
docker compose up -d --build
```

Access the web UI at `http://localhost:8083`.

---

## ⚙ Environment Variables

| Variable | Default | Description |
| :--- | :--- | :--- |
| `APP_PORT` | `8083` | Host port to publish the application web UI. |
| `ADMIN_USERNAME` | `admin` | Initial administrator login username. |
| `ADMIN_PASSWORD` | `admin` | Initial administrator login password. Change on first login! |
| `SECRET_KEY` | `change-me` | Secret key used for JWT signing and token encryption at rest. |
| `DATABASE_URL` | `sqlite+aiosqlite:////data/cloner.db` | Persistent database path (SQLite in Docker volume `/data`). |
| `MAX_CONCURRENT_JOBS` | `10` | Maximum number of simultaneous channel cloning tasks. |
| `LOG_LEVEL` | `INFO` | Log level: `DEBUG`, `INFO`, `WARNING`, `ERROR`. |

---

## 🤖 Channel & Bot Prerequisites

1. **Destination Channel**: Add your bot as an **Administrator** with **Post Messages** enabled.
2. **Source Channel**: If private, the bot must be added as a member/administrator to read messages. (Public channels can be read directly).
3. **Channel IDs**: Use standard channel IDs (e.g. `-1001234567890`). Use the built-in **🔍 Validate Bot Permissions & Probe Channels** button in the dashboard to instantly test channel access and permissions.

---

## ⏰ Scheduling & Incremental Cloning

- **Frequencies**: Daily at a specific time (e.g. `01:00`), Weekly on selected days, Once at a target date, or custom Cron expressions.
- **Timezone Awareness**: All schedule calculations account for local time and Daylight Saving Time (DST) shifts.
- **Incremental Mode**: Automatically starts from `last_copied_message_id + 1`. Only newly published posts are copied on subsequent runs.
- **Overlap & Missed Run Policies**: Choose whether to skip overlapping runs if a previous execution is still running, and whether to run once immediately if the server was offline during a scheduled time.

---

## 💾 Backup and Restore

Persistent data is stored in the Docker volume `tg_cloner_data` at `/data/cloner.db`.

- **From Web UI**: Go to **System Settings** ➔ Click **💾 Download Database Backup (.db)**.
- **From Host Terminal**:
  ```bash
  docker run --rm -v tg_cloner_data:/data -v $(pwd):/backup alpine cp /data/cloner.db /backup/cloner_backup.db
  ```
- **Restore**: Copy the backup `.db` file back into `/data/cloner.db` on any new server or VPS and restart the container.

---

## ⚠️ Telegram API Limitations

1. **Protected Content (`has_protected_content`)**: If the source channel owner enabled "Restrict saving content", Telegram rejects copying (`CHAT_FORWARDS_RESTRICTED`). The engine logs a notice and skips without crashing.
2. **Rate Limits (429)**: Telegram limits bots to ~30 req/s globally and ~20 msgs/min per channel. The engine handles `429 Too Many Requests` automatically by sleeping for the exact `retry_after` duration returned by Telegram.
3. **Deleted Messages**: Missing message IDs (from deleted posts) are detected as gaps and counted as `Skipped` without halting the sync.

---

## 👤 Author

Created and maintained by **Farzad (MusicOverdose)**
- <img src="https://img.shields.io/badge/Made_by-Farzad_(@MusicOverdose)-indigo?style=for-the-badge" alt="Made by Farzad" />
- GitHub: [@MusicOverdose](https://github.com/MusicOverdose)
- Repository: [MusicOverdose/tg-channel-cloner](https://github.com/MusicOverdose/tg-channel-cloner)

---

## 📄 License

This project is licensed under the [MIT License](LICENSE).
