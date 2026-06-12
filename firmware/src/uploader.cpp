#include <Arduino.h>
#include <HTTPClient.h>
#include <LittleFS.h>
#include <WiFiClient.h>
#include <ArduinoJson.h>
#include <mbedtls/sha256.h>

#include "config.h"
#include "device_auth.h"
#include "uploader.h"

static const char* QUEUE_DIR = "/queue";
static bool fsReady = false;
static int queueDepth = 0;

static String sha256Hex(const uint8_t* data, size_t len) {
    uint8_t hash[32];
    mbedtls_sha256_context ctx;
    mbedtls_sha256_init(&ctx);
    mbedtls_sha256_starts(&ctx, 0);
    mbedtls_sha256_update(&ctx, data, len);
    mbedtls_sha256_finish(&ctx, hash);
    mbedtls_sha256_free(&ctx);

    char hex[65];
    for (int i = 0; i < 32; i++) {
        sprintf(hex + (i * 2), "%02x", hash[i]);
    }
    hex[64] = '\0';
    return String(hex);
}

static String queueMetaPath(int slot) {
    return String(QUEUE_DIR) + "/item" + String(slot) + ".json";
}

static String queueWavPath(int slot) {
    return String(QUEUE_DIR) + "/item" + String(slot) + ".wav";
}

static void refreshQueueDepth() {
    queueDepth = 0;
    if (!fsReady) return;
    for (int i = 0; i < UPLOAD_QUEUE_MAX; i++) {
        if (LittleFS.exists(queueWavPath(i).c_str())) {
            queueDepth++;
        }
    }
}

static int findFreeQueueSlot() {
    for (int i = 0; i < UPLOAD_QUEUE_MAX; i++) {
        if (!LittleFS.exists(queueWavPath(i).c_str())) return i;
    }
    return -1;
}

static unsigned long retryDelayMs(uint8_t attempts) {
    if (attempts == 0) return 0;
    size_t idx = attempts - 1;
    if (idx >= UPLOAD_RETRY_DELAYS_COUNT) {
        idx = UPLOAD_RETRY_DELAYS_COUNT - 1;
    }
    return UPLOAD_RETRY_DELAYS_MS[idx];
}

// Stream wrapper for HTTPClient::POST(Stream*, size_t)
class MultipartBodyStream : public Stream {
public:
    MultipartBodyStream(
        const String& boundary,
        const char* sessionId,
        const char* checksum,
        const uint8_t* data,
        size_t dataLen
    )
        : boundary_(boundary),
          sessionId_(sessionId),
          checksum_(checksum),
          data_(data),
          dataLen_(dataLen) {
        partSession_ = "--" + boundary_ + "\r\n"
                       "Content-Disposition: form-data; name=\"session_id\"\r\n\r\n"
                       + String(sessionId_) + "\r\n";
        partChecksum_ = "--" + boundary_ + "\r\n"
                        "Content-Disposition: form-data; name=\"checksum\"\r\n\r\n"
                        + String(checksum_) + "\r\n";
        partFileHeader_ = "--" + boundary_ + "\r\n"
                          "Content-Disposition: form-data; name=\"file\"; filename=\"recording.wav\"\r\n"
                          "Content-Type: audio/wav\r\n\r\n";
        partEnd_ = "\r\n--" + boundary_ + "--\r\n";
        totalSize_ = partSession_.length() + partChecksum_.length() +
                     partFileHeader_.length() + dataLen_ + partEnd_.length();
        reset();
    }

    size_t totalSize() const { return totalSize_; }

    void reset() {
        phase_ = Phase::Session;
        phaseOffset_ = 0;
        bodyOffset_ = 0;
        bytesSent_ = 0;
    }

    virtual int available() override {
        return (int)(totalSize_ - bytesSent_);
    }

    virtual int read() override {
        uint8_t b;
        if (readBytes(&b, 1) == 1) return b;
        return -1;
    }

    virtual int peek() override { return -1; }

