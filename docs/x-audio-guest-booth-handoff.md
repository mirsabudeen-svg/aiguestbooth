# X- Audio Guest Booth

A designer-developer handoff for an AI audio guest phone booth system for weddings, receptions, brand activations, and live events.

This concept is best implemented as a split system: an ESP32-S3 booth device handles audio capture, playback, and local controls, while a FastAPI backend manages sessions, uploads, transcription, AI processing, storage, and operator tools.[cite:24][cite:20][cite:16]

## Product definition

X- Audio Guest Booth is a guided event booth that lets guests leave voice messages through a simple physical interaction model such as a large record button or a handset pickup trigger. The system then stores the raw message, generates a transcript, applies AI post-processing, and exposes the result to operators through an event management interface.[cite:16][cite:12]

The strongest initial product direction is a focused audio guestbook rather than a general-purpose assistant. In noisy event environments, guided recording with explicit start and stop interaction is more reliable than continuous listening or open-ended conversational behavior.[cite:20][cite:16]

## Users and surfaces

### Guest user

The guest experience should feel instant, playful, and low-friction. A guest should be able to understand the action within a few seconds: approach the booth, start recording, speak, finish, and receive a clear confirmation.[cite:16]

### Operator user

The operator needs a controlled interface for booth health, event settings, audio review, error handling, and export operations. This surface should prioritize reliability, status clarity, and speed during live event conditions.[cite:16]

### Admin user

The admin surface should manage events, booth assignment, branding, prompts, AI settings, storage, permissions, and post-event exports. This layer should not leak complexity into the guest-facing flow.[cite:16]

## Hardware architecture

### Core device roles

| Component | Role |
|---|---|
| OceanLabz DIY AI Voice Kit with ESP32-S3 | Main edge device for audio capture, playback, local button state, Wi-Fi connection, and optional camera-linked interactions.[cite:24] |
| INMP441 microphone | Digital I2S microphone for booth voice capture.[cite:24][cite:13] |
| MAX98357 DAC + speaker | I2S audio output for prompts, confirmations, and idle attract audio.[cite:24][cite:13] |
| Camera module | Optional guest snapshot, operator preview, or future audio-video message mode.[cite:24] |
| Arduino Uno | Optional peripheral controller for relays, legacy IO, LEDs, hook switch detection, or simple accessory control; not recommended as the main application controller.[cite:20][cite:24] |

### Device topology

The recommended topology is to treat the ESP32-S3 unit as the booth controller and network edge node. It should manage button input, microphone capture, speaker playback, state LEDs, audio buffering, and upload retries, while the cloud or local server manages identity, AI tasks, dashboards, and storage.[cite:20][cite:16]

## Functional scope

### MVP scope

The first usable release should include:

- Event selection or device-event pairing.
- Idle mode with attract screen or attract audio.
- Start recording via large button or handset pickup.
- Prompt playback before recording.
- Fixed-duration or manually stopped audio capture.
- Upload of recorded audio to backend.
- Session confirmation to guest.
- Operator dashboard with playback and transcript list.
- Event-based storage and export tools.[cite:12][cite:16]

### Phase 2 AI scope

After the MVP is stable, add:

- Speech-to-text transcription.[cite:16]
- Transcript cleanup and punctuation restoration.[cite:16]
- Message summaries and highlight extraction.[cite:16]
- Sentiment or emotion tagging.[cite:16]
- Language detection and multilingual routing.[cite:16]
- Moderation and safety screening for inappropriate content.[cite:16]

### Phase 3 premium scope

Longer-term premium capabilities can include:

- Audio + photo pairing using the camera module.[cite:24]
- Audio + short video guestbook mode.[cite:24]
- Host-branded synthetic voice prompts.[cite:16]
- QR delivery pages for guests or couples.[cite:16]
- Automated memory reels or tribute montages generated from selected clips.[cite:16]
- Analytics by booth, event, time period, and message category.[cite:16]

## Guest experience flow

### Primary flow

1. Idle booth displays branded welcome state.
2. Guest presses “Start” or lifts handset.
3. Booth plays event-specific prompt such as “Leave a message for the couple.”
4. Recording begins with visible recording feedback.
5. Guest speaks for up to the configured duration.
6. Guest presses stop or recording ends automatically.
7. Booth plays thank-you message.
8. Audio uploads in the background.
9. Guest sees success confirmation.[cite:12][cite:16]

