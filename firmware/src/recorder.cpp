#include <Arduino.h>
#include <cstring>

#include <esp_heap_caps.h>

#include "audio_input.h"
#include "config.h"
#include "recorder.h"

static bool recording = false;
static char activeSessionId[64] = {0};

static int16_t* pcmBuffer = nullptr;
static size_t pcmCapacitySamples = 0;
static size_t pcmSampleCount = 0;

static uint8_t* wavBuffer = nullptr;
static size_t wavBufferSize = 0;
static size_t finalizedWavSize = 0;

static int16_t captureScratch[512];

static size_t writeWavHeader(uint8_t* buf, size_t dataBytes) {
    uint32_t sampleRate = SAMPLE_RATE;
    uint16_t channels = CHANNELS;
    uint16_t bits = BITS_PER_SAMPLE;
    uint32_t byteRate = sampleRate * channels * bits / 8;
    uint16_t blockAlign = channels * bits / 8;

    memcpy(buf, "RIFF", 4);
    uint32_t chunkSize = 36 + (uint32_t)dataBytes;
    memcpy(buf + 4, &chunkSize, 4);
    memcpy(buf + 8, "WAVE", 4);
    memcpy(buf + 12, "fmt ", 4);
    uint32_t fmtSize = 16;
    memcpy(buf + 16, &fmtSize, 4);
    uint16_t audioFormat = 1;
    memcpy(buf + 20, &audioFormat, 2);
    memcpy(buf + 22, &channels, 2);
    memcpy(buf + 24, &sampleRate, 4);
    memcpy(buf + 28, &byteRate, 4);
    memcpy(buf + 32, &blockAlign, 2);
    memcpy(buf + 34, &bits, 2);
    memcpy(buf + 36, "data", 4);
    uint32_t dataSize = (uint32_t)dataBytes;
    memcpy(buf + 40, &dataSize, 4);
    return 44;
}

static bool allocateRecorderBuffers() {
    if (wavBuffer) return true;

    pcmCapacitySamples = (size_t)SAMPLE_RATE * MAX_RECORD_SECONDS;
    const size_t pcmBytes = pcmCapacitySamples * sizeof(int16_t);
    wavBufferSize = 44 + pcmBytes;

    pcmBuffer = (int16_t*)heap_caps_malloc(pcmBytes, MALLOC_CAP_SPIRAM | MALLOC_CAP_8BIT);
    wavBuffer = (uint8_t*)heap_caps_malloc(wavBufferSize, MALLOC_CAP_SPIRAM | MALLOC_CAP_8BIT);

    if (!pcmBuffer || !wavBuffer) {
        // Fallback when PSRAM is unavailable (shorter max recording).
        if (pcmBuffer) heap_caps_free(pcmBuffer);
        if (wavBuffer) heap_caps_free(wavBuffer);
        pcmBuffer = nullptr;
        wavBuffer = nullptr;

        pcmCapacitySamples = (size_t)SAMPLE_RATE * 30;
        const size_t fallbackPcmBytes = pcmCapacitySamples * sizeof(int16_t);
        wavBufferSize = 44 + fallbackPcmBytes;

        pcmBuffer = (int16_t*)heap_caps_malloc(fallbackPcmBytes, MALLOC_CAP_INTERNAL | MALLOC_CAP_8BIT);
        wavBuffer = (uint8_t*)heap_caps_malloc(wavBufferSize, MALLOC_CAP_INTERNAL | MALLOC_CAP_8BIT);

        if (!pcmBuffer || !wavBuffer) {
            Serial.println("[recorder] failed to allocate audio buffers");
            return false;
        }
        Serial.println("[recorder] using internal RAM — max ~30s recording");
    } else {
        Serial.printf("[recorder] PSRAM buffers ready — max %ds\n", MAX_RECORD_SECONDS);
    }

    return true;
}

void recorderInit() {
    allocateRecorderBuffers();
}

bool recorderStart(const char* sessionId) {
    if (!allocateRecorderBuffers()) return false;

    strncpy(activeSessionId, sessionId, sizeof(activeSessionId) - 1);
    activeSessionId[sizeof(activeSessionId) - 1] = '\0';
    pcmSampleCount = 0;
    finalizedWavSize = 0;
    recording = true;

    audioInputStart();
    Serial.printf("[recorder] started session %s\n", activeSessionId);
    return true;
}

void recorderCaptureTick() {
    if (!recording || !pcmBuffer) return;

    size_t remaining = pcmCapacitySamples - pcmSampleCount;
    if (remaining == 0) return;

    size_t toRead = min(remaining, (size_t)512);
    size_t got = audioInputRead(captureScratch, toRead);
    if (got == 0) return;

    memcpy(pcmBuffer + pcmSampleCount, captureScratch, got * sizeof(int16_t));
    pcmSampleCount += got;
}

size_t recorderFinalize() {
    if (!recording || !wavBuffer || !pcmBuffer) return 0;

    recording = false;
    audioInputStop();

    const size_t pcmBytes = pcmSampleCount * sizeof(int16_t);
    writeWavHeader(wavBuffer, pcmBytes);
    memcpy(wavBuffer + 44, pcmBuffer, pcmBytes);
    finalizedWavSize = 44 + pcmBytes;

    Serial.printf("[recorder] finalized %u samples (%.1fs)\n",
                  (unsigned)pcmSampleCount,
                  recorderGetDurationSeconds());
    return finalizedWavSize;
}

const uint8_t* recorderGetWavData() {
    return wavBuffer;
}

size_t recorderGetSampleCount() {
    return pcmSampleCount;
}

float recorderGetDurationSeconds() {
    return (float)pcmSampleCount / (float)SAMPLE_RATE;
}

size_t recorderStop(uint8_t* buffer, size_t maxBytes) {
    size_t total = recorderFinalize();
    if (total == 0 || !buffer) return 0;
    if (maxBytes < total) return 0;
    memcpy(buffer, wavBuffer, total);
    return total;
}
