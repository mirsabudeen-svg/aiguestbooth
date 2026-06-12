#pragma once

enum BoothState {
    STATE_IDLE = 0,
    STATE_READY,
    STATE_RECORDING,
    STATE_PROCESSING,
    STATE_UPLOADING,
    STATE_SUCCESS,
    STATE_RETRY,
    STATE_ERROR
};

const char* stateToString(BoothState state);
bool transitionTo(BoothState next);
BoothState getCurrentState();