### UX principles

The guest flow should be designed around emotional ease rather than feature density. Controls should be physically obvious, copy should be short, and every state should signal confidence: ready, recording, processing, complete, or retry needed.

The booth should avoid conversational complexity in version one. A guided ritual is more appropriate for weddings and event floors than a multi-turn assistant pattern.[cite:20][cite:16]

## Booth state machine

### Device states

| State | Description | Output behavior |
|---|---|---|
| Idle | Waiting for guest input | Ambient light, branded idle screen, optional attract audio |
| Ready | Guest has initiated interaction | Prompt queued or prompt playing |
| Recording | Audio capture active | Red light or waveform animation, mic active |
| Processing | Local buffering or packaging | Short hold indicator |
| Uploading | Sending file to backend | Progress or pulse feedback |
| Success | Upload completed | Thank-you audio and completion state |
| Retry | Upload failed but recoverable | Local queue retained, retry messaging |
| Error | Unrecoverable issue | Operator intervention required |

This state model is important because event hardware needs explicit feedback loops. Ambiguous states create guest hesitation and operator confusion under live conditions.

## Software architecture

### System split

| Layer | Responsibility |
|---|---|
| ESP32-S3 firmware | Capture audio, play prompts, manage IO, encode or package audio, upload files, report device status.[cite:20][cite:24] |
| FastAPI application | Device registration, event configuration, session lifecycle, upload endpoints, transcript jobs, dashboard APIs.[cite:10] |
| Worker layer | Speech-to-text, transcript cleanup, moderation, summaries, tagging, delivery jobs.[cite:16] |
| Storage layer | Raw audio files, derived files, transcripts, event assets, export archives |
| Admin frontend | Event management, booth monitoring, media review, search, tagging, export |

### Recommended stack

- Backend: FastAPI with Pydantic models and modular routers.[cite:10]
- Database: PostgreSQL.
- Background jobs: Celery, Dramatiq, RQ, or a lightweight task queue.
- Object storage: S3-compatible storage or local structured media storage.
- Frontend: React or Next.js dashboard.
- Device communication: HTTPS REST for MVP, with optional WebSocket heartbeat channel later.
- Authentication: booth device token plus operator/admin role-based access.

## Backend modules

A clean backend folder structure should look like this:

```text
backend/
  app/
    main.py
    core/
      config.py
      security.py
      logging.py
    api/
      routes/
        auth.py
        devices.py
        events.py
        sessions.py
        uploads.py
        messages.py
        exports.py
        health.py
    models/
      device.py
      event.py
      booth.py
      session.py
      message.py
      transcript.py
      export.py
    schemas/
      device.py
      event.py
      session.py
      upload.py
      message.py
    services/
      audio_storage.py
      transcription.py
      ai_postprocess.py
      moderation.py
      qr_delivery.py
    workers/
      jobs.py
    db/
      base.py
      session.py
      migrations/
```

This structure fits a production-friendly FastAPI workflow and aligns with the user’s preference for robust, scalable architecture patterns around event systems.[cite:10]

## Data model

### Core entities

| Entity | Purpose |
|---|---|
| Event | Wedding or event record with branding, date, prompts, and configuration |
| Booth | Physical booth assigned to an event |
| Device | Registered ESP32-S3 unit with firmware and health metadata |
| Session | A single guest interaction from start to finish |
| AudioMessage | Stored raw/processed audio tied to a session |
| Transcript | Text output and AI-enriched interpretation |
| OperatorNote | Human review comments or curation metadata |
| ExportJob | Post-event package generation |

### Suggested schema outline

```text
Event
- id
- name
- slug
- event_type
- start_at
- end_at
- venue
- branding_json
- prompt_audio_url
- max_record_seconds
- language_mode
- moderation_enabled
- created_at

Booth
- id
- event_id
- name
- location_label
- status
- assigned_device_id
- created_at

Device
- id
- serial_number
- display_name
- firmware_version
- last_seen_at
- battery_level
- wifi_strength
- status
- auth_token_hash
- created_at

Session
- id
- event_id
- booth_id
- device_id
- started_at
- ended_at
- trigger_type
- status
- upload_status
- local_reference

AudioMessage
- id
- session_id
- raw_audio_path
- normalized_audio_path
- duration_seconds
- file_size_bytes
- mime_type
- checksum
- created_at

Transcript
- id
- audio_message_id
- transcript_text
- cleaned_text
- summary_text
- sentiment_label
- moderation_label
- language_code
- confidence_score
- processed_at
```

