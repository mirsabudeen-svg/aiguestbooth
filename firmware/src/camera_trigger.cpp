#include <Arduino.h>
#include "config.h"
#include "camera_trigger.h"

void cameraTriggerInit() {
    pinMode(PIN_CAMERA_TRIGGER, OUTPUT);
    digitalWrite(PIN_CAMERA_TRIGGER, HIGH);
}

void cameraTriggerPulse() {
    digitalWrite(PIN_CAMERA_TRIGGER, LOW);
    delay(120);
    digitalWrite(PIN_CAMERA_TRIGGER, HIGH);
}
