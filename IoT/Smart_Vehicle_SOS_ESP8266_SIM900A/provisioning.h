// provisioning.h — Local SoftAP + HTTP provisioning portal for AccidentSOS
//
// Requires (install via Arduino Library Manager):
//   ArduinoJson  v7.x  (search "ArduinoJson" by Benoit Blanchon)
//
// Built-in ESP8266 core libraries used (no extra install):
//   ESP8266WebServer, DNSServer, ESP8266WiFi
//
// Boot-hold entry: hold SOS_BUTTON (D0/GPIO16) for 5 s during power-on
//   → device re-enters provisioning mode without erasing existing config.
#pragma once
#include <Arduino.h>
#include <ESP8266WiFi.h>
#include <ESP8266WebServer.h>
#include <DNSServer.h>
#include "config.h"

// ─── AP / network parameters ─────────────────────────────────────────────────
static const IPAddress PROV_AP_IP    (192, 168, 4, 1);
static const IPAddress PROV_AP_GW   (192, 168, 4, 1);
static const IPAddress PROV_AP_SUBNET(255, 255, 255, 0);
#define PROV_DNS_PORT      53
#define PROV_TIMEOUT_MS    600000UL   // 10-minute idle timeout → auto-reboot

// ─── Module state (read from main loop / setup) ───────────────────────────────
extern bool inProvisioningMode;    // true while AP is up
extern bool provisioningComplete;  // set when /finish-setup succeeds

// ─── API called from main .ino ────────────────────────────────────────────────
// Bring up SoftAP + DNS + HTTP server.  Call from setup().
void startProvisioningMode(const char *vehicleId);

// Must be called every loop() iteration while inProvisioningMode is true.
// Handles DNS captive-portal redirects, HTTP clients, and timeout.
void handleProvisioningClient();

// Tear down AP + server.
void stopProvisioningMode();

// Read GPIO16 (SOS_BUTTON) immediately after pinMode().
// Returns true if held continuously for 5 s at boot → force setup mode.
bool isBootHoldForSetup();

// ─── Implemented in main .ino, called from provisioning.cpp ──────────────────
// Sends a clearly-labelled test SMS to configured contacts via SIM900A.
// Must NOT create an accident event or modify any accident state.
// Returns true if at least one SMS was sent successfully.
bool sendTestSOSMessage();
