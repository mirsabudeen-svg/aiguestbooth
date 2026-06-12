# X- Audio Guest Booth — ESP32-S3 Firmware

## I2S wiring (default pin map)

### INMP441 microphone

| INMP441 | ESP32-S3 |
|---------|----------|
| VDD | 3.3V |
| GND | GND |
| L/R | GND (left channel) |
| SCK / BCLK | GPIO 14 |
| WS / LRCLK | GPIO 15 |
| SD / DOUT | GPIO 32 |

### MAX98357A amplifier

| MAX98357 | ESP32-S3 |
|----------|----------|
| VIN | 5V (or 3.3V per module) |
| GND | GND |
| DIN | GPIO 25 |
| BCLK | GPIO 27 |
| LRC | GPIO 26 |
| GAIN | leave floating or tie per module docs |
| SD | tie high to enable |

Mic uses **I2S port 0** (RX). Speaker uses **I2S port 1** (TX).

## Audio format

- 16 kHz, mono, 16-bit PCM WAV
- Mic captured as 32-bit I2S frames, shifted to 16-bit (`I2S_MIC_SHIFT_BITS` in `config.h`)

## Build & flash

```bash
cd firmware
pio run -t upload
pio device monitor
```

Set in `src/config.h`:

- `WIFI_SSID` / `WIFI_PASSWORD`
- `API_BASE_URL` (e.g. `http://192.168.1.100:8000/api/v1`)
- `DEVICE_SERIAL` (must match `python -m scripts.provision_device --serial`)

## Provisioning

From `backend/` after the device has booted once on Wi-Fi:

```bash
python -m scripts.seed
python -m scripts.provision_device --serial BOOTH-001
```

**Order matters:** flash firmware → first boot (auto-register + NVS) → run provision script to assign booth.

NVS recovery: `python -m scripts.provision_device --rotate-token`

## Upload queue

Failed uploads are saved to LittleFS (`/queue/itemN.wav`) with SHA256 checksum and retried with exponential backoff. Flash the filesystem partition after first code upload:

```bash
pio run -t uploadfs
```

## Boot test

On power-up the speaker plays two short beeps (880 Hz + 1175 Hz). If you hear them, I2S TX to the MAX98357 is working.

Hold the record button (GPIO 0): LED goes high, mic captures until release. Success plays an ascending two-tone chime.

## Tuning

| Symptom | Fix |
|---------|-----|
| Mic too quiet / loud | Adjust `I2S_MIC_SHIFT_BITS` (try 12, 14, or 16) |
| Speaker silent | Check MAX98357 SD pin, 5V power, and DIN/BCLK/LRC |
| Distorted mic | Lower gain; add foam windscreen; move mic away from speaker |
| Recording stops early | Board may lack PSRAM — use ESP32-S3 N8R8 or reduce `MAX_RECORD_SECONDS` |

## PSRAM

Long recordings (~120 s) need PSRAM. `platformio.ini` targets `qio_opi` PSRAM on the S3 DevKit. Without PSRAM, firmware falls back to ~30 s max using internal RAM.
