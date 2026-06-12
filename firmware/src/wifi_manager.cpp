#include <WiFi.h>
#include "config.h"

static bool connected = false;

void wifiInit() {
    WiFi.mode(WIFI_STA);
    WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
    Serial.printf("[wifi] Connecting to %s\n", WIFI_SSID);

    int attempts = 0;
    while (WiFi.status() != WL_CONNECTED && attempts < 30) {
        delay(500);
        Serial.print(".");
        attempts++;
    }
    Serial.println();
    connected = WiFi.status() == WL_CONNECTED;
    if (connected) {
        Serial.printf("[wifi] Connected: %s\n", WiFi.localIP().toString().c_str());
    }
}

bool wifiConnected() {
    connected = WiFi.status() == WL_CONNECTED;
    return connected;
}

int wifiSignalStrength() {
    if (!wifiConnected()) return 0;
    return min(100, max(0, 2 * (WiFi.RSSI() + 100)));
}
