# ⚡ Telegram Channel Cloner

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Docker Ready](https://img.shields.io/badge/Docker-Ready-2496ED?logo=docker&logoColor=white)](docker-compose.yml)
[![Portainer Ready](https://img.shields.io/badge/Portainer-Stack-13BEBB?logo=portainer&logoColor=white)](docker-compose.yml)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688?logo=fastapi&logoColor=white)](backend/)
[![Python 3.12+](https://img.shields.io/badge/Python-3.12+-3776AB?logo=python&logoColor=white)](Dockerfile)

A production-quality, self-hosted **Telegram Channel Cloner & Synchronizer** with a built-in persistent scheduler, timezone support, incremental cloning, multi-bot concurrency, encrypted secrets, and a modern web dashboard.

Engineered specifically for one-click deployment via **Portainer Git Stacks** and **Docker Compose**.

---

## 📑 Table of Contents

- [Overview](#-overview)
- [Key Features](#-key-features)
- [Architecture](#-architecture)
- [Portainer Deployment Guide (Recommended)](#-portainer-deployment-guide-recommended)
- [Docker Compose Deployment Guide](#-docker-compose-deployment-guide)
- [Environment Variables](#-environment-variables)
- [Telegram Bot & Channel Setup](#-telegram-bot--channel-setup)
- [Scheduling & Incremental Cloning](#-scheduling--incremental-cloning)
- [Backup and Restore](#-backup-and-restore)
- [Updating the Stack](#-updating-the-stack)
- [Telegram API Limitations & Best Practices](#-telegram-api-limitations--best-practices)
- [Troubleshooting](#-troubleshooting)
- [Security](#-security)
- [License](#-license)

---

## 🌟 Overview

**Telegram Channel Cloner** is an automated channel synchronization and backup system. It lets you clone public or private Telegram channels into your own destination channels. 

Whether you need a **one-time full history backup** or a **daily scheduled sync** that only copies newly published posts, everything runs autonomously inside a single, resilient Docker container without needing host cron, systemd scripts, or manual maintenance.

---

## ✨ Key Features

- **🚀 100% Portainer & GitHub Ready**: Push this repository to GitHub, open Portainer, point to your repository URL, enter environment variables, and click Deploy.
- **⏰ Zero Host Cron Requirement**: Authoritative persistent scheduler runs inside the container and survives Docker restarts, server reboots, and crashes.
- **🌍 Native Timezone Support**: Explicit IANA timezone configuration per job (e.g. `Asia/Tehran`, `Europe/Berlin`, `America/New_York`, `UTC`) with full Daylight Saving Time (DST) handling.
- **🔄 Intelligent Incremental Mode**: Copies only new messages published since the previous execution instead of needlessly re-copying existing history.
- **⚡ Bot API 7.0+ High-Speed Batching**: Uses native `copyMessages` for bulk copying with automatic item-by-item fallback for deleted messages or gaps.
- **🛡️ Isolated Per-Bot Rate Limiting**: Full handling of HTTP `429 Too Many Requests` (`retry_after`). A flood wait on Bot A never stalls Bot B.
- **🔐 Encrypted Secrets at Rest**: Sensitive Telegram Bot tokens are encrypted using AES-256 / Fernet using `SECRET_KEY`, and always masked in the UI.
- **📊 Real-time Web Dashboard**: Dark-mode Single Page Application with live WebSocket progress bars, channel permission probing, execution history, and live logs.
- **💾 One-Click Database Backups**: Export an authoritative SQLite snapshot directly from the Web UI with one click.

---

## 🏗 Architecture

```text
                           ┌──────────────────────────┐
                           │   Portainer / Docker     │
                           │     docker-compose.yml   │
                           └─────────────┬────────────┘
                                         │
                                         ▼
                 ┌──────────────────────────────────────────────┐
                 │       Telegram Channel Cloner (:8083)        │
                 │                                              │
                 │   ┌──────────────────────────────────────┐   │
                 │   │     Web Dashboard (SPA)              │   │
                 │   │     - Dashboard & Live Stats         │   │
                 │   │     - Job Detail & Live Log Viewer   │   │
                 │   │     - Schedule Wizard & Timezones    │   │
                 │   │     - Channel Permission Probing     │   │
                 │   └──────────────────┬───────────────────┘   │
                 │                      │ REST / WebSockets     │
                 │   ┌──────────────────▼───────────────────┐   │
                 │   │      FastAPI Backend Engine          │   │
                 │   │     - JWT Auth & Rate Limiting       │   │
                 │   │     - Channel Cloner & Batching      │   │
                 │   │     - Isolated Per-Bot Rate Limiters │   │
                 │   │     - Persistent Internal Scheduler  │   │
                 │   └──────────┬─────────────────┬─────────┘   │
                 │              │                 │             │
                 │              ▼                 ▼             │
                 │     ┌─────────────────┐  ┌─────────────────┐ │
                 │     │ Telegram Bot    │  │ SQLite Database │ │
                 │     │ API 7.0+ Engine │  │ Volume: /data   │ │
                 │     └─────────────────┘  └─────────────────┘ │
                 └──────────────────────────────────────────────┘
```

---

## 🚢 Portainer Deployment Guide (Recommended)

Follow these steps to deploy directly from GitHub using Portainer:

### 1. Push to GitHub
Fork or push this repository to your GitHub account (public or private):
```bash
git remote add origin https://github.com/YOUR_USERNAME/telegram-channel-cloner.git
git push -u origin main
```

### 2. Open Portainer
1. Log into your Portainer dashboard.
2. Select your Docker environment (e.g. `local` or remote agent).
3. In the left navigation menu, click **Stacks**.
4. Click **+ Add stack**.

### 3. Configure Stack via Git
1. **Name**: `telegram-cloner`
2. **Build method**: Select **Repository**.
3. **Repository URL**: `https://github.com/YOUR_USERNAME/telegram-channel-cloner.git`
   *(If your repository is private, toggle "Authentication" and enter your GitHub username and a Personal Access Token).*
4. **Repository reference**: `refs/heads/main`
5. **Compose path**: `docker-compose.yml`

### 4. Supply Environment Variables
In the **Environment variables** section, click **Add environment variable** for each of the following:

| Variable | Recommended Value | Description |
| :--- | :--- | :--- |
| `APP_PORT` | `8083` | Exposed port on host |
| `ADMIN_USERNAME` | `admin` | Initial admin username |
| `ADMIN_PASSWORD` | `YOUR_SECURE_PASSWORD` | Initial admin password |
| `SECRET_KEY` | *(32+ char random string)* | Encryption key for bot tokens & JWT |
| `MAX_CONCURRENT_JOBS` | `10` | Max simultaneous cloning jobs |
| `LOG_LEVEL` | `INFO` | Application log verbosity |

> [!TIP]
> Generate a strong `SECRET_KEY` on your terminal:
> ```bash
> openssl rand -base64 32
> ```

### 5. Deploy
1. Scroll down and click **Deploy the stack**.
2. Portainer will clone the repository, build the multi-stage Docker image, initialize the database volume, and start the application.
3. Once running, open your browser and navigate to:
   ```text
   http://SERVER_IP:8083
   ```
4. Log in using your `ADMIN_USERNAME` and `ADMIN_PASSWORD`.

---

## 💻 Docker Compose Deployment Guide

To deploy on any server using Docker Compose directly from terminal:

```bash
# 1. Clone the repository
git clone https://github.com/YOUR_USERNAME/telegram-channel-cloner.git
cd telegram-channel-cloner

# 2. Create your .env file
cp .env.example .env
nano .env

# 3. Build and launch the stack
docker compose up -d --build

# 4. Check container health
docker compose ps
docker compose logs -f
```

Access the dashboard at `http://localhost:8083`.

---

## ⚙ Environment Variables

| Variable | Default | Description |
| :--- | :--- | :--- |
| `APP_PORT` | `8083` | Host port to publish the application web UI. |
| `ADMIN_USERNAME` | `admin` | Initial administrator login username. |
| `ADMIN_PASSWORD` | `admin` | Initial administrator login password. Change on first login! |
| `SECRET_KEY` | `change-me` | Secret key used for JWT signing and token encryption at rest. |
| `DATABASE_URL` | `sqlite+aiosqlite:////data/cloner.db` | Database connection URI (defaults to SQLite in Docker volume). |
| `MAX_CONCURRENT_JOBS` | `10` | Maximum number of simultaneous channel cloning tasks. |
| `LOG_LEVEL` | `INFO` | Log level: `DEBUG`, `INFO`, `WARNING`, `ERROR`. |

---

## 🤖 Telegram Bot & Channel Setup

To clone messages between channels, a Telegram Bot is used as the transfer engine:

### 1. Create a Bot via @BotFather
1. Open Telegram and search for [@BotFather](https://t.me/BotFather).
2. Send `/newbot` and follow the prompts to choose a Name and Username.
3. Copy the HTTP API token (e.g. `123456789:ABCdefGhIjkLmNoPqRsTuVwXyZ`).

### 2. Destination Channel Setup (Required)
1. Open your **Destination Channel** on Telegram.
2. Go to **Channel Settings** ➔ **Administrators** ➔ **Add Administrator**.
3. Search for your Bot's username and add it.
4. Ensure the bot has the **Post Messages** permission enabled.

### 3. Source Channel Setup
- **If Source is a Public Channel**: You can use its public `@username` or channel ID.
- **If Source is a Private Channel**: You MUST add the Bot to the private source channel as an Administrator or Member so Telegram allows the bot to read messages.

### 4. Finding Channel IDs
- Telegram channel IDs typically start with `-100` (e.g. `-1001234567890`).
- You can forward any message from the channel to [@userinfobot](https://t.me/userinfobot) or use the Web Telegram client where the channel ID appears in the URL.
- In the dashboard, use the **🔍 Validate Bot Permissions & Probe Channels** button: it will verify both channels and confirm whether your bot has the required posting permissions!

---

## ⏰ Scheduling & Incremental Cloning

### Scheduling Options
When creating or editing a copy job, toggle **Enable Automatic Scheduling**:

- **Every day**: Runs daily at a specific local time (e.g. `01:00`).
- **Every week**: Runs on specified days of the week (e.g. Monday & Thursday at `01:00`).
- **Once**: Runs once at a specific future date and time.
- **Custom (Cron)**: Enter standard cron expressions (e.g. `0 */4 * * *` for every 4 hours).

### Timezone Precision
Every schedule has an explicit timezone (e.g. `Asia/Tehran`, `Europe/Berlin`, `America/New_York`, `UTC`). The application converts schedule times accurately across Daylight Saving Time (DST) changes.

### Overlapping & Missed Executions Policy
- **If previous execution is still running**: Choose whether to **Skip** the next scheduled run (recommended) or allow concurrent runs.
- **If execution was missed (server offline)**: Choose whether to **Run once immediately** upon return (recommended) or skip.

### Incremental Mode
- **Incremental (Recommended)**: On the first run, copies from your starting message ID to the latest post. On every subsequent run (manual or scheduled), it starts from `last_copied_message_id + 1`. Only newly published messages are copied!
- **Full History**: Re-scans all messages starting from message #1 on every run.
- **Specific Range**: Processes strictly between specified Start and End message IDs.

---

## 💾 Backup and Restore

All persistent state (jobs, schedules, bot tokens, execution history, logs) is stored in the Docker volume `cloner_data` at `/data/cloner.db`.

### 1-Click Backup from UI
1. Navigate to **System Settings** in the dashboard.
2. Click **💾 Download Database Backup (.db)**.
3. Save the downloaded database snapshot.

### Backup via Host Terminal
```bash
docker run --rm \
  -v telegram_cloner_data:/data \
  -v $(pwd):/backup \
  alpine cp /data/cloner.db /backup/cloner_backup.db
```

### Restoring on a New Server
1. Deploy the stack on your new server.
2. Stop the container: `docker compose stop`.
3. Copy your backup file into the volume:
   ```bash
   docker run --rm \
     -v telegram_cloner_data:/data \
     -v $(pwd):/backup \
     alpine cp /backup/cloner_backup.db /data/cloner.db
   ```
4. Restart the stack: `docker compose start`.
5. All jobs and schedules will resume automatically!

---

## 🔄 Updating the Stack

### Via Portainer
1. Go to **Stacks** ➔ select `telegram-cloner`.
2. Click **Pull and redeploy**.
3. Toggle **Re-pull image** and **Re-build image**.
4. Click **Update**.

### Via Docker Compose
```bash
git pull origin main
docker compose up -d --build
```

---

## ⚠️ Telegram API Limitations & Best Practices

1. **Protected Content (`has_protected_content`)**:
   If the source channel owner enabled "Restrict saving content" in Channel Settings, Telegram's API strictly forbids copying or forwarding messages (`CHAT_FORWARDS_RESTRICTED`). The engine detects this and logs a clear error without crashing.
2. **Rate Limits & Flood Waits (429)**:
   Telegram enforces a rate limit of ~30 requests/second globally and ~20 messages/minute per chat. The engine automatically handles `429 Too Many Requests` by sleeping for the exact `retry_after` duration returned by Telegram before retrying.
3. **Deleted Messages (Gaps)**:
   Telegram message IDs increment sequentially, but deleted messages leave gaps. The cloner automatically handles missing message IDs, counts them as `Skipped`, and continues without halting.
4. **Media Albums (Groups)**:
   When consecutive media items belong to an album, Bot API 7.0+ `copyMessages` groups them together natively in the destination channel.

---

## 🔧 Troubleshooting

### Container is unhealthy
Check application logs:
```bash
docker compose logs -f telegram-cloner
```
Verify port `8083` is not already used by another service on your server.

### Bot says "Chat not found" or "Forbidden"
- Double-check that your destination channel ID starts with `-100`.
- Verify your Bot is added as an **Administrator** in the destination channel with **Post Messages** permission.
- If the source channel is private, ensure your bot is a member/admin of the source channel.

### Resetting Admin Password
Log into the server and run:
```bash
docker exec -it telegram-channel-cloner python3 -c "
import asyncio
from backend.app.database import AsyncSessionLocal
from backend.app.models import User
from backend.app.security import get_password_hash
from sqlalchemy import select

async def reset():
    async with AsyncSessionLocal() as session:
        user = (await session.execute(select(User))).scalar_one_or_none()
        if user:
            user.hashed_password = get_password_hash('NewPassword123!')
            await session.commit()
            print('Password successfully reset to NewPassword123!')
asyncio.run(reset())
"
```

---

## 🔒 Security

- **Zero committed secrets**: The repository contains no tokens, passwords, or keys.
- **AES-256 Token Encryption**: Bot tokens are encrypted at rest using your `SECRET_KEY`.
- **Token Masking**: Bot tokens are never displayed in full in the browser or logged to stdout.
- **Brute-Force Protection**: Built-in login rate limiter blocks automated password guessing.
- **SQL Injection Prevention**: SQLAlchemy parameterized async queries throughout.

---

## 📄 License

This project is licensed under the [MIT License](LICENSE).