## API design

### Device-facing endpoints

| Endpoint | Method | Purpose |
|---|---|---|
| `/v1/device/register` | POST | Register or activate booth device |
| `/v1/device/heartbeat` | POST | Report online status, firmware, signal, and health |
| `/v1/device/config` | GET | Fetch active event config, prompts, and limits |
| `/v1/sessions/start` | POST | Open a guest session |
| `/v1/uploads/audio` | POST | Upload recorded audio file |
| `/v1/sessions/{id}/complete` | POST | Mark booth interaction complete |
| `/v1/device/errors` | POST | Push device-side error reports |

### Operator/admin endpoints

| Endpoint | Method | Purpose |
|---|---|---|
| `/v1/events` | GET/POST | Manage events |
| `/v1/booths` | GET/POST | Manage booths |
| `/v1/messages` | GET | Search and list guest messages |
| `/v1/messages/{id}` | GET/PATCH | Review metadata and edits |
| `/v1/transcripts/{id}` | PATCH | Correct transcript text |
| `/v1/exports` | POST | Generate event export packages |
| `/v1/dashboard/overview` | GET | Live event summary and booth status |

## ESP32 firmware plan

### Firmware responsibilities

The device firmware should do a small number of things extremely well:

- Connect to Wi-Fi securely.
- Pull the current booth configuration.
- Detect trigger input from button or handset logic.
- Play local prompt audio.
- Record microphone input to a buffered audio file.
- Retry uploads when connectivity is weak.
- Surface booth status clearly through LEDs, small display, or speaker cues.[cite:24][cite:20]

### Firmware structure

```text
firmware/
  src/
    main.cpp
    config.h
    wifi_manager.cpp
    device_auth.cpp
    audio_input.cpp
    audio_output.cpp
    recorder.cpp
    uploader.cpp
    session_manager.cpp
    state_machine.cpp
    led_feedback.cpp
    trigger_input.cpp
```

### Device logic notes

Espressif’s ESP-SR framework supports on-device speech recognition on ESP32-S3, which makes it suitable for local wake word or short command handling. For this product, that capability is more useful for optional commands such as “start,” “stop,” or a wake phrase than for full transcription, which should remain on the backend for quality and maintainability.[cite:20][cite:17]

## Reliability design

Event technology must assume bad Wi-Fi, guest impatience, power interruptions, and operator overload. The software should therefore be designed as an offline-tolerant upload system rather than a live-stream dependency.

Required reliability features:

- Local file queue for unsent audio.
- Retry with exponential backoff.
- Upload checksum validation.
- Session IDs generated before recording upload.
- Operator-visible sync status.
- Graceful recovery after reboot.
- Health heartbeat from booth to backend.
- Safe max-duration enforcement to avoid oversized recordings.

## Dashboard requirements

### Operator dashboard

The operator dashboard should show:

- Current event.
- Online/offline booth list.
- Current booth status.
- Number of messages captured.
- Upload failures or retry queue alerts.
- Recent recordings.
- Quick playback and transcript preview.
- Simple controls for prompt testing and booth restart.

### Admin dashboard

The admin dashboard should add:

- Event creation and configuration.
- Multi-event management.
- Booth assignment.
- Branding assets.
- Prompt library management.
- AI processing settings.
- Export and archive tools.
- Role and permission controls.

## AI pipeline design

### Processing stages

1. Raw audio ingestion.
2. Audio normalization.
3. Speech-to-text.
4. Transcript cleanup.
5. Safety or moderation pass.
6. Summary extraction.
7. Sentiment or emotion classification.
8. Storage of structured metadata.
9. Optional curation and reel generation.[cite:16]

### AI outputs per message

| Output | Value |
|---|---|
| Transcript | Searchable text version of the message |
| Clean transcript | Human-friendly punctuation and corrections |
| Summary | Short description of the message content |
| Tags | Family, friends, funny, emotional, advice, blessing, children, etc. |
| Moderation result | Safe, review, blocked |
| Language label | Useful for multilingual events |
| Confidence score | Helps operator review low-quality transcripts |

## UX copy patterns

