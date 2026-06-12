# X- Audio Guest Booth — System Architecture

Production-oriented event audio guestbook: ESP32-S3 edge device + FastAPI backend + AI pipeline + operator dashboard.

---

## 1. Product Architecture

### 1.1 System Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         EVENT FLOOR (Guest)                              │
│  ┌──────────────────┐                                                    │
│  │  ESP32-S3 Booth  │  Button / Handset → Record → Upload WAV          │
│  │  INMP441 + MAX   │  LEDs / Speaker feedback                          │
│  └────────┬─────────┘                                                    │
└───────────┼─────────────────────────────────────────────────────────────┘
            │ HTTPS REST (device token)
            ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                         BACKEND (FastAPI)                                │
│  ┌─────────────┐  ┌──────────────┐  ┌─────────────┐  ┌───────────────┐  │
│  │ Device API  │  │ Session API  │  │ Upload API  │  │ Dashboard API │  │
│  └──────┬──────┘  └──────┬───────┘  └──────┬──────┘  └───────┬───────┘  │
│         └────────────────┴─────────────────┴─────────────────┘        │
│                                    │                                     │
│                    ┌───────────────┼───────────────┐                    │
│                    ▼               ▼               ▼                    │
│              PostgreSQL      Object Storage    Task Queue               │
│              (metadata)      (audio files)     (AI jobs)                │
└─────────────────────────────────────────────────────────────────────────┘
            │
            ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    WORKERS (Phase 2 — async)                           │
│  STT → Cleanup → Summary → Sentiment → Moderation → Tagging            │
└─────────────────────────────────────────────────────────────────────────┘
            │
            ▼
┌─────────────────────────────────────────────────────────────────────────┐
│              OPERATOR DASHBOARD (Next.js)                                │
│  Events · Booths · Messages · Playback · Transcripts · Export          │
└─────────────────────────────────────────────────────────────────────────┘
```

### 1.2 Design Principles

| Principle | Implementation |
|-----------|----------------|
| Simple guest UX | One action to start, one to stop; no login, no menus |
| Noisy environments | Push-to-talk / handset trigger; fixed max duration; local prompt audio |
| Unreliable Wi-Fi | Local upload queue on device; session ID before record; retry + checksum |
| Operator clarity | Live booth status, sync queue visibility, fast playback |
| Guest/operator separation | Device firmware = guest only; dashboard = operator/admin only |
| MVP first | Record → upload → store → list → play; AI queued but optional in MVP |

### 1.3 Component Responsibilities

| Component | Owns | Does NOT own |
|-----------|------|--------------|
| ESP32-S3 firmware | Audio I/O, state machine, local queue, upload retries | Transcription, user accounts, event CRUD |
| FastAPI API | Auth, sessions, storage paths, metadata, job enqueue | Real-time audio streaming |
| Worker processes | STT, AI enrichment, moderation | HTTP request handling |
| PostgreSQL | Relational metadata, search indexes | Binary audio blobs |
| Object storage | WAV files, prompt assets, exports | Application logic |
| Next.js dashboard | Operator UI, search, review, export triggers | Device firmware |

### 1.4 Deployment Modes

**Local event server** — Single laptop or NUC on venue LAN; PostgreSQL + local `./storage`; devices point to `http://192.168.x.x:8000`.

**Cloud mode** — Render/Fly/Railway for API; managed Postgres; S3/R2 for audio; workers as separate service or same container with background thread (MVP).

### 1.5 Failure Handling

| Failure | Device behavior | Backend behavior |
|---------|-----------------|------------------|
| Wi-Fi drop mid-upload | Retain file in SPIFFS/SD queue; retry with backoff | Idempotent upload by `session_id` + checksum |
| Mic/speaker fault | Transition to `Error`; report via `/device/errors` | Alert on dashboard; booth marked degraded |
| Upload duplicate | N/A | Return 200 with existing `message_id` if checksum matches |
| STT failure | N/A | Message stays `processing_failed`; operator can retry job |
| Power loss | Queue persists on flash; resume on boot | Sessions with `upload_status=pending` flagged |

---

## 2. Folder Structure

