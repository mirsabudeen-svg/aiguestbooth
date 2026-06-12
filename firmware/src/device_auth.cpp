#include <Preferences.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>

#include "config.h"
#include "device_auth.h"
#include "state_machine.h"
#include "uploader.h"

extern int wifiSignalStrength();

static Preferences prefs;
String deviceToken;
static String deviceId;

static char promptAudioUrl[256] = {0};
static char thankYouAudioUrl[256] = {0};
static bool configAssigned = false;

static void clearCachedConfig() {
    promptAudioUrl[0] = '\0';
    thankYouAudioUrl[0] = '\0';
    configAssigned = false;
}

void deviceAuthInit() {
    prefs.begin("booth", false);
    deviceToken = prefs.getString("token", "");
    deviceId = prefs.getString("device_id", "");
    clearCachedConfig();

    if (deviceToken.isEmpty()) {
        Serial.println("[auth] No token in NVS — will register on first Wi-Fi connect");
    } else {
        Serial.printf("[auth] Loaded device %s from NVS\n", deviceId.c_str());
    }
}

static bool saveCredentials(const char* token, const char* id) {
    if (!token || !id || token[0] == '\0' || id[0] == '\0') return false;

    prefs.putString("token", token);
    prefs.putString("device_id", id);
    deviceToken = token;
    deviceId = id;
    Serial.printf("[auth] Credentials saved to NVS (device %s)\n", id);
    return true;
}

bool deviceEnsureRegistered() {
    if (!deviceToken.isEmpty()) return true;
    if (!wifiConnected()) {
        Serial.println("[auth] Wi-Fi required for registration");
        return false;
    }

    HTTPClient http;
    String url = String(API_BASE_URL) + "/device/register";
    http.begin(url);
    http.addHeader("Content-Type", "application/json");

    JsonDocument body;
    body["serial_number"] = DEVICE_SERIAL;
    body["firmware_version"] = FIRMWARE_VERSION;
    body["display_name"] = DEVICE_SERIAL;
    String payload;
    serializeJson(body, payload);

    int code = http.POST(payload);
    String response = http.getString();
    http.end();

    if (code == 409) {
        Serial.println("[auth] Serial already registered — run backend provision script with --rotate-token");
        return false;
    }

    if (code != 200 && code != 201) {
        Serial.printf("[auth] Registration failed HTTP %d: %s\n", code, response.c_str());
        return false;
    }

    JsonDocument doc;
    if (deserializeJson(doc, response)) {
        Serial.println("[auth] Invalid registration response JSON");
        return false;
    }

    const char* token = doc["token"];
    const char* id = doc["device_id"];
    if (!token || !id) {
        Serial.println("[auth] Registration response missing token or device_id");
        return false;
    }

    return saveCredentials(token, id);
}

bool fetchDeviceConfig() {
    if (deviceToken.isEmpty()) return false;

    HTTPClient http;
    String url = String(API_BASE_URL) + "/device/config";
    http.begin(url);
    http.addHeader("Authorization", "Bearer " + deviceToken);

    int code = http.GET();
    if (code != 200) {
        Serial.printf("[config] Failed: HTTP %d\n", code);
        http.end();
        return false;
    }

    String response = http.getString();
    http.end();

    JsonDocument doc;
    if (deserializeJson(doc, response)) return false;

    configAssigned = doc["assigned"] | false;

    const char* prompt = doc["prompt_audio_url"] | "";
    const char* thanks = doc["thank_you_audio_url"] | "";
    strncpy(promptAudioUrl, prompt, sizeof(promptAudioUrl) - 1);
    strncpy(thankYouAudioUrl, thanks, sizeof(thankYouAudioUrl) - 1);

    Serial.printf("[config] assigned=%d event=%s booth=%s\n",
                  configAssigned,
                  doc["event_name"] | "none",
                  doc["booth_name"] | "none");
    return configAssigned;
}

bool deviceIsAssigned() {
    return configAssigned;
}

const char* deviceGetPromptAudioUrl() {
    return promptAudioUrl[0] ? promptAudioUrl : nullptr;
}

const char* deviceGetThankYouAudioUrl() {
    return thankYouAudioUrl[0] ? thankYouAudioUrl : nullptr;
}

void heartbeatSend() {
    if (deviceToken.isEmpty()) return;

    HTTPClient http;
    String url = String(API_BASE_URL) + "/device/heartbeat";
    http.begin(url);
    http.addHeader("Authorization", "Bearer " + deviceToken);
    http.addHeader("Content-Type", "application/json");

    JsonDocument body;
    body["wifi_strength"] = wifiSignalStrength();
    body["state"] = stateToString(getCurrentState());
    body["queue_depth"] = uploaderQueueDepth();
    body["firmware_version"] = FIRMWARE_VERSION;

    String payload;
    serializeJson(body, payload);
    http.POST(payload);
    http.end();
}
