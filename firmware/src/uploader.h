#pragma once

#include <stddef.h>
#include <stdint.h>
#include <stdbool.h>

void uploaderInit();
int uploaderQueueDepth();

bool uploaderEnqueue(const char* sessionId, const uint8_t* data, size_t len);
bool uploaderProcessQueue();