### Guest copy

Guest-facing copy should be short and emotionally warm. Examples:

- “Pick up the phone to start.”
- “Leave your message after the tone.”
- “Speak from the heart.”
- “Tap stop when you’re done.”
- “Thank you — your message has been saved.”

### Operator copy

Operator-facing copy should be practical and precise. Examples:

- “Booth 2 upload delayed.”
- “Mic signal low.”
- “Prompt audio missing.”
- “3 recordings waiting to sync.”

## Visual and industrial direction

The booth should feel like an event object, not a dev board in a box. A wedding version should present itself as a polished audio guestbook or retro phone experience with concealed electronics, protected IO, clear speaker openings, and physically inviting start controls.

The software should follow the same separation-of-complexity principle already important in the user’s broader photobooth work: the guest surface feels magical and obvious, while the operational surface carries the actual system depth.[cite:8][cite:11]

## Security and privacy

This product captures personal voice data, so privacy controls should be built in from the start. Voice messages, event identity, and operator access should be treated as sensitive by default.[cite:5]

Minimum controls should include:

- Signed device authentication.
- HTTPS-only communication.
- Role-based operator access.
- Secure object storage.
- Configurable retention periods.
- Consent signage for booth usage.
- Audit logs for playback, deletion, and export.
- Event-level isolation of content.[cite:5]

## Suggested implementation roadmap

### Stage 1: Booth prototype

- Wire ESP32-S3, microphone, speaker, trigger button, and power system.
- Record a WAV clip locally.
- Play back a sample prompt.
- Upload the clip to a simple FastAPI endpoint.[cite:24][cite:20]

### Stage 2: Working MVP

- Add event config API.
- Add session creation and upload flow.
- Store files and metadata.
- Build operator message list and playback UI.
- Add transcript job queue.

### Stage 3: Event-ready version

- Add retries, health checks, and sync queue.
- Add live booth monitoring dashboard.
- Add branded prompts and multi-event management.
- Add export package generation.

### Stage 4: Premium productization

- Add AI curation, summaries, and tagging.
- Add QR or couple delivery page.
- Add photo pairing.
- Add curated memory reel export.

## Cursor prompt pack

### Prompt 1: System architecture

```text
Design a production-oriented architecture for an event audio guestbook booth called X- Audio Guest Booth.
Use ESP32-S3 as the edge audio device and FastAPI as the backend.
Return:
1. architecture overview
2. component diagram in text
3. module responsibilities
4. failure handling strategy
5. deployment options for local event server and cloud mode
```

### Prompt 2: FastAPI backend scaffold

```text
Create a FastAPI backend scaffold for X- Audio Guest Booth.
Requirements:
- modular routers
- Pydantic schemas
- PostgreSQL-ready models
- endpoints for device registration, event config, session start, audio upload, session completion, message listing, transcript review, and exports
- production-friendly folder structure
- clear TODO markers for storage and auth integrations
Return code in complete files.
```

### Prompt 3: ESP32 firmware scaffold

```text
Create an ESP32-S3 firmware scaffold for an audio guestbook booth.
Requirements:
- connect to Wi-Fi
- authenticate with backend
- fetch booth config
- start recording on button press
- capture audio from INMP441
- play prompt audio via MAX98357
- upload WAV to backend
- maintain a retry queue when upload fails
- expose clear state machine structure
Use modular C++ files and explain pin mapping assumptions separately.
```

### Prompt 4: Operator dashboard

```text
Build a React admin/operator dashboard for X- Audio Guest Booth.
Requirements:
- booth status cards
- recent recordings list
- audio player
- transcript preview
- event selector
- upload failure alerts
- clean event-tech UI optimized for laptops and tablets
Use component-based architecture and prepare mock data first.
```

### Prompt 5: Database design

```text
Design a PostgreSQL schema for an event audio guestbook platform.
Entities should include events, booths, devices, sessions, audio_messages, transcripts, operators, exports, and audit_logs.
Return SQL schema plus explanation of relationships and indexing strategy.
```

## Final recommendation

The best first commercializable version is a reliable audio guestbook booth with AI enrichment, not a fully conversational assistant. That choice fits the strengths of the ESP32-S3 audio kit, the realities of noisy live events, and the product direction of a premium event-tech system that can later expand into photo, video, and deeper AI features.[cite:24][cite:20][cite:16]
