# NEXORA POSITION — VPS Deployment Guide

> **Scope:** GitHub → VPS → NEXORA Bot → Telegram  
> **Mode:** Simulated position image generator. Public Binance market data only. Zero trade execution.

---

## 1. Requirements Summary

| Item | Detail |
|---|---|
| **Python Version** | **3.11 minimum**, 3.12 or 3.13 recommended (codebase uses `str | int` union type hints, `tuple[...]` generics — Python ≥ 3.10; `python-telegram-bot==22.8` best on 3.11+) |
| **Docker** | ✅ `Dockerfile` already present and configured |
| **docker-compose.yml** | ❌ Not present — must be created on VPS (see Section 4.1) |
| **Entry Point** | `python -m app.main` |
| **Binance Access** | Public market data only: `GET /fapi/v1/exchangeInfo`, `GET /fapi/v1/premiumIndex` |

---

## 2. Required Environment Variables

Copy from `.env.example` and fill in only `TELEGRAM_BOT_TOKEN`:

```env
# REQUIRED — Your BotFather token
TELEGRAM_BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrsTUVwxyz

# Optional — Telegram Chat ID (not currently used by bot logic)
TELEGRAM_CHAT_ID=

# Binance Public Market Data (do NOT change)
BINANCE_BASE_URL=https://fapi.binance.com
BINANCE_WS_URL=wss://fstream.binance.com/ws

# Simulation defaults
DEFAULT_MAX_LEVERAGE=125
DEFAULT_MODE=MOCK

# Card renderer dimensions
IMAGE_WIDTH=1080
IMAGE_HEIGHT=650

# Logging (DEBUG for troubleshooting, INFO for production)
LOG_LEVEL=INFO
```

> **NEVER** add Binance API keys, secrets, or account credentials.
> The bot uses only **unauthenticated public endpoints**. No authentication required.

---

## 3. VPS Package Requirements

### Minimum VPS Specs
- **OS:** Ubuntu 22.04 LTS or 24.04 LTS
- **RAM:** 512 MB minimum, 1 GB recommended (Pillow PNG rendering)
- **Storage:** 2 GB free
- **CPU:** 1 vCPU minimum
- **Network:** Outbound HTTPS to `api.telegram.org` and `fapi.binance.com`

### Option A — Docker (Recommended)

```bash
sudo apt-get update && sudo apt-get install -y \
    git \
    docker.io \
    docker-compose-plugin

sudo systemctl enable docker
sudo systemctl start docker
sudo usermod -aG docker $USER
newgrp docker
```

### Option B — Direct Python (No Docker)

```bash
sudo apt-get update && sudo apt-get install -y \
    git \
    python3.13 \
    python3.13-venv \
    python3.13-dev \
    python3-pip \
    fonts-dejavu-core \
    fonts-liberation \
    libfontconfig1
```

> `fonts-dejavu-core` and `fonts-liberation` are required as system font fallbacks for Pillow's PNG renderer (same packages installed in the Dockerfile).

---

## 4. Docker Deployment (Recommended)

### 4.1 docker-compose.yml

Create this file on the VPS **after cloning** — do NOT commit it to git:

```yaml
# docker-compose.yml — NEXORA POSITION VPS deployment
# Place on VPS alongside .env — do NOT commit to git

version: "3.9"

services:
  nexora-bot:
    build: .
    container_name: nexora_position_bot
    restart: unless-stopped
    env_file:
      - .env
    volumes:
      - ./data:/app/data
      - ./output:/app/output
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
```

### 4.2 Full Docker Deployment Steps

```bash
# 1. Clone the repository
git clone https://github.com/roxy4798/NEXORA-CARD.git
cd NEXORA-CARD

# 2. Create .env from example
cp .env.example .env
nano .env   # Set TELEGRAM_BOT_TOKEN=<your-real-token>

# 3. Create docker-compose.yml (paste YAML from 4.1)
nano docker-compose.yml

# 4. Build Docker image
docker compose build

# 5. Start the bot (daemonized)
docker compose up -d

# 6. Verify running
docker compose ps
docker compose logs -f --tail=50
```