```
aiguestbooth/
├── docs/
│   ├── ARCHITECTURE.md          # This document
│   ├── MVP-ROADMAP.md           # Phased implementation plan
│   └── x-audio-guest-booth-handoff.md
│
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI app factory
│   │   ├── core/
│   │   │   ├── config.py        # Settings (env-based)
│   │   │   ├── security.py      # Device + operator auth
│   │   │   └── logging.py
│   │   ├── api/
│   │   │   ├── deps.py          # DI: db, auth, storage
│   │   │   └── routes/
│   │   │       ├── auth.py
│   │   │       ├── devices.py
│   │   │       ├── events.py
│   │   │       ├── booths.py
│   │   │       ├── sessions.py
│   │   │       ├── uploads.py
│   │   │       ├── messages.py
│   │   │       ├── transcripts.py
│   │   │       ├── exports.py
│   │   │       ├── dashboard.py
│   │   │       └── health.py
│   │   ├── models/              # SQLAlchemy ORM
│   │   ├── schemas/             # Pydantic request/response
│   │   ├── services/
│   │   │   ├── audio_storage.py
│   │   │   ├── session_service.py
│   │   │   ├── transcription.py      # Phase 2
│   │   │   ├── ai_postprocess.py     # Phase 2
│   │   │   └── moderation.py         # Phase 2
│   │   ├── workers/
│   │   │   └── jobs.py          # Background task definitions
│   │   └── db/
│   │       ├── base.py
│   │       └── session.py
│   ├── alembic/
│   │   └── versions/
│   ├── tests/
│   ├── requirements.txt
│   ├── Dockerfile
│   └── .env.example
│
├── frontend/
│   ├── src/
│   │   ├── app/                 # Next.js App Router pages
│   │   ├── components/
│   │   ├── lib/api.ts           # API client
│   │   └── types/
│   ├── package.json
│   └── .env.example
│
├── firmware/
│   ├── platformio.ini
│   └── src/
│       ├── main.cpp
│       ├── config.h
│       ├── state_machine.cpp
│       ├── wifi_manager.cpp
│       ├── device_auth.cpp
│       ├── audio_input.cpp
│       ├── audio_output.cpp
│       ├── recorder.cpp
│       ├── uploader.cpp
│       ├── session_manager.cpp
│       ├── led_feedback.cpp
│       └── trigger_input.cpp
│
├── storage/                     # Local audio (gitignored)
├── docker-compose.yml
└── README.md
```

---

## 3. Database Schema

### 3.1 Entity Relationship

```
Event 1──* Booth 1──1 Device (optional assign)
  │            │
  │            └──* Session *──1 AudioMessage 1──1 Transcript
  │                      │
  └──* ExportJob         └──* MessageTag
```

### 3.2 Tables (PostgreSQL)

See `backend/alembic/versions/001_initial_schema.py` for executable migration.

**Core tables:**

| Table | Key columns | Indexes |
|-------|-------------|---------|
| `events` | slug, branding_json, max_record_seconds, prompt_audio_url | `slug` UNIQUE |
| `booths` | event_id, assigned_device_id, status | `event_id`, `status` |
| `devices` | serial_number, auth_token_hash, last_seen_at, firmware_version | `serial_number` UNIQUE |
| `sessions` | event_id, booth_id, device_id, status, upload_status, local_reference | `device_id`, `upload_status`, `started_at` |
| `audio_messages` | session_id, raw_audio_path, checksum, duration_seconds | `session_id` UNIQUE, `checksum` |
| `transcripts` | audio_message_id, transcript_text, cleaned_text, summary_text, sentiment_label, moderation_label | `audio_message_id` UNIQUE |
| `message_tags` | audio_message_id, tag | `(audio_message_id, tag)` |
| `operator_notes` | audio_message_id, author_id, note_text | `audio_message_id` |
| `export_jobs` | event_id, status, output_path | `event_id`, `status` |
| `audit_logs` | actor_type, actor_id, action, resource_type, resource_id | `resource_type, resource_id` |
| `users` | email, password_hash, role (admin/operator) | `email` UNIQUE |
| `processing_jobs` | audio_message_id, job_type, status, attempts | `status`, `audio_message_id` |

### 3.3 Session / Upload Status Enums

```
session.status:       started | recording | completed | abandoned | error
session.upload_status: pending | uploading | synced | failed | retrying
transcript.moderation_label: safe | review | blocked | pending
processing_job.status: queued | running | completed | failed
```

---

## 4. API Design

