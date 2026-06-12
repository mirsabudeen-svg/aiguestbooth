#include <HTTPClient.h>
#include <ArduinoJson.h>
#include "config.h"

extern String deviceToken;

bool sessionStart(const char* triggerType, char* outSessionId, size_t outLen) {
    HTTPClient http;
    String url = String(API_BASE_URL) + "/sessions/start";
    http.begin(url);
    http.addHeader("Authorization", "Bearer " + deviceToken);
    http.addHeader("Content-Type", "application/json");

    String body = String("{\"trigger_type\":\"") + (triggerType ? triggerType : "button") + "\"}";
    int code = http.POST(body);
    if (code != 200) {
        http.end();
        return false;
    }

    String payload = http.getString();
    http.end();

    JsonDocument doc;
    if (deserializeJson(doc, payload)) return false;

    const char* sid = doc["session_id"];
    if (!sid) return false;
    strncpy(outSessionId, sid, outLen - 1);
    return true;
}

bool sessionComplete(const char* sessionId, float durationSec) {
    HTTPClient http;
    String url = String(API_BASE_URL) + "/sessions/" + String(sessionId) + "/complete";
    http.begin(url);
    http.addHeader("Authorization", "Bearer " + deviceToken);
    http.addHeader("Content-Type", "application/json");

    String body = "{\"duration_seconds\":" + String(durationSec, 2) + "}";
    int code = http.POST(body);
    http.end();
    return code == 200;
}
