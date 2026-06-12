#pragma once

// Wi-Fi — set via build flags or edit before flash
#ifndef WIFI_SSID
#define WIFI_SSID "YOUR_WIFI_SSID"
#endif
#ifndef WIFI_PASSWORD
#define WIFI_PASSWORD "YOUR_WIFI_PASSWORD"
#endif

// Backend
#ifndef API_BASE_URL
#define API_BASE_URL "http://192.168.1.100:8000/api/v1"
#endif

// Device identity — must match provision script serial
#ifndef DEVICE_SERIAL
#define DEVICE_SERIAL "BOOTH-001"
#endif

#ifndef FIRMWARE_VERSION
#define FIRMWARE_VERSION "0.2.0"
#endif

// I2S Microphone (INMP441)
#define I2S_MIC_BCK 14
#define I2S_MIC_WS  15
#define I2S_MIC_DATA 32

// I2S Speaker (MAX98357)
#define I2S_SPK_BCK  27
#define I2S_SPK_WS   26
#define I2S_SPK_DATA 25

// Inputs / outputs
#define PIN_RECORD_BUTTON 0
#define PIN_HANDSET_HOOK  4
#define PIN_STATUS_LED    2
#define PIN_CAMERA_TRIGGER 12

// Audio
#define SAMPLE_RATE 16000
#define BITS_PER_SAMPLE 16
#define CHANNELS 1
#define MAX_RECORD_SECONDS 120
#define UPLOAD_QUEUE_MAX 5

// INMP441: 24-bit sample left-justified in 32-bit slot. Tune 12–16 if level is off.
#define I2S_MIC_SHIFT_BITS 14

// Upload retry backoff (ms)
static const unsigned long UPLOAD_RETRY_DELAYS_MS[] = {5000, 15000, 45000, 120000};
static const size_t UPLOAD_RETRY_DELAYS_COUNT = 4;
static const uint8_t UPLOAD_MAX_ATTEMPTS = 10;
