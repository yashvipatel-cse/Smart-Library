// ============================================
// Smart Library RFID Detection System
// COMBINED: 4 Book UIDs + Backend + Buzzer
// ESP32 Firmware — C++ (Arduino Framework)
//
// PIN CONNECTIONS:
//   RC522 SDA  → GPIO 5
//   RC522 SCK  → GPIO 18
//   RC522 MOSI → GPIO 23
//   RC522 MISO → GPIO 19
//   RC522 RST  → GPIO 22
//   RC522 VCC  → 3.3V
//   RC522 GND  → GND
//   Buzzer (+) → GPIO 13
//   Buzzer (-) → GND
//   LED        → GPIO 2
// ============================================

#include <Arduino.h>
#include <WiFi.h>
#include <HTTPClient.h>
#include <SPI.h>
#include <MFRC522.h>
#include <ArduinoJson.h>

// ============================================
// WIFI + SERVER CONFIGURATION
// Update SERVER_IP to match your PC's IP
// ============================================
const char* WIFI_SSID     = "Yug's S24 FE";
const char* WIFI_PASSWORD = "00000000";
const char* SERVER_IP     = "10.237.63.144";   // ← your PC IP running Spring Boot
const int   SERVER_PORT   = 8080;
const char* SHELF_ID      = "A1";              // this shelf code

// ============================================
// YOUR 4 BOOK RFID UIDs
// These must also exist in MySQL rfid_books table
// ============================================
String correctBooks[] = {
    "FA7819C1",   // Book 1 — Clean Code
    "D3FB9CF8",   // Book 2 — Introduction to Algorithms
    "A432859A",   // Book 3 — Calculus Vol.1
    "AA2894C1"    // Book 4 — University Physics
};
int totalBooks = 4;

// ============================================
// PIN DEFINITIONS
// ============================================
#define RFID_SS_PIN   5
#define RFID_RST_PIN  22
#define BUZZER_PIN    13
#define LED_PIN       2

MFRC522 rfid(RFID_SS_PIN, RFID_RST_PIN);

void connectToWiFi();
String readRFIDTag();
bool isBookRegisteredLocally(String uid);
String sendScanToServer(String uid, String shelfId);
void alarmWRONG();
void beepOK();
void beepUNKNOWN();
void blinkLED(int times);
void beep(int times, int duration);

void setup() {
    Serial.begin(115200);
    delay(500);

    Serial.println("========================================");
    Serial.println("  Smart Library RFID System Starting...");
    Serial.println("========================================");

    pinMode(BUZZER_PIN, OUTPUT);
    pinMode(LED_PIN, OUTPUT);
    digitalWrite(BUZZER_PIN, LOW);
    digitalWrite(LED_PIN, LOW);

    SPI.begin();
    rfid.PCD_Init();
    Serial.print("[RFID] Version: ");
    rfid.PCD_DumpVersionToSerial();
    Serial.println("[RFID] RC522 Ready");

    connectToWiFi();

    beep(3, 150);
    blinkLED(3);

    Serial.println("========================================");
    Serial.println("[INFO] Registered books on this shelf:");
    for (int i = 0; i < totalBooks; i++) {
        Serial.print("       Book ");
        Serial.print(i + 1);
        Serial.print(" → UID: ");
        Serial.println(correctBooks[i]);
    }
    Serial.println("========================================");
    Serial.print("[INFO] Shelf ID: ");
    Serial.println(SHELF_ID);
    Serial.println("[READY] Waiting for RFID scan...");
    Serial.println("========================================");
}

