#include <Arduino.h>
#include "config.h"
#include "state_machine.h"

void ledFeedbackInit() {
    pinMode(PIN_STATUS_LED, OUTPUT);
    digitalWrite(PIN_STATUS_LED, LOW);
}

void ledSetState(BoothState state) {
    switch (state) {
        case STATE_IDLE:
            digitalWrite(PIN_STATUS_LED, LOW);
            break;
        case STATE_RECORDING:
            digitalWrite(PIN_STATUS_LED, HIGH);
            break;
        case STATE_UPLOADING:
            // TODO: pulse pattern
            digitalWrite(PIN_STATUS_LED, HIGH);
            break;
        case STATE_SUCCESS:
            digitalWrite(PIN_STATUS_LED, LOW);
            break;
        case STATE_ERROR:
        case STATE_RETRY:
            // TODO: blink pattern
            digitalWrite(PIN_STATUS_LED, HIGH);
            break;
        default:
            digitalWrite(PIN_STATUS_LED, HIGH);
            break;
    }
}
