#include <Arduino.h>
#include "config.h"
#include "trigger_input.h"

static bool lastButtonState = HIGH;
static unsigned long lastDebounceMs = 0;
const unsigned long DEBOUNCE_MS = 50;

void triggerInputInit() {
    pinMode(PIN_RECORD_BUTTON, INPUT_PULLUP);
    pinMode(PIN_HANDSET_HOOK, INPUT_PULLUP);
}

const char* readTriggerType() {
    bool button = digitalRead(PIN_RECORD_BUTTON) == LOW;
    bool handset = digitalRead(PIN_HANDSET_HOOK) == LOW;
    if (handset && !button) {
        return "handset";
    }
    return "button";
}

bool triggerPressed() {
    bool reading = digitalRead(PIN_RECORD_BUTTON) == LOW;
    bool handset = digitalRead(PIN_HANDSET_HOOK) == LOW;

    if (reading != lastButtonState) {
        lastDebounceMs = millis();
    }
    lastButtonState = reading;

    if ((millis() - lastDebounceMs) > DEBOUNCE_MS) {
        return reading || handset;
    }
    return false;
}
