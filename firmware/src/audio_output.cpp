#include <Arduino.h>
#include <cstring>
#include <math.h>
#include <HTTPClient.h>

#include "audio_output.h"
#include "audio_i2s_common.h"
#include "config.h"

static const i2s_port_t I2S_SPK_PORT = I2S_NUM_1;
static bool spkInstalled = false;
static bool spkPlaying = false;

void audioOutputInit() {
    if (spkInstalled) return;

    i2s_config_t cfg = boothSpkI2sConfig();
    esp_err_t err = i2s_driver_install(I2S_SPK_PORT, &cfg, 0, nullptr);
    if (err != ESP_OK) {
        Serial.printf("[i2s-spk] driver install failed: %d\n", err);
        return;
    }

    i2s_pin_config_t pins = {};
    pins.bck_io_num = I2S_SPK_BCK;
    pins.ws_io_num = I2S_SPK_WS;
    pins.data_out_num = I2S_SPK_DATA;
    pins.data_in_num = I2S_PIN_NO_CHANGE;

    err = i2s_set_pin(I2S_SPK_PORT, &pins);
    if (err != ESP_OK) {
        Serial.printf("[i2s-spk] set pin failed: %d\n", err);
        i2s_driver_uninstall(I2S_SPK_PORT);
        return;
    }

    i2s_zero_dma_buffer(I2S_SPK_PORT);
    spkInstalled = true;
    Serial.println("[i2s-spk] MAX98357 ready");
}

void audioOutputStop() {
    if (!spkInstalled) return;
    spkPlaying = false;
    i2s_zero_dma_buffer(I2S_SPK_PORT);
}

bool audioOutputIsPlaying() {
    return spkPlaying;
}

static bool writePcmToSpeaker(const int16_t* samples, size_t sampleCount) {
    if (!spkInstalled || !samples || sampleCount == 0) return false;

    spkPlaying = true;
    const size_t chunk = 512;
    size_t offset = 0;

    while (offset < sampleCount) {
        size_t n = min(chunk, sampleCount - offset);
        size_t bytesWritten = 0;
        esp_err_t err = i2s_write(
            I2S_SPK_PORT,
            samples + offset,
            n * sizeof(int16_t),
            &bytesWritten,
            pdMS_TO_TICKS(200)
        );
        if (err != ESP_OK || bytesWritten == 0) {
            spkPlaying = false;
            return false;
        }
        offset += bytesWritten / sizeof(int16_t);
    }

    spkPlaying = false;
    return true;
}

bool audioOutputPlayPcm(const int16_t* samples, size_t sampleCount) {
    return writePcmToSpeaker(samples, sampleCount);
}

static bool parseWavPcm(
    const uint8_t* data,
    size_t len,
    uint16_t* outChannels,
    uint32_t* outSampleRate,
    uint16_t* outBits,
    const uint8_t** outPcm,
    size_t* outPcmBytes
) {
    if (!data || len < 44) return false;
    if (memcmp(data, "RIFF", 4) != 0 || memcmp(data + 8, "WAVE", 4) != 0) return false;

    size_t pos = 12;
    uint16_t channels = 0;
    uint32_t sampleRate = 0;
    uint16_t bits = 0;
    const uint8_t* pcm = nullptr;
    size_t pcmBytes = 0;

    while (pos + 8 <= len) {
        const char* chunkId = (const char*)(data + pos);
        uint32_t chunkSize = 0;
        memcpy(&chunkSize, data + pos + 4, 4);
        pos += 8;

        if (pos + chunkSize > len) break;

        if (memcmp(chunkId, "fmt ", 4) == 0 && chunkSize >= 16) {
            uint16_t audioFormat = 0;
            memcpy(&audioFormat, data + pos, 2);
            memcpy(&channels, data + pos + 2, 2);
            memcpy(&sampleRate, data + pos + 4, 4);
            memcpy(&bits, data + pos + 14, 2);
            if (audioFormat != 1) return false;  // PCM only
        } else if (memcmp(chunkId, "data", 4) == 0) {
            pcm = data + pos;
            pcmBytes = chunkSize;
        }

        pos += chunkSize + (chunkSize & 1);
    }

    if (!pcm || pcmBytes == 0 || bits != 16) return false;

    *outChannels = channels;
    *outSampleRate = sampleRate;
    *outBits = bits;
    *outPcm = pcm;
    *outPcmBytes = pcmBytes;
    return true;
}

