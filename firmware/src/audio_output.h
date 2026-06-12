#pragma once

#include <stddef.h>
#include <stdint.h>
#include <stdbool.h>

void audioOutputInit();
void audioOutputStop();

bool audioOutputPlayPcm(const int16_t* samples, size_t sampleCount);
bool audioOutputPlayWav(const uint8_t* data, size_t len);
bool audioOutputPlayUrl(const char* url);

// Short confirmation beep — useful for bench testing speaker wiring.
bool audioOutputPlayBeep(uint16_t frequencyHz, uint16_t durationMs);

bool audioOutputIsPlaying();
