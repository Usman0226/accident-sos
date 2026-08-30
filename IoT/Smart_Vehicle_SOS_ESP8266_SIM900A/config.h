// config.h — Persistent device configuration for AccidentSOS
// Stored in EEPROM (flash emulation).  Magic bytes guard against
// uninitialised-flash false positives.
//
// Requires: ESP8266 Arduino core (EEPROM.h is built-in)
// Layout  : [magic:2][configured:1][vehicle_name:32][contact_1:20][contact_2:20][contact_3:20]
//           = 95 bytes at address 0 inside a 256-byte EEPROM region.
#pragma once
#include <Arduino.h>
#include <EEPROM.h>

// ─── Storage constants ────────────────────────────────────────────────────────
#define EEPROM_TOTAL_SIZE    256
#define CONFIG_EEPROM_ADDR     0
#define CONFIG_MAGIC_0      0xAB     // validity sentinel byte 0
#define CONFIG_MAGIC_1      0xCD     // validity sentinel byte 1

// ─── Persistent configuration struct ─────────────────────────────────────────
// pack(1) prevents compiler padding — struct maps verbatim to EEPROM bytes.
#pragma pack(push, 1)
struct DeviceConfig {
  uint8_t magic[2];                 // { 0xAB, 0xCD } — valid image marker
  uint8_t configured;               // 1 = normal mode, 0 = setup required
  char    vehicle_name[32];         // owner-visible label, null-terminated
  char    emergency_contact_1[20];  // "+91XXXXXXXXXX\0"  (≤19 chars + NUL)
  char    emergency_contact_2[20];  // optional
  char    emergency_contact_3[20];  // optional
};
#pragma pack(pop)

extern DeviceConfig deviceConfig;  // single global instance

// ─── API ──────────────────────────────────────────────────────────────────────
void        initConfig();
bool        loadDeviceConfig();                      // true → valid + configured
bool        saveDeviceConfig();                      // true → EEPROM commit OK
bool        validateDeviceConfig(const DeviceConfig &cfg);
void        clearDeviceConfig();                     // wipe → unconfigured
bool        isConfigured();

int         getEmergencyContactCount();
const char *getEmergencyContact(int index);          // 0, 1, 2