    virtual size_t readBytes(char* buffer, size_t length) override {
        size_t written = 0;
        while (written < length && bytesSent_ < totalSize_) {
            const char* chunk = nullptr;
            size_t chunkLen = 0;

            switch (phase_) {
                case Phase::Session:
                    chunk = partSession_.c_str();
                    chunkLen = partSession_.length();
                    break;
                case Phase::Checksum:
                    chunk = partChecksum_.c_str();
                    chunkLen = partChecksum_.length();
                    break;
                case Phase::FileHeader:
                    chunk = partFileHeader_.c_str();
                    chunkLen = partFileHeader_.length();
                    break;
                case Phase::Body:
                    chunkLen = min(length - written, dataLen_ - bodyOffset_);
                    memcpy(buffer + written, data_ + bodyOffset_, chunkLen);
                    bodyOffset_ += chunkLen;
                    bytesSent_ += chunkLen;
                    written += chunkLen;
                    if (bodyOffset_ >= dataLen_) {
                        phase_ = Phase::End;
                        phaseOffset_ = 0;
                    }
                    continue;
                case Phase::End:
                    chunk = partEnd_.c_str();
                    chunkLen = partEnd_.length();
                    break;
                case Phase::Done:
                    return written;
            }

            size_t toCopy = min(length - written, chunkLen - phaseOffset_);
            memcpy(buffer + written, chunk + phaseOffset_, toCopy);
            phaseOffset_ += toCopy;
            bytesSent_ += toCopy;
            written += toCopy;

            if (phaseOffset_ >= chunkLen) {
                phaseOffset_ = 0;
                advancePhase();
            }
        }
        return written;
    }

    virtual size_t write(uint8_t) override { return 0; }

    virtual void flush() override {}

private:
    enum class Phase { Session, Checksum, FileHeader, Body, End, Done };

    void advancePhase() {
        switch (phase_) {
            case Phase::Session: phase_ = Phase::Checksum; break;
            case Phase::Checksum: phase_ = Phase::FileHeader; break;
            case Phase::FileHeader: phase_ = Phase::Body; break;
            case Phase::End: phase_ = Phase::Done; break;
            default: break;
        }
    }

    String boundary_;
    const char* sessionId_;
    const char* checksum_;
    const uint8_t* data_;
    size_t dataLen_;

    String partSession_;
    String partChecksum_;
    String partFileHeader_;
    String partEnd_;
    size_t totalSize_ = 0;
    size_t bytesSent_ = 0;

    Phase phase_ = Phase::Session;
    size_t phaseOffset_ = 0;
    size_t bodyOffset_ = 0;
};

static bool uploadDirect(const char* sessionId, const uint8_t* data, size_t len, const char* checksum) {
    if (!wifiConnected() || deviceToken.isEmpty()) return false;

    const String boundary = "----BoothUploadBoundary";
    MultipartBodyStream bodyStream(boundary, sessionId, checksum, data, len);

    WiFiClient client;
    HTTPClient http;
    String url = String(API_BASE_URL) + "/uploads/audio";

    http.begin(client, url);
    http.addHeader("Authorization", "Bearer " + deviceToken);
    http.addHeader("Content-Type", "multipart/form-data; boundary=" + boundary);

    int code = http.POST(&bodyStream, bodyStream.totalSize());
    String response = http.getString();
    http.end();

    if (code == 200 || code == 201) {
        Serial.printf("[upload] OK session=%s (%u bytes)\n", sessionId, (unsigned)len);
        return true;
    }

    Serial.printf("[upload] Failed HTTP %d: %s\n", code, response.c_str());
    return false;
}

static bool saveToQueue(const char* sessionId, const uint8_t* data, size_t len, const char* checksum) {
    if (!fsReady) return false;

    int slot = findFreeQueueSlot();
    if (slot < 0) {
        Serial.println("[upload] Queue full — dropping oldest slot 0");
        LittleFS.remove(queueWavPath(0).c_str());
        LittleFS.remove(queueMetaPath(0).c_str());
        slot = 0;
    }

    File wav = LittleFS.open(queueWavPath(slot).c_str(), "w");
    if (!wav) {
        Serial.println("[upload] Failed to open queue wav for write");
        return false;
    }
    wav.write(data, len);
    wav.close();

    JsonDocument meta;
    meta["session_id"] = sessionId;
    meta["checksum"] = checksum;
    meta["data_len"] = len;
    meta["attempts"] = 0;
    meta["next_retry_ms"] = millis() + retryDelayMs(1);

    File metaFile = LittleFS.open(queueMetaPath(slot).c_str(), "w");
    if (!metaFile) {
        LittleFS.remove(queueWavPath(slot).c_str());
        Serial.println("[upload] Failed to write queue metadata");
        return false;
    }
    serializeJson(meta, metaFile);
    metaFile.close();

    refreshQueueDepth();
    Serial.printf("[upload] Queued slot %d session=%s depth=%d\n", slot, sessionId, queueDepth);
    return true;
}

