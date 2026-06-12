#pragma once

#include <Arduino.h>

extern String deviceToken;

void deviceAuthInit();
bool deviceEnsureRegistered();
bool fetchDeviceConfig();
bool deviceIsAssigned();
const char* deviceGetPromptAudioUrl();
const char* deviceGetThankYouAudioUrl();
void heartbeatSend();
