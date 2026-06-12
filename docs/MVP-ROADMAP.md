# X- Audio Guest Booth — MVP Implementation Roadmap

Phased delivery plan. **MVP = guest can record, upload succeeds, operator can play back.** AI enrichment is Phase 2.

---

## Success Criteria

| Phase | Guest can… | Operator can… | System does… |
|-------|-----------|---------------|--------------|
| MVP | Record & hear confirmation | See messages, play audio | Store WAV + metadata reliably |
| Phase 2 | Same | Read transcripts, search | STT + summary + tags |
| Phase 3 | Branded prompts | Manage events live | Multi-booth monitoring |
| Phase 4 | Photo optional | Export packages | S3, audit, retention |

---

## Phase 0: Foundation (Days 1–3)

### Backend
1. FastAPI app with `/health`, `/api/v1/device/register`, `/api/v1/device/config`
2. PostgreSQL via Docker Compose
3. Alembic migration: events, booths, devices, sessions, audio_messages
4. Local storage service writing to `./storage/{event_id}/{session_id}.wav`

### Firmware
1. PlatformIO project targeting ESP32-S3
2. Wi-Fi connect from `config.h`
3. INMP441 capture → 5-second test WAV to serial/SPIFFS
4. MAX98357 playback of embedded test tone

### Frontend
1. Next.js app shell with layout + nav
2. Mock data pages for dashboard preview

**Exit test:** `curl /health` returns 200; device registers and receives config JSON.

---

## Phase 1: Core Recording Loop (Days 4–7) ✅

### Backend
1. ✅ `POST /sessions/start` — create session, return `session_id`
2. ✅ `POST /uploads/audio` — multipart upload, checksum validation, idempotent
3. ✅ `POST /sessions/{id}/complete` — finalize duration, enqueue processing stub
4. ✅ `POST /device/heartbeat` — update `last_seen_at`, booth status
5. ✅ Assign device → booth via `scripts/provision_device.py`

### Firmware
1. ✅ Full state machine: Idle → Ready → Recording → Processing → Uploading → Success
2. ✅ Button trigger with debounce
3. ✅ Play prompt from config URL (fallback beep if URL missing)
4. ✅ Upload WAV with session_id + SHA256 checksum (multipart POST)
5. ✅ Local retry queue on LittleFS (5 slots, exponential backoff)

### Frontend
- None required yet (use curl/Postman)

**Exit test:** Press button on device → WAV appears in storage → session row in DB with `upload_status=synced`.

---

## Phase 2: Operator Dashboard MVP (Days 8–12) ✅

### Backend
1. ✅ JWT auth: `POST /auth/login`, operator middleware
2. ✅ `GET /messages?event_id=` with pagination (`MessageListResponse`)
3. ✅ `GET /messages/{id}` + authenticated `GET /messages/audio/{event_id}/{session_id}.wav`
4. ✅ `GET /dashboard/overview` — booth online/offline, message count, failed uploads
5. ✅ `POST /exports` + `GET /exports/{id}/download` — ZIP all WAVs for event

### Frontend
1. ✅ Login page
2. ✅ Dashboard overview: booth status cards, live refresh, export button
3. ✅ Messages page: search, pagination, authenticated audio player
4. ✅ Event selector (sidebar dropdown, persisted in localStorage)

**Exit test:** Operator logs in, sees today's messages, plays audio in browser, downloads ZIP export.

---

## Phase 3: AI Pipeline (Days 13–20) ✅

### Backend
1. ✅ `processing_jobs` worker (thread pool + optional `scripts/run_worker.py` poller)
2. ✅ STT via OpenAI Whisper API (`whisper-1`)
3. ✅ Transcript cleanup + summary via GPT (`gpt-4o-mini`)
4. ✅ Sentiment label + OpenAI moderation pass
5. ✅ `message_tags` auto-population
6. ✅ `POST /transcripts/{id}/reprocess`

### Frontend
1. ✅ Message detail page with transcript panel
2. ✅ Edit transcript + summary inline
3. ✅ Tag chips + transcript search (messages list)
4. ✅ Processing status badge (queued / running / completed / failed)

**Exit test:** Upload message → within 2 min transcript appears → operator can search by text.

**Requires:** `OPENAI_API_KEY` in backend `.env`

---

## Phase 4: Event-Ready Hardening (Days 21–28) ✅

1. ✅ Multi-event CRUD in admin UI (`/events`)
2. ✅ Booth assignment UI (`/booths`)
3. ✅ Prompt audio upload to storage (`POST /events/{id}/assets/{type}`)
4. ✅ Branding fields on event (colors, logo URL via `branding_json`)
5. ✅ Audit log on playback/export (retention purge logs deletes)
6. ✅ S3 storage adapter (boto3) with `STORAGE_BACKEND=s3` toggle
7. ✅ Retention policy field on event (`retention_days`, `scripts/purge_retention.py`)
8. ✅ Device error reporting → dashboard alerts
9. ✅ Handset trigger support in firmware (`readTriggerType()`)
10. ✅ Optional camera snapshot endpoint (`POST /uploads/snapshot`) + trigger pulse

**Exit test:** Run two events same day on two booths; operators switch events; no cross-event data leak.

---

## Phase 5: Premium ✅

- ✅ QR delivery page for couples (`/share/{token}`, enable in Events admin)
- ✅ Audio + photo pairing on delivery page (snapshot + audio)
- ✅ Curated memory reel (`format=reel`, star messages, ffmpeg → MP3)
- ✅ Analytics by time/tag/booth (`/analytics`)
- ✅ Host-branded TTS prompts (`POST /events/{id}/tts`)
- ✅ OTA firmware version check (`GET /device/firmware`, firmware logs update URL)

---

## Phase 6: Production & Booth Polish ✅

- ✅ Render Blueprint (`render.yaml`) — API, dashboard, worker, retention cron
- ✅ Docker Compose AI worker service
- ✅ ESP32 HTTP OTA (download + flash when idle)
- ✅ Firmware publish endpoint (`POST /device/firmware/publish`)
- ✅ Booth QR page (`/booth-qr`) for on-site guest scanning
- ✅ Delivery QR in device config (`delivery_qr_url`)
- ✅ Moderation workflow (approve/block → couple page shows `safe` only)
- ✅ Slideshow export (HTML + photos + audio ZIP)

---

## Local Development Commands

```bash
# Start infrastructure
docker compose up -d postgres

# Backend
cd backend
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Frontend
cd frontend
npm install
npm run dev

# Firmware
cd firmware
pio run -t upload
pio device monitor
```

---

## Environment Variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `DATABASE_URL` | `postgresql://booth:booth@localhost:5432/aiguestbooth` | Postgres |
| `STORAGE_BACKEND` | `local` | `local` or `s3` |
| `STORAGE_PATH` | `./storage` | Local audio root |
| `JWT_SECRET` | (required in prod) | Operator tokens |
| `OPENAI_API_KEY` | — | STT + LLM (Phase 3) |
| `S3_BUCKET` | — | Cloud storage (Phase 4) |
| `CORS_ORIGINS` | `http://localhost:3000` | Frontend |

---

## Risk Register

| Risk | Mitigation |
|------|------------|
| Venue Wi-Fi unusable | Local event server on booth LAN; device upload queue |
| Mic picks up crowd noise | Directional mic enclosure; max gain limit in firmware |
| Guests speak too long | Hard cap `max_record_seconds`; auto-stop |
| STT quality poor | Operator edit UI; confidence score flagging |
| Storage fills up | Per-event retention; export then archive |