static bool uploadFromQueueSlot(int slot) {
    String metaPath = queueMetaPath(slot);
    String wavPath = queueWavPath(slot);

    if (!LittleFS.exists(metaPath.c_str()) || !LittleFS.exists(wavPath.c_str())) {
        return false;
    }

    File metaFile = LittleFS.open(metaPath.c_str(), "r");
    if (!metaFile) return false;

    JsonDocument meta;
    if (deserializeJson(meta, metaFile)) {
        metaFile.close();
        return false;
    }
    metaFile.close();

    unsigned long nextRetry = meta["next_retry_ms"] | 0UL;
    if (millis() < nextRetry) return false;

    const char* sessionId = meta["session_id"] | "";
    const char* checksum = meta["checksum"] | "";
    size_t dataLen = meta["data_len"] | 0;
    uint8_t attempts = meta["attempts"] | 0;

    if (sessionId[0] == '\0' || checksum[0] == '\0' || dataLen == 0) {
        LittleFS.remove(metaPath.c_str());
        LittleFS.remove(wavPath.c_str());
        refreshQueueDepth();
        return false;
    }

    uint8_t* buffer = (uint8_t*)malloc(dataLen);
    if (!buffer) {
        Serial.println("[upload] malloc failed for queue playback");
        return false;
    }

    File wav = LittleFS.open(wavPath.c_str(), "r");
    if (!wav) {
        free(buffer);
        return false;
    }
    size_t readLen = wav.read(buffer, dataLen);
    wav.close();

    if (readLen != dataLen) {
        free(buffer);
        return false;
    }

    bool ok = uploadDirect(sessionId, buffer, dataLen, checksum);
    free(buffer);

    if (ok) {
        LittleFS.remove(metaPath.c_str());
        LittleFS.remove(wavPath.c_str());
        refreshQueueDepth();
        Serial.printf("[upload] Queue slot %d synced\n", slot);
        return true;
    }

    attempts++;
    meta["attempts"] = attempts;
    meta["next_retry_ms"] = millis() + retryDelayMs(attempts);

    metaFile = LittleFS.open(metaPath.c_str(), "w");
    if (metaFile) {
        serializeJson(meta, metaFile);
        metaFile.close();
    }

    if (attempts >= UPLOAD_MAX_ATTEMPTS) {
        Serial.printf("[upload] Queue slot %d exceeded max attempts — retained for operator\n", slot);
    }
    return false;
}

void uploaderInit() {
    fsReady = LittleFS.begin(true);
    if (!fsReady) {
        Serial.println("[upload] LittleFS mount failed — offline queue disabled");
        return;
    }

    if (!LittleFS.exists(QUEUE_DIR)) {
        LittleFS.mkdir(QUEUE_DIR);
    }
    refreshQueueDepth();
    Serial.printf("[upload] Ready — queue depth %d\n", queueDepth);
}

int uploaderQueueDepth() {
    return queueDepth;
}

bool uploaderEnqueue(const char* sessionId, const uint8_t* data, size_t len) {
    if (!sessionId || !data || len < 44) return false;

    String checksum = sha256Hex(data, len);
    if (uploadDirect(sessionId, data, len, checksum.c_str())) {
        return true;
    }

    if (saveToQueue(sessionId, data, len, checksum.c_str())) {
        return false;
    }
    return false;
}

bool uploaderProcessQueue() {
    if (!fsReady || queueDepth == 0 || !wifiConnected() || deviceToken.isEmpty()) {
        return false;
    }

    bool progressed = false;
    for (int i = 0; i < UPLOAD_QUEUE_MAX; i++) {
        if (LittleFS.exists(queueWavPath(i).c_str())) {
            if (uploadFromQueueSlot(i)) {
                progressed = true;
            }
        }
    }
    return progressed;
}
