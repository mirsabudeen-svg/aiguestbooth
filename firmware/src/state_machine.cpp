#include "state_machine.h"

static BoothState currentState = STATE_IDLE;

const char* stateToString(BoothState state) {
    switch (state) {
        case STATE_IDLE: return "idle";
        case STATE_READY: return "ready";
        case STATE_RECORDING: return "recording";
        case STATE_PROCESSING: return "processing";
        case STATE_UPLOADING: return "uploading";
        case STATE_SUCCESS: return "success";
        case STATE_RETRY: return "retry";
        case STATE_ERROR: return "error";
        default: return "unknown";
    }
}

bool transitionTo(BoothState next) {
    // Allowed transitions for MVP
    switch (currentState) {
        case STATE_IDLE:
            if (next == STATE_READY || next == STATE_UPLOADING) { currentState = next; return true; }
            break;
        case STATE_READY:
            if (next == STATE_RECORDING || next == STATE_IDLE || next == STATE_ERROR) { currentState = next; return true; }
            break;
        case STATE_RECORDING:
            if (next == STATE_PROCESSING || next == STATE_IDLE || next == STATE_ERROR) { currentState = next; return true; }
            break;
        case STATE_PROCESSING:
            if (next == STATE_UPLOADING || next == STATE_RETRY || next == STATE_ERROR) { currentState = next; return true; }
            break;
        case STATE_UPLOADING:
            if (next == STATE_SUCCESS || next == STATE_RETRY || next == STATE_ERROR) { currentState = next; return true; }
            break;
        case STATE_SUCCESS:
            if (next == STATE_IDLE) { currentState = next; return true; }
            break;
        case STATE_RETRY:
            if (next == STATE_UPLOADING || next == STATE_ERROR || next == STATE_IDLE) { currentState = next; return true; }
            break;
        case STATE_ERROR:
            if (next == STATE_IDLE) { currentState = next; return true; }
            break;
    }
    return false;
}

BoothState getCurrentState() {
    return currentState;
}
