// config.cpp — EEPROM load / save / validate / clear
#include "config.h"

// ─── Global instance ──────────────────────────────────────────────────────────
DeviceConfig deviceConfig;

// ─── Init ─────────────────────────────────────────────────────────────────────
void initConfig() {
  EEPROM.begin(EEPROM_TOTAL_SIZE);
}

// ─── Load ─────────────────────────────────────────────────────────────────────
// Returns true if flash contains a valid, fully-configured record.
// On a fresh chip (all 0xFF bytes) magic will not match → falls back to
// safe defaults and returns false (→ provisioning mode).
bool loadDeviceConfig() {
  EEPROM.get(CONFIG_EEPROM_ADDR, deviceConfig);

  if (deviceConfig.magic[0] != CONFIG_MAGIC_0 ||
      deviceConfig.magic[1] != CONFIG_MAGIC_1) {
    Serial.println(F("CONFIG: No valid data in flash — fresh/reset device"));
    // Initialise with safe defaults (not saved — only saved when user configures)
    memset(&deviceConfig, 0, sizeof(deviceConfig));
    deviceConfig.magic[0]   = CONFIG_MAGIC_0;
    deviceConfig.magic[1]   = CONFIG_MAGIC_1;
    deviceConfig.configured = 0;
    strncpy(deviceConfig.vehicle_name, "My Vehicle",
            sizeof(deviceConfig.vehicle_name) - 1);
    return false;
  }

  Serial.println(F("CONFIG: Loaded from EEPROM"));
  Serial.print(F("  vehicle    : ")); Serial.println(deviceConfig.vehicle_name);
  Serial.print(F("  contact 1  : ")); Serial.println(deviceConfig.emergency_contact_1);
  Serial.print(F("  configured : ")); Serial.println(deviceConfig.configured ? F("YES") : F("NO"));
  return (bool)deviceConfig.configured;
}

// ─── Save ─────────────────────────────────────────────────────────────────────
// Stamps magic bytes, writes struct, commits.  Returns false on commit failure.
bool saveDeviceConfig() {
  deviceConfig.magic[0] = CONFIG_MAGIC_0;
  deviceConfig.magic[1] = CONFIG_MAGIC_1;
  EEPROM.put(CONFIG_EEPROM_ADDR, deviceConfig);
  bool ok = EEPROM.commit();
  Serial.println(ok ? F("CONFIG: Saved to EEPROM") : F("CONFIG: EEPROM commit FAILED"));
  return ok;
}

// ─── Validate ─────────────────────────────────────────────────────────────────
// Checks minimum requirements for normal operation.
bool validateDeviceConfig(const DeviceConfig &cfg) {
  if (cfg.vehicle_name[0]        == '\0') return false;   // empty name
  if (cfg.emergency_contact_1[0] == '\0') return false;   // no primary contact
  return true;
}

// ─── Clear ────────────────────────────────────────────────────────────────────
// Wipes config and marks device unconfigured.  Persists immediately.
void clearDeviceConfig() {
  memset(&deviceConfig, 0, sizeof(deviceConfig));
  deviceConfig.magic[0]   = CONFIG_MAGIC_0;
  deviceConfig.magic[1]   = CONFIG_MAGIC_1;
  deviceConfig.configured = 0;
  strncpy(deviceConfig.vehicle_name, "My Vehicle",
          sizeof(deviceConfig.vehicle_name) - 1);
  saveDeviceConfig();
  Serial.println(F("CONFIG: Cleared — device will enter setup mode on next boot"));
}

// ─── Helpers ──────────────────────────────────────────────────────────────────
bool isConfigured() {
  return deviceConfig.magic[0] == CONFIG_MAGIC_0 &&
         deviceConfig.magic[1] == CONFIG_MAGIC_1 &&
         (bool)deviceConfig.configured;
}

int getEmergencyContactCount() {
  int n = 0;
  if (deviceConfig.emergency_contact_1[0] != '\0') n++;
  if (deviceConfig.emergency_contact_2[0] != '\0') n++;
  if (deviceConfig.emergency_contact_3[0] != '\0') n++;
  return n;
}

// Returns "" for out-of-range or empty slots.
const char *getEmergencyContact(int index) {
  switch (index) {
    case 0: return deviceConfig.emergency_contact_1;
    case 1: return deviceConfig.emergency_contact_2;
    case 2: return deviceConfig.emergency_contact_3;
    default: return "";
  }
}
