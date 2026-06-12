/**
 * X- Audio Guest Booth — ESP32-S3 Firmware
 *
 * Flow: Idle → Ready → Recording → Processing → Uploading → Success → Idle
 */

#include <Arduino.h>
#include "config.h"
#include "state_machine.h"
#include "recorder.h"
#include "audio_output.h"
#include "device_auth.h"
#include "uploader.h"

void wifiInit();
bool wifiConnected();
#include "trigger_input.h"
#include "camera_trigger.h"
#include "ota_update.h"
void ledFeedbackInit();
void ledSetState(BoothState state);
void audioInputInit();
void audioOutputInit();
void recorderInit();
bool recorderStart(const char* sessionId);
void recorderCaptureTick();
size_t recorderFinalize();
const uint8_t* recorderGetWavData();
float recorderGetDurationSeconds();
bool sessionStart(const char* triggerType, char* outSessionId, size_t outLen);
bool sessionComplete(const char* sessionId, float durationSec);

unsigned long lastHeartbeatMs = 0;
unsigned long lastConfigRefreshMs = 0;
const unsigned long HEARTBEAT_INTERVAL_MS = 30000;
const unsigned long CONFIG_REFRESH_INTERVAL_MS = 60000;

static void playPrompt() {
    const char* url = deviceGetPromptAudioUrl();
    if (url && audioOutputPlayUrl(url)) return;
    audioOutputPlayBeep(660, 200);
}

static void playThankYou() {
    const char* url = deviceGetThankYouAudioUrl();
    if (url && audioOutputPlayUrl(url)) return;
    audioOutputPlayBeep(880, 150);
    delay(80);
    audioOutputPlayBeep(1175, 200);
}

void setup() {
    Serial.begin(115200);
    delay(500);
    Serial.println("[booth] X- Audio Guest Booth starting");

    ledFeedbackInit();
    triggerInputInit();
    cameraTriggerInit();
    audioInputInit();
    audioOutputInit();
    recorderInit();
    wifiInit();
    deviceAuthInit();
    uploaderInit();

    if (wifiConnected()) {
        deviceEnsureRegistered();
        fetchDeviceConfig();
    }

    audioOutputPlayBeep(880, 120);
    delay(80);
    audioOutputPlayBeep(1175, 120);

    transitionTo(STATE_IDLE);
    ledSetState(STATE_IDLE);
    Serial.println("[booth] ready — press and hold record button");
}

void loop() {
    if (getCurrentState() == STATE_IDLE || getCurrentState() == STATE_RETRY) {
        uploaderProcessQueue();
        if (millis() - lastConfigRefreshMs > CONFIG_REFRESH_INTERVAL_MS && wifiConnected()) {
            fetchDeviceConfig();
            lastConfigRefreshMs = millis();
        }
    }

    if (millis() - lastHeartbeatMs > HEARTBEAT_INTERVAL_MS && wifiConnected()) {
        if (deviceToken.isEmpty()) {
            deviceEnsureRegistered();
        }
        heartbeatSend();
        otaCheckForUpdate();
        lastHeartbeatMs = millis();
    }

    BoothState state = getCurrentState();

    if (state == STATE_IDLE && triggerPressed()) {
        if (!wifiConnected()) {
            Serial.println("[booth] Wi-Fi down — cannot start session");
            transitionTo(STATE_ERROR);
            ledSetState(STATE_ERROR);
            audioOutputPlayBeep(220, 300);
            delay(2000);
            transitionTo(STATE_IDLE);
            ledSetState(STATE_IDLE);
            return;
        }

        if (deviceToken.isEmpty() && !deviceEnsureRegistered()) {
            transitionTo(STATE_ERROR);
            ledSetState(STATE_ERROR);
            return;
        }

        if (!fetchDeviceConfig() || !deviceIsAssigned()) {
            Serial.println("[booth] Device not assigned to a booth — run provision script");
            transitionTo(STATE_ERROR);
            ledSetState(STATE_ERROR);
            audioOutputPlayBeep(220, 400);
            delay(2000);
            transitionTo(STATE_IDLE);
            ledSetState(STATE_IDLE);
            return;
        }

        transitionTo(STATE_READY);
        ledSetState(STATE_READY);

        const char* triggerType = readTriggerType();
        char sessionId[64] = {0};
        if (!sessionStart(triggerType, sessionId, sizeof(sessionId))) {
            transitionTo(STATE_ERROR);
            ledSetState(STATE_ERROR);
            return;
        }

        cameraTriggerPulse();
        playPrompt();

        transitionTo(STATE_RECORDING);
        ledSetState(STATE_RECORDING);

        if (!recorderStart(sessionId)) {
            transitionTo(STATE_ERROR);
            ledSetState(STATE_ERROR);
            return;
        }

        unsigned long recordStart = millis();
        while (triggerPressed() && (millis() - recordStart) < (MAX_RECORD_SECONDS * 1000UL)) {
            recorderCaptureTick();
            delay(1);
        }

        size_t recorded = recorderFinalize();
        float durationSec = recorderGetDurationSeconds();

        if (recorded < 44 + (SAMPLE_RATE / 4)) {
            Serial.println("[booth] recording too short — discarded");
            transitionTo(STATE_IDLE);
            ledSetState(STATE_IDLE);
            return;
        }

        transitionTo(STATE_PROCESSING);
        ledSetState(STATE_PROCESSING);

        sessionComplete(sessionId, durationSec);

        transitionTo(STATE_UPLOADING);
        ledSetState(STATE_UPLOADING);

        int queueBefore = uploaderQueueDepth();
        bool uploadedNow = uploaderEnqueue(sessionId, recorderGetWavData(), recorded);
        bool queuedSafely = uploaderQueueDepth() > queueBefore;

        if (uploadedNow || queuedSafely) {
            if (!uploadedNow) {
                Serial.println("[booth] Upload queued — will retry in background");
                transitionTo(STATE_RETRY);
                ledSetState(STATE_RETRY);
            } else {
                transitionTo(STATE_SUCCESS);
                ledSetState(STATE_SUCCESS);
            }
            playThankYou();
            delay(1500);
            transitionTo(STATE_IDLE);
            ledSetState(STATE_IDLE);
        } else {
            transitionTo(STATE_ERROR);
            ledSetState(STATE_ERROR);
            audioOutputPlayBeep(330, 400);
            delay(2000);
            transitionTo(STATE_IDLE);
            ledSetState(STATE_IDLE);
        }
    }

    delay(10);
}