---

## 5. Direct Python Deployment (No Docker)

```bash
# 1. Clone repository
git clone https://github.com/roxy4798/NEXORA-CARD.git
cd NEXORA-CARD

# 2. Create virtual environment
python3.13 -m venv .venv
source .venv/bin/activate

# 3. Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# 4. Set up environment
cp .env.example .env
nano .env   # Set TELEGRAM_BOT_TOKEN

# 5. Create runtime directories
mkdir -p data output

# 6. Run tests to verify
pytest -q
# Expected: 87 passed / 0 failed

# 7. Start the bot
python -m app.main
```

### 5.1 Keep Alive with systemd (Recommended for Direct Python)

Create `/etc/systemd/system/nexora-bot.service`:

```ini
[Unit]
Description=NEXORA POSITION Telegram Bot
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/NEXORA-CARD
ExecStart=/home/ubuntu/NEXORA-CARD/.venv/bin/python -m app.main
Restart=always
RestartSec=5
EnvironmentFile=/home/ubuntu/NEXORA-CARD/.env
StandardOutput=journal
StandardError=journal
SyslogIdentifier=nexora-bot

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable nexora-bot
sudo systemctl start nexora-bot

# Monitor logs
sudo journalctl -u nexora-bot -f
```

---

## 6. Update Workflow (Pull Latest Code)

### Docker

```bash
cd NEXORA-CARD
git pull origin main
docker compose down
docker compose build --no-cache
docker compose up -d
docker compose logs -f --tail=30
```

### Direct Python + systemd

```bash
cd NEXORA-CARD
git pull origin main
source .venv/bin/activate
pip install -r requirements.txt        # only if requirements changed
sudo systemctl restart nexora-bot
sudo journalctl -u nexora-bot -f
```

---

## 7. Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `ConnectTimeout` on startup | Telegram API unreachable from VPS | `curl -s https://api.telegram.org` — check VPS firewall |
| Bot starts but in "demo mode" | Empty `TELEGRAM_BOT_TOKEN` | Fill token in `.env` |
| Font rendering issues | Missing system fonts | `apt install fonts-dejavu-core fonts-liberation` |
| `data/positions.json` permission error | Wrong file ownership | `chown -R ubuntu:ubuntu ./data ./output` |
| `ModuleNotFoundError` | venv not activated or bad install | `source .venv/bin/activate && pip install -r requirements.txt` |

### Verify Network from VPS

```bash
# Check Telegram API reachability
curl -s https://api.telegram.org | head -1

# Check Binance public API reachability
curl -s "https://fapi.binance.com/fapi/v1/ping"
# Expected: {}
```

---

## 8. Security Notes

- `.env` is in `.gitignore` — never in GitHub
- No Binance API keys required — public endpoints only
- `tests/test_security_safety.py` enforces zero trade execution endpoints at test level
- Logs automatically sanitize Telegram tokens via `SensitiveFilter` regex (`logging_config.py`)
- VPS firewall: only **outbound** port 443 (HTTPS) needed; no inbound ports required (bot uses long-polling, not webhook)

---

## 9. Deployment Checklist

```
[ ] VPS running Ubuntu 22.04 or 24.04
[ ] Git and Docker (or Python 3.11+) installed
[ ] Repository cloned: git clone https://github.com/roxy4798/NEXORA-CARD.git
[ ] .env created and TELEGRAM_BOT_TOKEN filled in
[ ] docker-compose.yml created (if using Docker)
[ ] data/ and output/ directories exist with correct permissions
[ ] pytest -q passes: 87 passed, 0 failed
[ ] Bot started: docker compose up -d  OR  python -m app.main
[ ] Logs show "Starting Telegram Bot polling..."
[ ] Telegram /start command responded correctly
[ ] /position command generates position card PNG successfully
[ ] No errors in logs
```