bool audioOutputPlayWav(const uint8_t* data, size_t len) {
    uint16_t channels = 0;
    uint32_t sampleRate = 0;
    uint16_t bits = 0;
    const uint8_t* pcm = nullptr;
    size_t pcmBytes = 0;

    if (!parseWavPcm(data, len, &channels, &sampleRate, &bits, &pcm, &pcmBytes)) {
        Serial.println("[i2s-spk] unsupported WAV format");
        return false;
    }

    if (sampleRate != (uint32_t)SAMPLE_RATE) {
        Serial.printf("[i2s-spk] WAV rate %lu != %d — playback may sound wrong\n",
                      (unsigned long)sampleRate, SAMPLE_RATE);
    }

    const int16_t* samples = (const int16_t*)pcm;
    size_t sampleCount = pcmBytes / sizeof(int16_t);

    // Downmix stereo to mono if needed.
    if (channels == 2) {
        static int16_t monoScratch[1024];
        size_t offset = 0;
        while (offset < sampleCount) {
            size_t frames = min((size_t)1024, (sampleCount - offset) / 2);
            for (size_t i = 0; i < frames; i++) {
                int32_t left = samples[offset + i * 2];
                int32_t right = samples[offset + i * 2 + 1];
                monoScratch[i] = (int16_t)((left + right) / 2);
            }
            if (!writePcmToSpeaker(monoScratch, frames)) return false;
            offset += frames * 2;
        }
        return true;
    }

    if (channels != 1) return false;
    return writePcmToSpeaker(samples, sampleCount);
}

bool audioOutputPlayUrl(const char* url) {
    if (!url || url[0] == '\0' || !spkInstalled) return false;

    HTTPClient http;
    http.begin(url);
    int code = http.GET();
    if (code != 200) {
        Serial.printf("[i2s-spk] prompt download failed HTTP %d\n", code);
        http.end();
        return false;
    }

    int contentLen = http.getSize();
    if (contentLen <= 0 || contentLen > 512 * 1024) {
        Serial.println("[i2s-spk] prompt file missing or too large");
        http.end();
        return false;
    }

    uint8_t* buffer = (uint8_t*)malloc((size_t)contentLen);
    if (!buffer) {
        http.end();
        return false;
    }

    WiFiClient* stream = http.getStreamPtr();
    size_t offset = 0;
    while (http.connected() && offset < (size_t)contentLen) {
        size_t avail = stream->available();
        if (avail) {
            int read = stream->readBytes(buffer + offset, avail);
            if (read > 0) offset += (size_t)read;
        } else {
            delay(1);
        }
    }
    http.end();

    bool ok = audioOutputPlayWav(buffer, offset);
    free(buffer);
    return ok;
}

bool audioOutputPlayBeep(uint16_t frequencyHz, uint16_t durationMs) {
    if (!spkInstalled || frequencyHz == 0 || durationMs == 0) return false;

    const size_t sampleCount = (SAMPLE_RATE * durationMs) / 1000;
    int16_t* buf = (int16_t*)malloc(sampleCount * sizeof(int16_t));
    if (!buf) return false;

    const float amplitude = 12000.0f;
    for (size_t i = 0; i < sampleCount; i++) {
        float t = (float)i / (float)SAMPLE_RATE;
        buf[i] = (int16_t)(sinf(2.0f * PI * frequencyHz * t) * amplitude);
    }

    bool ok = writePcmToSpeaker(buf, sampleCount);
    free(buf);
    return ok;
}
