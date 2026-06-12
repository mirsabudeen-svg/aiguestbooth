#pragma once

#include <stddef.h>
#include <stdint.h>
#include <stdbool.h>

void recorderInit();

bool recorderStart(const char* sessionId);

// Call frequently while recording to pull I2S mic data into the buffer.
void recorderCaptureTick();

// Finalize WAV in the internal buffer. Returns total byte length (header + PCM).
size_t recorderFinalize();

const uint8_t* recorderGetWavData();
size_t recorderGetSampleCount();
float recorderGetDurationSeconds();

// Legacy helper — copies finalized WAV into caller buffer.
size_t recorderStop(uint8_t* buffer, size_t maxBytes);