Base URL: `/api/v1`  
Auth: `Authorization: Bearer <token>` — device tokens for device routes; JWT for operator routes.

### 4.1 Device API

| Method | Path | Request | Response |
|--------|------|---------|----------|
| POST | `/device/register` | `{serial_number, firmware_version}` | `{device_id, token}` |
| POST | `/device/heartbeat` | `{wifi_strength, battery_level, state, queue_depth}` | `{ok: true}` |
| GET | `/device/config` | — | `DeviceConfig` |
| POST | `/sessions/start` | `{trigger_type: "button"\|"handset"}` | `SessionStartResponse` |
| POST | `/uploads/audio` | multipart: `session_id`, `file`, `checksum` | `UploadResponse` |
| POST | `/sessions/{id}/complete` | `{duration_seconds}` | `SessionCompleteResponse` |
| POST | `/device/errors` | `{code, message, session_id?}` | `{ok: true}` |

**DeviceConfig schema:**
```json
{
  "event_id": "uuid",
  "event_name": "Sarah & James",
  "booth_id": "uuid",
  "max_record_seconds": 120,
  "prompt_audio_url": "https://.../prompt.wav",
  "thank_you_audio_url": "https://.../thanks.wav",
  "idle_attract_enabled": true
}
```

### 4.2 Operator / Admin API

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/auth/login` | Operator JWT |
| GET/POST | `/events` | List / create events |
| GET/PATCH | `/events/{id}` | Get / update event |
| GET/POST | `/booths` | Booth CRUD |
| PATCH | `/booths/{id}/assign-device` | Link device to booth |
| GET | `/messages` | `?event_id=&q=&tag=&page=` |
| GET | `/messages/{id}` | Full message + transcript + tags |
| PATCH | `/messages/{id}` | Update metadata, flags |
| GET | `/messages/{id}/audio` | Redirect or stream audio |
| PATCH | `/transcripts/{id}` | Manual transcript correction |
| POST | `/transcripts/{id}/reprocess` | Re-queue AI pipeline |
| POST | `/exports` | `{event_id, format: "zip"\|"csv"}` |
| GET | `/exports/{id}` | Export job status + download URL |
| GET | `/dashboard/overview` | Live stats for active event |

### 4.3 Error Contract

```json
{
  "error": {
    "code": "UPLOAD_CHECKSUM_MISMATCH",
    "message": "Uploaded file checksum does not match",
    "details": {}
  }
}
```

Standard codes: `UNAUTHORIZED`, `DEVICE_NOT_ASSIGNED`, `SESSION_NOT_FOUND`, `SESSION_ALREADY_COMPLETE`, `UPLOAD_TOO_LARGE`, `EVENT_NOT_ACTIVE`.

### 4.4 Idempotency

- `POST /sessions/start` — one active session per device; returns existing if in progress.
- `POST /uploads/audio` — dedupe by `(session_id, checksum)`; safe to retry.
- `POST /sessions/{id}/complete` — idempotent; second call returns same result.

---

## 5. ESP32 Firmware Plan

### 5.1 Hardware Pin Map (default assumptions)

| Signal | GPIO | Notes |
|--------|------|-------|
| I2S mic BCK | 14 | INMP441 |
| I2S mic WS | 15 | |
| I2S mic DATA | 32 | |
| I2S spk BCK | 27 | MAX98357 |
| I2S spk WS | 26 | |
| I2S spk DATA | 25 | |
| Record button | 0 | Active low, debounced |
| Handset hook | 4 | Optional, active low |
| Status LED | 2 | RGB or single |
| Camera trigger | 12 | Optional, pulse on record start |

### 5.2 State Machine

```
        ┌──────┐
        │ IDLE │◄────────────────────────────┐
        └──┬───┘                             │
           │ trigger                          │ timeout / complete
           ▼                                  │
        ┌──────┐    prompt done    ┌───────────┴──┐
        │READY │──────────────────►│  RECORDING   │
        └──┬───┘                   └───────┬──────┘
           │                               │ stop / max duration
           │                               ▼
           │                        ┌────────────┐
           │                        │ PROCESSING │ (encode WAV)
           │                        └─────┬──────┘
           │                              ▼
           │                        ┌────────────┐
           │                        │ UPLOADING  │◄──┐ retry
           │                        └─────┬──────┘   │
           │                              │ success │
           │                              ▼         │
           │                        ┌────────────┐  │
           └───────────────────────►│  SUCCESS   │  │
                                    └────────────┘  │
                                           │        │
                              fail (recoverable)────┘
                                           │
                                           ▼
                                    ┌────────────┐
                                    │   RETRY    │ (queue on flash)
                                    └────────────┘
                                           │ max retries
                                           ▼
                                    ┌────────────┐
                                    │   ERROR    │
                                    └────────────┘