void loop() {

    if (!rfid.PICC_IsNewCardPresent()) return;
    if (!rfid.PICC_ReadCardSerial()) return;

    String uid = readRFIDTag();

    Serial.println("========================================");
    Serial.print("[SCAN] Tag detected! UID: ");
    Serial.println(uid);

    bool isKnownBook = isBookRegisteredLocally(uid);

    if (!isKnownBook) {
        Serial.println("[WARN] This book is NOT registered!");
        beepUNKNOWN();
        blinkLED(5);
        rfid.PICC_HaltA();
        rfid.PCD_StopCrypto1();
        delay(1500);
        return;
    }

    Serial.println("[INFO] Book found in registered list");

    if (WiFi.status() == WL_CONNECTED) {

        String result = sendScanToServer(uid, String(SHELF_ID));

        Serial.print("[RESULT] Server response: ");
        Serial.println(result);

        if (result == "OK") {
            Serial.println("[OK] Book is on CORRECT shelf ✅");
            beepOK();
            blinkLED(1);

        } else if (result == "WRONG") {
            Serial.println("[ALARM] Book is on WRONG shelf! 🔔");
            alarmWRONG();

        } else if (result == "UNKNOWN") {
            Serial.println("[WARN] Book not in MySQL database!");
            beepUNKNOWN();
            blinkLED(5);

        } else {
            Serial.println("[ERROR] Cannot reach Java server!");
            beep(2, 300);
            blinkLED(2);
        }

    } else {
        Serial.println("[ERROR] WiFi disconnected! Reconnecting...");
        connectToWiFi();
        beep(2, 100);
    }

    rfid.PICC_HaltA();
    rfid.PCD_StopCrypto1();

    Serial.println("[READY] Scan next book...");
    Serial.println("========================================");
    delay(1500);
}

bool isBookRegisteredLocally(String uid) {
    for (int i = 0; i < totalBooks; i++) {
        if (uid == correctBooks[i]) {
            Serial.print("[INFO] Matched: Book ");
            Serial.println(i + 1);
            return true;
        }
    }
    return false;
}

String readRFIDTag() {
    String uid = "";
    for (byte i = 0; i < rfid.uid.size; i++) {
        if (rfid.uid.uidByte[i] < 0x10) uid += "0";
        uid += String(rfid.uid.uidByte[i], HEX);
    }
    uid.toUpperCase();
    return uid;
}

String sendScanToServer(String uid, String shelfId) {
    HTTPClient http;

    String url = "http://";
    url += SERVER_IP;
    url += ":";
    url += SERVER_PORT;
    url += "/api/scan";

    Serial.print("[HTTP] Sending to: ");
    Serial.println(url);

    http.begin(url);
    http.addHeader("Content-Type", "application/json");
    http.setTimeout(5000);

    StaticJsonDocument<200> doc;
    doc["uid"]     = uid;
    doc["shelfId"] = shelfId;

    String jsonPayload;
    serializeJson(doc, jsonPayload);

    Serial.print("[HTTP] Payload: ");
    Serial.println(jsonPayload);

    int httpCode = http.POST(jsonPayload);
    String response = "ERROR";

    if (httpCode > 0) {
        response = http.getString();
        response.trim();
        Serial.print("[HTTP] Response code: ");
        Serial.println(httpCode);
    } else {
        Serial.print("[HTTP] Failed: ");
        Serial.println(http.errorToString(httpCode));
    }

    http.end();
    return response;
}

void alarmWRONG() {
    for (int i = 0; i < 3; i++) {
        digitalWrite(BUZZER_PIN, HIGH);
        digitalWrite(LED_PIN, HIGH);
        delay(700);
        digitalWrite(BUZZER_PIN, LOW);
        digitalWrite(LED_PIN, LOW);
        delay(200);
    }
}

void beepOK() {
    digitalWrite(BUZZER_PIN, HIGH);
    delay(150);
    digitalWrite(BUZZER_PIN, LOW);
}

void beepUNKNOWN() {
    for (int i = 0; i < 5; i++) {
        digitalWrite(BUZZER_PIN, HIGH);
        delay(80);
        digitalWrite(BUZZER_PIN, LOW);
        delay(60);
    }
}

void blinkLED(int times) {
    for (int i = 0; i < times; i++) {
        digitalWrite(LED_PIN, HIGH);
        delay(200);
        digitalWrite(LED_PIN, LOW);
        delay(200);
    }
}

void beep(int times, int duration) {
    for (int i = 0; i < times; i++) {
        digitalWrite(BUZZER_PIN, HIGH);
        delay(duration);
        digitalWrite(BUZZER_PIN, LOW);
        if (times > 1) delay(80);
    }
}

void connectToWiFi() {
    Serial.print("[WiFi] Connecting to: ");
    Serial.println(WIFI_SSID);

    WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

    int attempt = 0;
    while (WiFi.status() != WL_CONNECTED) {
        delay(500);
        Serial.print(".");
        attempt++;
        if (attempt > 30) {
            Serial.println();
            Serial.println("[WiFi] Failed! Check SSID/Password.");
            return;
        }
    }
    Serial.println();
    Serial.println("[WiFi] Connected! ✅");
    Serial.print("[WiFi] ESP32 IP: ");
    Serial.println(WiFi.localIP());
}
