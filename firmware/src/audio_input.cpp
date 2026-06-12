#include <Arduino.h>
#include <cstring>

#include "audio_input.h"
#include "audio_i2s_common.h"
#include "config.h"

static const i2s_port_t I2S_MIC_PORT = I2S_NUM_0;
static bool micRunning = false;
static bool micInstalled = false;

// INMP441: 24-bit left-justified in 32-bit slot — shift down to 16-bit PCM.
#ifndef I2S_MIC_SHIFT_BITS
#define I2S_MIC_SHIFT_BITS 14
#endif

static int16_t convertMicSample(int32_t raw) {
    int32_t shifted = raw >> I2S_MIC_SHIFT_BITS;
    if (shifted > 32767) shifted = 32767;
    if (shifted < -32768) shifted = -32768;
    return (int16_t)shifted;
}

void audioInputInit() {
    if (micInstalled) return;

    i2s_config_t cfg = boothMicI2sConfig();
    esp_err_t err = i2s_driver_install(I2S_MIC_PORT, &cfg, 0, nullptr);
    if (err != ESP_OK) {
        Serial.printf("[i2s-mic] driver install failed: %d\n", err);
        return;
    }

    i2s_pin_config_t pins = {};
    pins.bck_io_num = I2S_MIC_BCK;
    pins.ws_io_num = I2S_MIC_WS;
    pins.data_out_num = I2S_PIN_NO_CHANGE;
    pins.data_in_num = I2S_MIC_DATA;

    err = i2s_set_pin(I2S_MIC_PORT, &pins);
    if (err != ESP_OK) {
        Serial.printf("[i2s-mic] set pin failed: %d\n", err);
        i2s_driver_uninstall(I2S_MIC_PORT);
        return;
    }

    i2s_zero_dma_buffer(I2S_MIC_PORT);
    micInstalled = true;
    Serial.println("[i2s-mic] INMP441 ready");
}

void audioInputFlush() {
    if (!micInstalled) return;
    int32_t discard[128];
    size_t bytesRead = 0;
    i2s_read(I2S_MIC_PORT, discard, sizeof(discard), &bytesRead, pdMS_TO_TICKS(20));
}

void audioInputStart() {
    if (!micInstalled) {
        audioInputInit();
    }
    if (!micInstalled) return;

    audioInputFlush();
    micRunning = true;
}

void audioInputStop() {
    micRunning = false;
}

bool audioInputIsRunning() {
    return micRunning;
}

size_t audioInputRead(int16_t* buffer, size_t maxSamples) {
    if (!micInstalled || !buffer || maxSamples == 0) return 0;

    // Read 32-bit mic frames, convert to 16-bit mono.
    const size_t chunkSamples = min(maxSamples, (size_t)256);
    int32_t raw[256];
    size_t bytesRead = 0;

    esp_err_t err = i2s_read(
        I2S_MIC_PORT,
        raw,
        chunkSamples * sizeof(int32_t),
        &bytesRead,
        pdMS_TO_TICKS(50)
    );

    if (err != ESP_OK || bytesRead == 0) return 0;

    size_t samplesRead = bytesRead / sizeof(int32_t);
    for (size_t i = 0; i < samplesRead; i++) {
        buffer[i] = convertMicSample(raw[i]);
    }
    return samplesRead;
}