```

### 5.3 Module Responsibilities

| Module | Responsibility |
|--------|----------------|
| `wifi_manager` | Connect, reconnect, signal strength reporting |
| `device_auth` | Store token in NVS; attach to HTTP headers |
| `trigger_input` | Debounce button/handset; emit trigger events |
| `audio_input` | I2S read from INMP441; ring buffer |
| `audio_output` | I2S write to MAX98357; play URL or embedded WAV |
| `recorder` | Buffer → 16-bit PCM WAV; enforce max duration |
| `uploader` | Multipart POST; checksum; exponential backoff |
| `session_manager` | Track session_id; coordinate API calls |
| `state_machine` | Central state transitions + LED/audio cues |
| `led_feedback` | Map state → LED patterns |

### 5.4 Upload Queue (offline tolerance)

- Persist pending uploads as `{session_id, path, checksum, attempts}` in SPIFFS/LittleFS.
- On boot: fetch config → drain queue oldest-first.
- Backoff: 5s, 15s, 45s, 120s (cap at 10 attempts).
- Heartbeat includes `queue_depth` for operator visibility.

### 5.5 Audio Format

- Sample rate: 16000 Hz (STT-friendly) or 44100 Hz (quality); MVP uses **16000 Hz mono 16-bit PCM WAV**.
- Max file size: `max_record_seconds * 32000 + 44` bytes header.

### 5.6 Phase 2 Firmware Additions

- Optional wake word ("start"/"stop") via ESP-SR.
- Camera snapshot on record start (HTTP POST separate endpoint).
- OTA firmware updates.

---

## 6. MVP Implementation Roadmap

### Phase 0 — Foundation (Week 1)
- [x] Architecture + schema + API contracts (this doc)
- [ ] Docker Compose: Postgres + API + storage volume
- [ ] FastAPI scaffold: health, device register, config
- [ ] Alembic initial migration
- [ ] ESP32: Wi-Fi + record 5s WAV locally + serial debug

### Phase 1 — Core Loop (Week 2)
- [ ] Session start/complete endpoints
- [ ] Audio upload with checksum + local storage
- [ ] Device config tied to event/booth assignment
- [ ] ESP32: full state machine + upload
- [ ] Firmware upload retry queue (SPIFFS)

### Phase 2 — Operator MVP (Week 3)
- [ ] JWT auth for operators
- [ ] Next.js dashboard: event selector, booth cards, message list
- [ ] Audio playback in browser
- [ ] Dashboard overview API (live stats)
- [ ] Basic export (ZIP of WAV files)

### Phase 3 — AI Pipeline (Week 4+)
- [ ] `processing_jobs` table + worker runner
- [ ] Whisper / cloud STT integration
- [ ] Transcript cleanup + summary (LLM)
- [ ] Sentiment + moderation labels
- [ ] Transcript review UI + reprocess button
- [ ] Search by transcript text

### Phase 4 — Event-Ready (Week 5+)
- [ ] Multi-event management + branding uploads
- [ ] Prompt audio management
- [ ] Audit logs
- [ ] S3-compatible storage adapter
- [ ] Health alerts + operator notifications
- [ ] Optional camera trigger endpoint

### Phase 5 — Premium
- [x] QR delivery pages for couples
- [x] Photo pairing
- [x] Memory reel export
- [x] Analytics dashboard

---

## API Contract Quick Reference (Pydantic)

All schemas live in `backend/app/schemas/`. Key types:

- `DeviceRegisterRequest`, `DeviceRegisterResponse`
- `DeviceConfigResponse`
- `SessionStartRequest`, `SessionStartResponse`
- `AudioUploadResponse`
- `MessageListItem`, `MessageDetail`
- `TranscriptUpdate`, `DashboardOverview`
- `EventCreate`, `EventResponse`, `BoothCreate`

See scaffold code for full field definitions.
