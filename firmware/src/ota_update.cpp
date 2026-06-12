#include <HTTPClient.h>
#include <Update.h>
#include <ArduinoJson.h>

#include "config.h"
#include "device_auth.h"
#include "ota_update.h"
#include "state_machine.h"

extern String deviceToken;
bool wifiConnected();

static bool versionLessThan(const char* current, const char* latest) {
    int cMaj = 0, cMin = 0, cPat = 0;
    int lMaj = 0, lMin = 0, lPat = 0;
    sscanf(current, "%d.%d.%d", &cMaj, &cMin, &cPat);
    sscanf(latest, "%d.%d.%d", &lMaj, &lMin, &lPat);
    if (cMaj != lMaj) return cMaj < lMaj;
    if (cMin != lMin) return cMin < lMin;
    return cPat < lPat;
}

static bool performHttpOta(const char* url) {
    HTTPClient http;
    http.begin(url);
    http.addHeader("Authorization", "Bearer " + deviceToken);

    int code = http.GET();
    if (code != 200) {
        Serial.printf("[ota] download failed HTTP %d\n", code);
        http.end();
        return false;
    }

    int contentLen = http.getSize();
    if (contentLen <= 0) {
        Serial.println("[ota] unknown content length");
        http.end();
        return false;
    }

    if (!Update.begin(contentLen)) {
        Serial.printf("[ota] Update.begin failed: %s\n", Update.errorString());
        http.end();
        return false;
    }

    WiFiClient* stream = http.getStreamPtr();
    size_t written = Update.writeStream(*stream);
    http.end();

    if (written != (size_t)contentLen) {
        Serial.printf("[ota] incomplete write %u/%d\n", (unsigned)written, contentLen);
        Update.abort();
        return false;
    }

    if (!Update.end(true)) {
        Serial.printf("[ota] Update.end failed: %s\n", Update.errorString());
        return false;
    }

    Serial.println("[ota] success — rebooting");
    delay(500);
    ESP.restart();
    return true;
}

void otaCheckForUpdate() {
    if (deviceToken.isEmpty() || !wifiConnected()) return;
    if (getCurrentState() != STATE_IDLE && getCurrentState() != STATE_RETRY) return;

    HTTPClient http;
    String url = String(API_BASE_URL) + "/device/firmware";
    http.begin(url);
    http.addHeader("Authorization", "Bearer " + deviceToken);

    int code = http.GET();
    if (code != 200) {
        http.end();
        return;
    }

    String payload = http.getString();
    http.end();

    JsonDocument doc;
    if (deserializeJson(doc, payload)) return;

    bool available = doc["update_available"] | false;
    const char* latest = doc["latest_version"] | FIRMWARE_VERSION;
    const char* downloadUrl = doc["download_url"] | "";

    if (!available || !downloadUrl || downloadUrl[0] == '\0') return;
    if (!versionLessThan(FIRMWARE_VERSION, latest)) return;

    Serial.printf("[ota] Updating %s -> %s\n", FIRMWARE_VERSION, latest);
    performHttpOta(downloadUrl);
}
