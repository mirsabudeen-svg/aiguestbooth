# X- Audio Guest Booth

Production-oriented event audio guestbook system. Guests record voice messages on an ESP32-S3 booth; a FastAPI backend stores audio, runs AI processing, and powers an operator dashboard.

## Repository structure

```
aiguestbooth/
├── docs/ARCHITECTURE.md    # Full system design (architecture, schema, API, firmware)
├── docs/MVP-ROADMAP.md     # Phased implementation plan
├── backend/                # FastAPI + PostgreSQL
├── frontend/               # Next.js operator dashboard
├── firmware/               # ESP32-S3 PlatformIO project
└── docker-compose.yml      # Postgres + API
```

## Quick start

### 1. Infrastructure

```bash
docker compose up -d postgres
```

### 2. Backend

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate        # Windows
pip install -r requirements.txt
copy .env.example .env
alembic upgrade head
python -m scripts.seed
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

API docs: http://localhost:8000/docs

Default operator login (after seed): `operator@booth.local` / `booth123`

### 3. Frontend

```bash
cd frontend
npm install
copy .env.example .env.local
npm run dev
```

Dashboard: http://localhost:3000

### 4. Device setup

1. Edit `firmware/src/config.h`: `WIFI_SSID`, `WIFI_PASSWORD`, `API_BASE_URL`, `DEVICE_SERIAL` (e.g. `BOOTH-001`).

2. Flash and boot once (auto-registers, saves token to NVS):

```bash
cd firmware
pio run -t upload
pio run -t uploadfs   # LittleFS for offline upload queue
```

3. Assign device to demo booth:

```bash
cd backend
python -m scripts.seed
python -m scripts.provision_device --serial BOOTH-001
```

**NVS recovery:** if token is lost but serial exists in DB, run `python -m scripts.provision_device --rotate-token`.

## MVP flow

1. Guest presses button → ESP32 calls `POST /sessions/start`
2. Device records WAV → `POST /uploads/audio` with checksum
3. Backend stores file, queues AI job (stub in dev)
4. Operator logs in at http://localhost:3000 → views messages, plays audio, downloads ZIP export

**Operator login:** `operator@booth.local` / `booth123`

## Phase 3 (AI pipeline)

Set in `backend/.env`:

```
OPENAI_API_KEY=sk-...
OPENAI_CHAT_MODEL=gpt-4o-mini
OPENAI_WHISPER_MODEL=whisper-1
AI_PIPELINE_ENABLED=true
```

After each upload, the API runs Whisper → GPT enrichment → moderation in a background thread.

Optional standalone worker:

```bash
cd backend && python -m scripts.run_worker
```

Operator UI: open a message at `/messages/{id}` to review/edit transcript, re-run AI, and see processing status.

## Phase 6 (production)

```bash
# AI worker (optional — API also processes in-thread)
docker compose up -d worker

# Retention purge (manual)
cd backend && python -m scripts.purge_retention
```

**Couple delivery:** Events → enable delivery → share `/share/{token}` or print QR from **Booth QR**.

**Moderation:** Approve messages on the message detail page before they appear on the couple page.

**OTA:** Build firmware (`pio run`), upload `firmware.bin` via `POST /api/v1/device/firmware/publish` (admin), set `FIRMWARE_LATEST_VERSION`, reboot booths.

**Render deploy (free, no card):** `render.yaml` uses `plan: free` — API + dashboard + Postgres only (no worker/cron/disk). Open [Blueprint setup](https://dashboard.render.com/blueprint/new?repo=https://github.com/mirsabudeen-svg/aiguestbooth), connect GitHub, click **Apply**. Free tier: services sleep after 15 min idle; Postgres expires after 30 days; uploads are ephemeral (lost on redeploy).

| Service | Variable | Example |
|---------|----------|---------|
| API | `CORS_ORIGINS` | `https://aiguestbooth-dashboard.onrender.com` |
| API | `PUBLIC_API_URL` | `https://aiguestbooth-api.onrender.com` |
| API | `FRONTEND_PUBLIC_URL` | `https://aiguestbooth-dashboard.onrender.com` |
| API | `OPENAI_API_KEY` | `sk-...` (optional) |
| Dashboard | `NEXT_PUBLIC_API_URL` | `https://aiguestbooth-api.onrender.com/api/v1` |

## Documentation

- [Architecture](docs/ARCHITECTURE.md) — system design, API contracts, data model
- [MVP Roadmap](docs/MVP-ROADMAP.md) — week-by-week implementation steps
- [Product handoff](docs/x-audio-guest-booth-handoff.md) — original product spec
