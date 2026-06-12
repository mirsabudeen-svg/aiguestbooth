#pragma once

#include <stddef.h>
#include <stdint.h>
#include <stdbool.h>

void audioInputInit();
void audioInputStart();
void audioInputStop();
void audioInputFlush();

// Read up to maxSamples of 16-bit mono PCM. Returns samples actually read.
size_t audioInputRead(int16_t* buffer, size_t maxSamples);

bool audioInputIsRunning();
