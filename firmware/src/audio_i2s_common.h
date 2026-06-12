#pragma once

#include "driver/i2s.h"
#include "config.h"

// IDF 4.x vs 5.x naming differences for legacy I2S driver.
#if defined(I2S_COMM_FORMAT_STAND_I2S)
#define BOOTH_I2S_COMM_FORMAT I2S_COMM_FORMAT_STAND_I2S
#elif defined(I2S_COMM_FORMAT_I2S)
#define BOOTH_I2S_COMM_FORMAT ((i2s_comm_format_t)(I2S_COMM_FORMAT_I2S | I2S_COMM_FORMAT_I2S_MSB))
#else
#define BOOTH_I2S_COMM_FORMAT ((i2s_comm_format_t)0x01)
#endif

static inline i2s_config_t boothMicI2sConfig() {
    i2s_config_t cfg = {};
    cfg.mode = (i2s_mode_t)(I2S_MODE_MASTER | I2S_MODE_RX);
    cfg.sample_rate = SAMPLE_RATE;
    // INMP441 delivers 24-bit samples in a 32-bit I2S slot.
    cfg.bits_per_sample = I2S_BITS_PER_SAMPLE_32BIT;
    cfg.channel_format = I2S_CHANNEL_FMT_ONLY_LEFT;
    cfg.communication_format = BOOTH_I2S_COMM_FORMAT;
    cfg.intr_alloc_flags = ESP_INTR_FLAG_LEVEL1;
    cfg.dma_buf_count = 8;
    cfg.dma_buf_len = 512;
    cfg.use_apll = false;
    cfg.tx_desc_auto_clear = false;
    cfg.fixed_mclk = 0;
    return cfg;
}

static inline i2s_config_t boothSpkI2sConfig() {
    i2s_config_t cfg = {};
    cfg.mode = (i2s_mode_t)(I2S_MODE_MASTER | I2S_MODE_TX);
    cfg.sample_rate = SAMPLE_RATE;
    cfg.bits_per_sample = I2S_BITS_PER_SAMPLE_16BIT;
    cfg.channel_format = I2S_CHANNEL_FMT_ONLY_LEFT;
    cfg.communication_format = BOOTH_I2S_COMM_FORMAT;
    cfg.intr_alloc_flags = ESP_INTR_FLAG_LEVEL1;
    cfg.dma_buf_count = 8;
    cfg.dma_buf_len = 512;
    cfg.use_apll = false;
    cfg.tx_desc_auto_clear = true;
    cfg.fixed_mclk = 0;
    return cfg;
}
