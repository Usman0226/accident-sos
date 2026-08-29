#include <Wire.h>
#include <ESP8266WiFi.h>
#include <ESP8266HTTPClient.h>
#include <WiFiClientSecure.h>
#include <SoftwareSerial.h>

#include <Adafruit_MPU6050.h>
#include <Adafruit_Sensor.h>
#include <DHT.h>

#include <math.h>
// WIFI
const char* WIFI_SSID     = "sos-alert";
const char* WIFI_PASSWORD = "12345678";

const char* SERVER_URL =
  "https://accident-detection-sos.onrender.com/api/sos/";
// VEHICLE
const char* VEHICLE_ID = "VEHICLE-001";
// SIM900A / GSM
// Emergency recipients.
const char* EMERGENCY_NUMBERS[] = {
  "9441578782",
  "9123456789" // Add more contacts here
};
const int NUM_EMERGENCY_CONTACTS = sizeof(EMERGENCY_NUMBERS) / sizeof(EMERGENCY_NUMBERS[0]);

// SMS text.
const char* SOS_SMS_TEXT =
  "SOS ALERT: Emergency detected. Please check the vehicle immediately.";

// Call duration.
const unsigned long GSM_CALL_DURATION = 20000;

// Set true to use GSM call/SMS.
const bool GSM_ENABLED = true;

// WhatsApp is NOT sent directly by SIM900A.
// The server can send WhatsApp using its configured WhatsApp API.
const bool WHATSAPP_REQUESTED = true;
// PINS
// I2C pins for MPU6050.
#define SDA_PIN        4    // D2 / GPIO4
#define SCL_PIN        5    // D1 / GPIO5

// SIM900A — does not conflict with MPU6050.
#define SIM900_RX     14    // D5 / GPIO14 <- SIM900A TX
#define SIM900_TX     12    // D6 / GPIO12 -> SIM900A RX

// Control pins.
#define SOS_BUTTON    16    // D0 / GPIO16
#define CANCEL_BUTTON  2    // D4 / GPIO2
#define BUZZER        13    // D7 / GPIO13

// DHT11 temperature & humidity sensor.
#define DHT_PIN        0    // D3 / GPIO0
#define DHT_TYPE    DHT11

SoftwareSerial sim900(SIM900_RX, SIM900_TX);
DHT            dht(DHT_PIN, DHT_TYPE);
// MPU6050
Adafruit_MPU6050 mpu;

bool mpuAvailable = false;
// BLOCK 1 — SLIDING WINDOW RING BUFFER
// Stores the last 2 seconds of sensor samples at 50 Hz.
// Every temporal feature is computed from this buffer.
#define SAMPLE_RATE_HZ    50
#define WINDOW_SIZE      100   // 2 seconds at 50 Hz
#define SAMPLE_INTERVAL_MS 20  // 1000 / SAMPLE_RATE_HZ

struct SensorSample
{
  float ax, ay, az;     // raw acceleration (m/s²)
  float gx, gy, gz;     // raw gyroscope   (rad/s)
  float mag;            // accel magnitude (m/s²)
  unsigned long ts;     // millis() timestamp
};

SensorSample  sampleBuf[WINDOW_SIZE];
int           sampleHead    = 0;
bool          bufferFull    = false;
unsigned long lastSampleMs  = 0;
// BLOCK 2 — FEATURE SET STRUCT
struct FeatureSet
{
  float peak_acceleration;     // m/s²
  float peak_jerk;             // m/s³
  float peak_angular_velocity; // rad/s
  float velocity_change;       // m/s  (delta-V estimate)
  float orientation_change;    // degrees
  float post_impact_motion;    // m/s² (mean accel last 0.5 s)
};

FeatureSet lastFeatures;
// BLOCK 3 — DETECTION WEIGHTS & SEVERITY THRESHOLDS
// Scoring weights (must sum to 1.0).
const float WEIGHT_IMPACT    = 0.35f;
const float WEIGHT_JERK      = 0.20f;
const float WEIGHT_GYRO      = 0.15f;
const float WEIGHT_VELOCITY  = 0.15f;
const float WEIGHT_ORIENT    = 0.10f;
const float WEIGHT_STILLNESS = 0.05f;

// Normalisation maxima — tune from RC-car recordings.
const float NORM_ACCEL_MAX    = 50.0f;   // m/s²
const float NORM_JERK_MAX     = 200.0f;  // m/s³
const float NORM_GYRO_MAX     = 10.0f;   // rad/s
const float NORM_VELOCITY_MAX = 10.0f;   // m/s
const float NORM_ORIENT_MAX   = 90.0f;   // degrees

// Stillness threshold: post-impact mean accel below this → likely stationary.
const float STILLNESS_THRESHOLD = 1.0f;  // m/s²

// Confidence boundaries.
const float CONF_SEVERE   = 0.75f;
const float CONF_MODERATE = 0.45f;
const float CONF_LOW      = 0.25f;

// Cooldown after an accident trigger.
const unsigned long ACCIDENT_COOLDOWN = 15000;
unsigned long lastAccidentTime        = 0;

// Live classification output.
float  accidentConfidence = 0.0f;
String accidentSeverity   = "NONE";
// BLOCK 4 — UNIQUE EVENT ID
String currentEventId = "";

String generateEventId()
{
  String id = VEHICLE_ID;
  id += "-";
  id += String(millis());
  id += "-";
  id += String(random(0x1000, 0xFFFF), HEX);
  id.toUpperCase();
  return id;
}
// BLOCK 5 — LOCAL QUEUE + RETRY
#define MAX_QUEUE_SIZE    3
#define RETRY_INTERVAL_MS 30000UL
#define MAX_RETRY_COUNT   5

struct QueuedSOS
{
  bool          pending;
  String        eventId;
  String        jsonPayload;
  int           retryCount;
  unsigned long lastAttemptMs;
};

QueuedSOS sosQueue[MAX_QUEUE_SIZE];

void initQueue()
{
  for (int i = 0; i < MAX_QUEUE_SIZE; i++)
  {
    sosQueue[i].pending      = false;
    sosQueue[i].retryCount   = 0;
    sosQueue[i].lastAttemptMs = 0;
  }
}

bool enqueueSOSEvent(const String& eid, const String& json)
{
  for (int i = 0; i < MAX_QUEUE_SIZE; i++)
  {
    if (!sosQueue[i].pending)
    {
      sosQueue[i].pending       = true;
      sosQueue[i].eventId       = eid;
      sosQueue[i].jsonPayload   = json;
      sosQueue[i].retryCount    = 0;
      sosQueue[i].lastAttemptMs = 0;   // try immediately

      Serial.println();
      Serial.println("SOS QUEUED — SLOT " + String(i));
      Serial.println("EVENT ID: " + eid);
      return true;
    }
  }

  Serial.println("QUEUE FULL — SOS DROPPED");
  return false;
}
// COUNTDOWN
const unsigned long COUNTDOWN_TIME = 10000;
// GPS
// No GPS module currently connected.
// Replace when a NEO-6M or similar is added.
const float FALLBACK_LATITUDE  = 13.629000f;
const float FALLBACK_LONGITUDE = 78.485000f;

bool  gpsFix        = false;
float gpsLat        = FALLBACK_LATITUDE;
float gpsLon        = FALLBACK_LONGITUDE;
float gpsSpeedKmph  = 0.0f;
// BATTERY
// No voltage measurement — stub 100 %.
float batteryPct = 100.0f;
// DHT11 — TEMPERATURE & HUMIDITY
float dhtTemperatureC = 0.0f;  // °C
float dhtHumidityPct  = 0.0f;  // %
bool  dhtAvailable    = false;

void readDHT11()
{
  float t = dht.readTemperature();
  float h = dht.readHumidity();

  if (isnan(t) || isnan(h))
  {
    // DHT not responding or checksum failed.
    dhtAvailable    = false;
    dhtTemperatureC = -999.0f;
    dhtHumidityPct  = -999.0f;

    Serial.println("DHT11 READ FAILED — using last valid value");
    return;
  }

  dhtTemperatureC = t;
  dhtHumidityPct  = h;
  dhtAvailable    = true;

  Serial.print("DHT11 — TEMP: ");
  Serial.print(t, 1);
  Serial.print(" C  |  HUMIDITY: ");
  Serial.print(h, 1);
  Serial.println(" %");
}
// SYSTEM STATE
enum SystemState
{
  SAFE,
  MANUAL_COUNTDOWN,
  ACCIDENT_COUNTDOWN,
  SOS_ACTIVE
};

SystemState currentState = SAFE;
// COUNTDOWN VARIABLES
unsigned long countdownStart = 0;
int           lastSecond     = -1;
// CURRENT SENSOR VARIABLES
// (also written by tickSensorBuffer each iteration)
float accelX = 0.0f;
float accelY = 0.0f;
float accelZ = 0.0f;

float gyroX = 0.0f;
float gyroY = 0.0f;
float gyroZ = 0.0f;

float accelerationMagnitude = 0.0f;
float impactG               = 0.0f;
float tiltAngle             = 0.0f;
// SENSOR SOURCE
String sensorSource = "SIMULATED";
// READ MPU6050
bool readMPU6050()
{
  if (!mpuAvailable)
  {
    return false;
  }

  sensors_event_t acceleration;
  sensors_event_t gyro;
  sensors_event_t temperature;

  mpu.getEvent(&acceleration, &gyro, &temperature);

  accelX = acceleration.acceleration.x;
  accelY = acceleration.acceleration.y;
  accelZ = acceleration.acceleration.z;

  gyroX = gyro.gyro.x;
  gyroY = gyro.gyro.y;
  gyroZ = gyro.gyro.z;

  // Total acceleration magnitude.
  accelerationMagnitude = sqrt(
    accelX * accelX +
    accelY * accelY +
    accelZ * accelZ
  );

  // Impact G: net G above 1 g baseline.
  impactG = (accelerationMagnitude / 9.80665f) - 1.0f;
  if (impactG < 0.0f) impactG = 0.0f;

  // Tilt angle from vertical.
  tiltAngle = atan2(
    sqrt(accelX * accelX + accelY * accelY),
    fabs(accelZ)
  ) * 180.0f / PI;

  sensorSource = "REAL_MPU6050";
  return true;
}
// SIMULATED SENSOR DATA
void generateSimulatedSensorData()
{
  accelX = random(-30, 31) / 10.0f;
  accelY = random(-30, 31) / 10.0f;
  accelZ = random(90, 110) / 10.0f;

  gyroX = random(-100, 101) / 10.0f;
  gyroY = random(-100, 101) / 10.0f;
  gyroZ = random(-100, 101) / 10.0f;

  accelerationMagnitude = sqrt(
    accelX * accelX +
    accelY * accelY +
    accelZ * accelZ
  );

  impactG = (accelerationMagnitude / 9.80665f) - 1.0f;
  if (impactG < 0.0f) impactG = 0.0f;

  tiltAngle = atan2(
    sqrt(accelX * accelX + accelY * accelY),
    fabs(accelZ)
  ) * 180.0f / PI;

  sensorSource = "SIMULATED";
}
// UPDATE SENSOR (snapshot)
void updateSensorData()
{
  if (mpuAvailable)
  {
    if (!readMPU6050())
    {
      generateSimulatedSensorData();
    }
  }
  else
  {
    generateSimulatedSensorData();
  }
}
// BLOCK 1 (cont.) — TICK SENSOR BUFFER
// Called every loop() iteration.
// Writes one sample to the ring buffer every SAMPLE_INTERVAL_MS.
void tickSensorBuffer()
{
  if (!mpuAvailable) return;

  unsigned long now = millis();
  if (now - lastSampleMs < SAMPLE_INTERVAL_MS) return;
  lastSampleMs = now;

  // Read raw sensor.
  readMPU6050();

  // Write into circular buffer.
  SensorSample s;
  s.ax  = accelX;
  s.ay  = accelY;
  s.az  = accelZ;
  s.gx  = gyroX;
  s.gy  = gyroY;
  s.gz  = gyroZ;
  s.mag = accelerationMagnitude;
  s.ts  = now;

  sampleBuf[sampleHead] = s;
  sampleHead = (sampleHead + 1) % WINDOW_SIZE;

  if (sampleHead == 0) bufferFull = true;
}
// BLOCK 2 (cont.) — COMPUTE FEATURES
// Walks the ring buffer and derives all six contract features.
FeatureSet computeFeatures()
{
  FeatureSet f;
  f.peak_acceleration     = 0.0f;
  f.peak_jerk             = 0.0f;
  f.peak_angular_velocity = 0.0f;
  f.velocity_change       = 0.0f;
  f.orientation_change    = 0.0f;
  f.post_impact_motion    = 0.0f;

  int count = bufferFull ? WINDOW_SIZE : sampleHead;
  if (count < 2) return f;

  // ------------------------------------------------------------
  // Determine iteration order (oldest → newest).
  // If buffer is full the oldest sample is at sampleHead.
  // ------------------------------------------------------------
  int start = bufferFull ? sampleHead : 0;

  float prevMag = sampleBuf[start].mag;
  unsigned long prevTs = sampleBuf[start].ts;

  // For velocity_change integration.
  float   deltaV = 0.0f;

  // For post_impact_motion (last 0.5 s = 25 samples at 50 Hz).
  int postImpactSamples = SAMPLE_RATE_HZ / 2;  // 25
  float postMotionSum   = 0.0f;
  int   postMotionCount = 0;

  // Gravity vectors: first 5 samples = pre-event gravity estimate.
  float grav_bx = 0, grav_by = 0, grav_bz = 0;
  float grav_ax = 0, grav_ay = 0, grav_az = 0;
  int   gravSamples = 5;

  for (int n = 0; n < count; n++)
  {
    int idx = (start + n) % WINDOW_SIZE;
    SensorSample& s = sampleBuf[idx];

    // Peak acceleration.
    if (s.mag > f.peak_acceleration)
      f.peak_acceleration = s.mag;

    // Jerk (rate of change of magnitude).
    unsigned long dt_us = s.ts - prevTs;
    if (dt_us > 0)
    {
      float dt_s  = dt_us / 1000.0f;
      float jerk  = fabs(s.mag - prevMag) / dt_s;
      if (jerk > f.peak_jerk)
        f.peak_jerk = jerk;
    }

    // Peak angular velocity.
    float av = sqrt(s.gx * s.gx + s.gy * s.gy + s.gz * s.gz);
    if (av > f.peak_angular_velocity)
      f.peak_angular_velocity = av;

    // Velocity change: integrate (mag - g) × dt.
    if (dt_us > 0)
    {
      float dt_s = dt_us / 1000.0f;
      deltaV += (s.mag - 9.80665f) * dt_s;
    }

    // Gravity estimate: first N samples → before, last N samples → after.
    if (n < gravSamples)
    {
      grav_bx += s.ax;
      grav_by += s.ay;
      grav_bz += s.az;
    }
    if (n >= count - gravSamples)
    {
      grav_ax += s.ax;
      grav_ay += s.ay;
      grav_az += s.az;
    }

    // Post-impact motion: mean mag of last postImpactSamples.
    if (n >= count - postImpactSamples)
    {
      postMotionSum   += s.mag;
      postMotionCount++;
    }

    prevMag = s.mag;
    prevTs  = s.ts;
  }

  // Velocity change (absolute value).
  f.velocity_change = fabs(deltaV);

  // Orientation change: angle between pre- and post-event gravity vectors.
  if (gravSamples > 0)
  {
    grav_bx /= gravSamples; grav_by /= gravSamples; grav_bz /= gravSamples;
    grav_ax /= gravSamples; grav_ay /= gravSamples; grav_az /= gravSamples;

    float dot = grav_bx * grav_ax + grav_by * grav_ay + grav_bz * grav_az;
    float magB = sqrt(grav_bx * grav_bx + grav_by * grav_by + grav_bz * grav_bz);
    float magA = sqrt(grav_ax * grav_ax + grav_ay * grav_ay + grav_az * grav_az);

    if (magB > 0.001f && magA > 0.001f)
    {
      float cosAngle = dot / (magB * magA);
      // Clamp to [-1, 1] to guard against floating-point drift.
      cosAngle = constrain(cosAngle, -1.0f, 1.0f);
      f.orientation_change = acos(cosAngle) * 180.0f / PI;
    }
  }

  // Post-impact motion.
  if (postMotionCount > 0)
    f.post_impact_motion = postMotionSum / postMotionCount;

  return f;
}
// BLOCK 3 (cont.) — CLASSIFY ACCIDENT
// Returns true if a real accident is detected.
// Writes accidentConfidence and accidentSeverity.
float clampNormalize(float value, float maxVal)
{
  float n = value / maxVal;
  return constrain(n, 0.0f, 1.0f);
}

bool classifyAccident(const FeatureSet& f)
{
  float score = 0.0f;

  score += WEIGHT_IMPACT    * clampNormalize(f.peak_acceleration,     NORM_ACCEL_MAX);
  score += WEIGHT_JERK      * clampNormalize(f.peak_jerk,             NORM_JERK_MAX);
  score += WEIGHT_GYRO      * clampNormalize(f.peak_angular_velocity, NORM_GYRO_MAX);
  score += WEIGHT_VELOCITY  * clampNormalize(f.velocity_change,       NORM_VELOCITY_MAX);
  score += WEIGHT_ORIENT    * clampNormalize(f.orientation_change,    NORM_ORIENT_MAX);
  score += WEIGHT_STILLNESS * (f.post_impact_motion < STILLNESS_THRESHOLD ? 1.0f : 0.0f);

  accidentConfidence = constrain(score, 0.0f, 1.0f);

  if      (accidentConfidence >= CONF_SEVERE)   accidentSeverity = "SEVERE";
  else if (accidentConfidence >= CONF_MODERATE) accidentSeverity = "MODERATE";
  else if (accidentConfidence >= CONF_LOW)      accidentSeverity = "LOW";
  else
  {
    accidentSeverity = "NONE";
    return false;
  }

  return true;
}
// BUZZER FUNCTIONS
void buzzerOff()
{
  digitalWrite(BUZZER, LOW);
}

void countdownBeep()
{
  digitalWrite(BUZZER, HIGH);
  delay(150);
  digitalWrite(BUZZER, LOW);
}

void buzzerConfirm()
{
  // 3 short beeps — SOS sent.
  for (int i = 0; i < 3; i++)
  {
    digitalWrite(BUZZER, HIGH); delay(100);
    digitalWrite(BUZZER, LOW);  delay(100);
  }
}

void buzzerCancel()
{
  // 1 long beep — cancelled.
  digitalWrite(BUZZER, HIGH); delay(600);
  digitalWrite(BUZZER, LOW);
}

void buzzerTest()
{
  Serial.println();
  Serial.println("BUZZER TEST");
  Serial.println("----------------");

  for (int i = 0; i < 3; i++)
  {
    digitalWrite(BUZZER, HIGH); delay(300);
    digitalWrite(BUZZER, LOW);  delay(300);
  }

  Serial.println("BUZZER TEST COMPLETE");
}
// WIFI
bool connectWiFi()
{
  Serial.println();
  Serial.println("CONNECTING TO WIFI...");

  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

  unsigned long startTime = millis();

  while (WiFi.status() != WL_CONNECTED && millis() - startTime < 20000)
  {
    delay(500);
    Serial.print(".");
  }

  Serial.println();

  if (WiFi.status() == WL_CONNECTED)
  {
    Serial.println("WIFI CONNECTED");
    Serial.print("ESP8266 IP: ");
    Serial.println(WiFi.localIP());
    return true;
  }

  Serial.println("WIFI CONNECTION FAILED");
  return false;
}

bool ensureWiFi()
{
  if (WiFi.status() == WL_CONNECTED) return true;

  Serial.println();
  Serial.println("WIFI DISCONNECTED — RECONNECTING...");

  WiFi.disconnect();
  delay(500);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

  unsigned long startTime = millis();

  while (WiFi.status() != WL_CONNECTED && millis() - startTime < 15000)
  {
    delay(500);
    Serial.print(".");
  }

  Serial.println();

  if (WiFi.status() == WL_CONNECTED)
  {
    Serial.println("WIFI RECONNECTED");
    Serial.print("ESP8266 IP: ");
    Serial.println(WiFi.localIP());
    return true;
  }

  Serial.println("WIFI RECONNECT FAILED");
  return false;
}
// HTTP ERROR PRINT
void printHTTPError(int responseCode)
{
  Serial.println();
  Serial.println("================================");
  Serial.println("HTTP ERROR DETAILS");
  Serial.println("================================");

  if      (responseCode == 400) Serial.println("400 BAD REQUEST — Server rejected JSON");
  else if (responseCode == 401) Serial.println("401 UNAUTHORIZED");
  else if (responseCode == 403) Serial.println("403 FORBIDDEN");
  else if (responseCode == 404) Serial.println("404 NOT FOUND — Check FastAPI endpoint");
  else if (responseCode == 405) Serial.println("405 METHOD NOT ALLOWED");
  else if (responseCode == 422) Serial.println("422 VALIDATION ERROR — FastAPI rejected a field");
  else if (responseCode == 429) Serial.println("429 TOO MANY REQUESTS");
  else if (responseCode >= 300 && responseCode < 400) Serial.println("3xx REDIRECT");
  else if (responseCode >= 500) Serial.println("5xx SERVER ERROR");
  else { Serial.print("HTTP STATUS: "); Serial.println(responseCode); }

  Serial.println("================================");
}
// SIM900A HELPERS
void flushSIM900()
{
  while (sim900.available()) sim900.read();
}

bool waitForSIM900Response(const char* expected, unsigned long timeout)
{
  String response = "";
  unsigned long start = millis();

  while (millis() - start < timeout)
  {
    while (sim900.available())
    {
      char c = sim900.read();
      Serial.write(c);
      response += c;

      if (response.indexOf(expected) >= 0) return true;
      if (response.length() > 180) response.remove(0, 90);
    }
    delay(5);
  }

  return false;
}

bool sim900Test()
{
  Serial.println();
  Serial.println("================================");
  Serial.println("SIM900A TEST");
  Serial.println("================================");

  flushSIM900();
  sim900.println("AT");

  bool ok = waitForSIM900Response("OK", 3000);

  Serial.println();
  Serial.println(ok ? "SIM900A RESPONDING" : "SIM900A NOT RESPONDING");
  return ok;
}

bool sim900NetworkReady()
{
  Serial.println();
  Serial.println("CHECKING SIM CARD...");

  flushSIM900();
  sim900.println("AT+CPIN?");
  bool simReady = waitForSIM900Response("READY", 3000);

  Serial.println();
  Serial.println("CHECKING NETWORK...");

  flushSIM900();
  sim900.println("AT+CREG?");
  String response = "";
  unsigned long start = millis();

  while (millis() - start < 3000)
  {
    while (sim900.available())
    {
      char c = sim900.read();
      Serial.write(c);
      response += c;
    }
  }

  bool registered =
    response.indexOf("+CREG: 0,1") >= 0 ||
    response.indexOf("+CREG: 0,5") >= 0;

  Serial.println();

  if (simReady && registered)
  {
    Serial.println("SIM900A NETWORK READY");
    return true;
  }

  Serial.println("SIM900A NETWORK NOT READY");
  return false;
}

bool sendSOSSMS()
{
  Serial.println();
  Serial.println("================================");
  Serial.println("SENDING SOS SMS");
  Serial.println("================================");

  flushSIM900();
  sim900.println("AT+CMGF=1");

  if (!waitForSIM900Response("OK", 3000))
  {
    Serial.println("SMS MODE FAILED");
    return false;
  }

  bool allSent = true;

  for (int i = 0; i < NUM_EMERGENCY_CONTACTS; i++)
  {
    Serial.print("SENDING TO: ");
    Serial.println(EMERGENCY_NUMBERS[i]);

    flushSIM900();
    sim900.print("AT+CMGS=\"");
    sim900.print(EMERGENCY_NUMBERS[i]);
    sim900.println("\"");

    if (!waitForSIM900Response(">", 5000))
    {
      Serial.println("SMS PROMPT NOT RECEIVED");
      allSent = false;
      continue;
    }

    sim900.print(SOS_SMS_TEXT);
    sim900.write(26);

    bool sent = waitForSIM900Response("OK", 10000);
    Serial.println(sent ? "SMS SENT" : "SMS FAILED");
    if (!sent) allSent = false;
    
    delay(1000); // short pause between texts
  }

  return allSent;
}

bool makeSOSCall()
{
  Serial.println();
  Serial.println("================================");
  Serial.println("MAKING SOS PHONE CALL");
  Serial.println("================================");

  bool allCalled = true;

  for (int i = 0; i < NUM_EMERGENCY_CONTACTS; i++)
  {
    Serial.print("CALLING: ");
    Serial.println(EMERGENCY_NUMBERS[i]);

    flushSIM900();
    sim900.print("ATD");
    sim900.print(EMERGENCY_NUMBERS[i]);
    sim900.println(";");

    unsigned long start = millis();
    bool callStarted = false;

    while (millis() - start < 8000)
    {
      while (sim900.available()) Serial.write(sim900.read());
      delay(5);
      if (millis() - start > 1000) callStarted = true;
    }

    if (!callStarted)
    {
      Serial.println("CALL COMMAND FAILED");
      allCalled = false;
      continue;
    }

    Serial.println("CALL ACTIVE — WILL END IN 20 SECONDS");

    unsigned long callStart = millis();
    while (millis() - callStart < GSM_CALL_DURATION)
    {
      while (sim900.available()) Serial.write(sim900.read());
      delay(5);
    }

    Serial.println("ENDING SOS CALL");
    sim900.println("ATH");
    delay(1500);
    while (sim900.available()) Serial.write(sim900.read());
    delay(1000); // pause between calls
  }

  Serial.println();
  Serial.println("SOS CALL PROCESS COMPLETE");
  return allCalled;
}

void initializeSIM900A()
{
  if (!GSM_ENABLED)
  {
    Serial.println("GSM DISABLED");
    return;
  }

  sim900.begin(9600);
  delay(3000);

  Serial.println();
  Serial.println("================================");
  Serial.println("INITIALIZING SIM900A");
  Serial.println("================================");

  if (!sim900Test())
  {
    Serial.println("WARNING: SIM900A IS NOT RESPONDING");
    Serial.println("Check power, GND, TX/RX and baud rate.");
    return;
  }

  flushSIM900();
  sim900.println("ATE0");
  waitForSIM900Response("OK", 2000);

  flushSIM900();
  sim900.println("AT+CMEE=2");
  waitForSIM900Response("OK", 2000);

  flushSIM900();
  sim900.println("AT+CSQ");
  waitForSIM900Response("OK", 3000);

  sim900NetworkReady();
}
// BLOCK 6 — BUILD JSON PAYLOAD
// Assembles the full event contract JSON including the new
// event_id, confidence, severity, and features object.
String buildSOSJson(
  bool           manualButtonPressed,
  const String&  eventId,
  float          confidence,
  const String&  severity,
  const FeatureSet& feat
)
{
  String json = "{";

  json += "\"device_id\":\"";     json += VEHICLE_ID;    json += "\",";
  
  String sosType = "NONE";
  if (manualButtonPressed) sosType = "MANUAL";
  else if (severity != "NONE") sosType = "ACCIDENT";
  json += "\"sos_type\":\"";      json += sosType;       json += "\",";

  json += "\"accel_x\":"          + String(accelX,    3) + ",";
  json += "\"accel_y\":"          + String(accelY,    3) + ",";
  json += "\"accel_z\":"          + String(accelZ,    3) + ",";
  json += "\"gyro_x\":"           + String(gyroX,     3) + ",";
  json += "\"gyro_y\":"           + String(gyroY,     3) + ",";
  json += "\"gyro_z\":"           + String(gyroZ,     3) + ",";
  json += "\"impact_g\":"         + String(impactG,   3) + ",";
  
  json += "\"vibration\":";
  json += (impactG > 1.5f || manualButtonPressed) ? "true" : "false";
  json += ",";

  json += "\"temperature\":"      + String(dhtTemperatureC, 1) + ",";
  json += "\"humidity\":"         + String(dhtHumidityPct,  1) + ",";

  json += "\"gps_lat\":"          + String(gpsLat,    6) + ",";
  json += "\"gps_lon\":"          + String(gpsLon,    6) + ",";
  json += "\"gps_speed_kmph\":"   + String(gpsSpeedKmph, 2) + ",";
  json += "\"gps_fix\":";
  json += gpsFix ? "true" : "false";

  json += "}";
  return json;
}
// HTTP POST — single attempt (used by retry loop)
bool postSOSToServer(const String& json)
{
  if (!ensureWiFi())
  {
    Serial.println("HTTP POST SKIPPED — WIFI UNAVAILABLE");
    return false;
  }

  WiFiClientSecure client;
  client.setInsecure();
  client.setTimeout(20);

  HTTPClient http;
  http.setTimeout(20000);
  http.setFollowRedirects(HTTPC_FORCE_FOLLOW_REDIRECTS);
  http.setRedirectLimit(5);

  if (!http.begin(client, SERVER_URL))
  {
    Serial.println("HTTPS BEGIN FAILED");
    http.end();
    return false;
  }

  http.addHeader("Content-Type", "application/json");
  http.addHeader("Accept",       "application/json");
  http.addHeader("User-Agent",   "ESP8266-SOS");

  Serial.println();
  Serial.println("POSTING JSON TO RENDER...");

  int responseCode = http.POST(json);

  Serial.print("HTTP RESPONSE: ");
  Serial.println(responseCode);

  if (responseCode <= 0)
  {
    Serial.print("ERROR: ");
    Serial.println(http.errorToString(responseCode));
    http.end();
    return false;
  }

  String response = http.getString();
  Serial.println();
  Serial.println("SERVER RESPONSE:");
  Serial.println(response);

  http.end();

  bool success = (responseCode >= 200 && responseCode <= 299);

  if (!success) printHTTPError(responseCode);

  return success;
}
// BLOCK 5 (cont.) — PROCESS RETRY QUEUE
// Called every loop() iteration.
// Retries any pending SOS events.
void processRetryQueue()
{
  for (int i = 0; i < MAX_QUEUE_SIZE; i++)
  {
    QueuedSOS& q = sosQueue[i];
    if (!q.pending) continue;

    unsigned long now = millis();

    // Not yet time to retry.
    if (q.retryCount > 0 && now - q.lastAttemptMs < RETRY_INTERVAL_MS) continue;

    Serial.println();
    Serial.println("================================");
    Serial.print("QUEUE RETRY — SLOT ");
    Serial.print(i);
    Serial.print(" | ATTEMPT ");
    Serial.println(q.retryCount + 1);
    Serial.println("================================");

    bool sent = postSOSToServer(q.jsonPayload);
    q.lastAttemptMs = now;
    q.retryCount++;

    if (sent)
    {
      Serial.println("QUEUE DELIVERY CONFIRMED — SLOT " + String(i));
      q.pending = false;
      buzzerConfirm();
    }
    else if (q.retryCount >= MAX_RETRY_COUNT)
    {
      Serial.println("MAX RETRIES REACHED — DROPPING SLOT " + String(i));
      Serial.println("EVENT ID: " + q.eventId);
      q.pending = false;
    }
    else
    {
      Serial.print("WILL RETRY IN ");
      Serial.print(RETRY_INTERVAL_MS / 1000);
      Serial.println(" SECONDS");
    }
  }
}
// SEND SOS (builds JSON → enqueues → first attempt now)
void sendSOS(bool manualButtonPressed)
{
  Serial.println();
  Serial.println("================================");
  Serial.println("PREPARING SOS EVENT");
  Serial.println("================================");

  // Snapshot current sensor state.
  updateSensorData();

  // DHT11 — read temperature & humidity.
  readDHT11();

  // GPS — no module yet.
  gpsFix       = false;
  gpsLat       = FALLBACK_LATITUDE;
  gpsLon       = FALLBACK_LONGITUDE;
  gpsSpeedKmph = 0.0f;

  // --- Print sensor snapshot ---
  Serial.println();
  Serial.println("SENSOR SOURCE: " + sensorSource);
  Serial.println();
  Serial.println("SENSOR DATA");
  Serial.println("--------------------------------");
  Serial.print("accel_x = ");          Serial.println(accelX, 3);
  Serial.print("accel_y = ");          Serial.println(accelY, 3);
  Serial.print("accel_z = ");          Serial.println(accelZ, 3);
  Serial.print("gyro_x = ");           Serial.println(gyroX,  3);
  Serial.print("gyro_y = ");           Serial.println(gyroY,  3);
  Serial.print("gyro_z = ");           Serial.println(gyroZ,  3);
  Serial.print("impact_g = ");         Serial.println(impactG, 3);
  Serial.print("gps_lat = ");          Serial.println(gpsLat, 6);
  Serial.print("gps_lon = ");          Serial.println(gpsLon, 6);
  Serial.print("gps_speed_kmph = ");   Serial.println(gpsSpeedKmph, 2);
  Serial.print("gps_fix = ");          Serial.println(gpsFix ? "true" : "false");
  Serial.print("battery_pct = ");      Serial.println(batteryPct, 1);
  Serial.print("temperature_c = ");    Serial.println(dhtTemperatureC, 1);
  Serial.print("humidity_pct = ");     Serial.println(dhtHumidityPct,  1);
  Serial.print("dht_valid = ");        Serial.println(dhtAvailable ? "true" : "false");
  Serial.print("confidence = ");       Serial.println(accidentConfidence, 3);
  Serial.print("severity = ");         Serial.println(accidentSeverity);

  // --- Feature extraction printout ---
  Serial.println();
  Serial.println("EXTRACTED FEATURES");
  Serial.println("--------------------------------");
  Serial.print("peak_acceleration = ");     Serial.println(lastFeatures.peak_acceleration,     2);
  Serial.print("peak_jerk = ");             Serial.println(lastFeatures.peak_jerk,             2);
  Serial.print("peak_angular_velocity = "); Serial.println(lastFeatures.peak_angular_velocity, 2);
  Serial.print("velocity_change = ");       Serial.println(lastFeatures.velocity_change,       2);
  Serial.print("orientation_change = ");    Serial.println(lastFeatures.orientation_change,    2);
  Serial.print("post_impact_motion = ");    Serial.println(lastFeatures.post_impact_motion,    3);

  // --- GSM (SMS + call) ---
  if (GSM_ENABLED)
  {
    Serial.println();
    Serial.println("================================");
    Serial.println("GSM SOS NOTIFICATIONS");
    Serial.println("================================");

    if (sim900Test() && sim900NetworkReady())
    {
      sendSOSSMS();
      makeSOSCall();
    }
    else
    {
      Serial.println("GSM NOT READY — CALL/SMS SKIPPED");
      Serial.println("SERVER SOS WILL STILL BE ATTEMPTED");
    }
  }

  // --- Build JSON and enqueue ---
  String json = buildSOSJson(
    manualButtonPressed,
    currentEventId,
    accidentConfidence,
    accidentSeverity,
    lastFeatures
  );

  Serial.println();
  Serial.println("JSON PAYLOAD:");
  Serial.println(json);

  enqueueSOSEvent(currentEventId, json);

  // Trigger immediate delivery attempt via the retry queue on next tick.
}
// START MANUAL SOS
void startManualSOS()
{
  Serial.println();
  Serial.println("********************************");
  Serial.println("MANUAL SOS BUTTON PRESSED");
  Serial.println("10 SECOND COUNTDOWN");
  Serial.println("PRESS CANCEL TO STOP");
  Serial.println("********************************");

  // Confidence 1.0 for a manually triggered event.
  accidentConfidence = 1.0f;
  accidentSeverity   = "SEVERE";

  // Compute features even for manual (best-effort).
  lastFeatures = computeFeatures();

  // Generate event ID before countdown.
  currentEventId = generateEventId();

  currentState   = MANUAL_COUNTDOWN;
  countdownStart = millis();
  lastSecond     = -1;
}
// START ACCIDENT SOS
void startAccidentSOS()
{
  Serial.println();
  Serial.println("********************************");
  Serial.println("ACCIDENT DETECTED");
  Serial.print("SEVERITY: ");    Serial.println(accidentSeverity);
  Serial.print("CONFIDENCE: ");  Serial.println(accidentConfidence, 3);
  Serial.println("10 SECOND COUNTDOWN");
  Serial.println("PRESS CANCEL IF SAFE");
  Serial.println("********************************");

  // Event ID generated once here so the retry queue can reuse it.
  currentEventId = generateEventId();

  currentState   = ACCIDENT_COUNTDOWN;
  countdownStart = millis();
  lastSecond     = -1;
}
// ACTIVATE SOS
void activateSOS(bool manualButtonPressed)
{
  currentState = SOS_ACTIVE;

  Serial.println();
  Serial.println("================================");
  Serial.println("SOS ACTIVE — SENDING");
  Serial.println("================================");

  sendSOS(manualButtonPressed);

  buzzerOff();

  currentState = SAFE;
  lastSecond   = -1;

  Serial.println();
  Serial.println("SOS PROCESS COMPLETE");
  Serial.println("SYSTEM READY");
  Serial.println("MONITORING...");
  Serial.println();
}
// DETECT ACCIDENT
// Uses the ring buffer features + classifier instead of a
// single instantaneous threshold.
bool detectAccident()
{
  if (!mpuAvailable) return false;

  // -- Cooldown guard --
  if (millis() - lastAccidentTime < ACCIDENT_COOLDOWN) return false;

  // Compute features from ring buffer.
  FeatureSet f = computeFeatures();

  // Debug print every 500 ms.
  static unsigned long lastPrint = 0;
  if (millis() - lastPrint > 500)
  {
    lastPrint = millis();
    Serial.print("IMPACT_G: "); Serial.print(impactG, 2);
    Serial.print(" | TILT: ");  Serial.print(tiltAngle, 1);
    Serial.print(" | CONF: ");  Serial.print(accidentConfidence, 2);
    Serial.print(" | SEV: ");   Serial.println(accidentSeverity);
  }

  bool isAccident = classifyAccident(f);

  if (isAccident)
  {
    lastFeatures      = f;
    lastAccidentTime  = millis();

    Serial.println();
    Serial.println("!!! ACCIDENT DETECTED !!!");
    Serial.print("CONFIDENCE: ");  Serial.println(accidentConfidence, 3);
    Serial.print("SEVERITY:   ");  Serial.println(accidentSeverity);
    Serial.print("PEAK ACCEL: ");  Serial.println(f.peak_acceleration, 2);
    Serial.print("PEAK JERK:  ");  Serial.println(f.peak_jerk, 2);
    Serial.print("ORIENTATION CHANGE: "); Serial.println(f.orientation_change, 1);
  }

  return isAccident;
}
// MANUAL COUNTDOWN
void processManualCountdown()
{
  unsigned long elapsed = millis() - countdownStart;

  if (digitalRead(CANCEL_BUTTON) == LOW)
  {
    Serial.println();
    Serial.println("MANUAL SOS CANCELLED");

    buzzerCancel();
    buzzerOff();

    currentState = SAFE;
    lastSecond   = -1;

    delay(500);

    Serial.println("SYSTEM READY");
    Serial.println("MONITORING...");
    return;
  }

  int secondsLeft = 10 - (int)(elapsed / 1000);
  if (secondsLeft < 0) secondsLeft = 0;

  if (secondsLeft != lastSecond)
  {
    lastSecond = secondsLeft;
    Serial.print("SOS COUNTDOWN: ");
    Serial.println(secondsLeft);
    countdownBeep();
  }

  if (elapsed >= COUNTDOWN_TIME)
  {
    activateSOS(true);
  }
}
// ACCIDENT COUNTDOWN
void processAccidentCountdown()
{
  unsigned long elapsed = millis() - countdownStart;

  if (digitalRead(CANCEL_BUTTON) == LOW)
  {
    Serial.println();
    Serial.println("ACCIDENT ALERT CANCELLED");

    buzzerCancel();
    buzzerOff();

    currentState = SAFE;
    lastSecond   = -1;

    delay(500);

    Serial.println("SYSTEM READY");
    Serial.println("MONITORING...");
    return;
  }

  int secondsLeft = 10 - (int)(elapsed / 1000);
  if (secondsLeft < 0) secondsLeft = 0;

  if (secondsLeft != lastSecond)
  {
    lastSecond = secondsLeft;
    Serial.print("ACCIDENT COUNTDOWN: ");
    Serial.println(secondsLeft);
    countdownBeep();
  }

  if (elapsed >= COUNTDOWN_TIME)
  {
    activateSOS(false);
  }
}
// SETUP
void setup()
{
  Serial.begin(115200);
  delay(1000);

  Serial.println();
  Serial.println("====================================");
  Serial.println(" SMART VEHICLE SOS SYSTEM");
  Serial.println(" ESP8266 NODEMCU");
  Serial.println(" WIFI + HTTPS + RENDER");
  Serial.println(" WITH FEATURE EXTRACTION & QUEUE");
  Serial.println("====================================");

  randomSeed(analogRead(A0));

  // --- Buttons ---
  pinMode(SOS_BUTTON,    INPUT_PULLUP);
  pinMode(CANCEL_BUTTON, INPUT_PULLUP);

  // --- Buzzer ---
  pinMode(BUZZER, OUTPUT);
  buzzerOff();

  // --- I2C ---
  Wire.begin(SDA_PIN, SCL_PIN);

  // --- DHT11 ---
  dht.begin();
  Serial.println("DHT11 INITIALIZED (D3 / GPIO0)");

  // --- Startup tests ---
  buzzerTest();

  // --- Queue init ---
  initQueue();

  // --- SIM900A ---
  initializeSIM900A();

  // --- MPU6050 ---
  Serial.println();
  Serial.println("CHECKING MPU6050...");

  if (mpu.begin())
  {
    mpuAvailable = true;

    Serial.println("MPU6050 CONNECTED");

    mpu.setAccelerometerRange(MPU6050_RANGE_8_G);
    mpu.setGyroRange(MPU6050_RANGE_500_DEG);
    mpu.setFilterBandwidth(MPU6050_BAND_21_HZ);
  }
  else
  {
    mpuAvailable = false;

    Serial.println("MPU6050 NOT FOUND");
    Serial.println("SIMULATED SENSOR DATA ENABLED");
    Serial.println("ACCIDENT DETECTION DISABLED");
  }

  // --- WiFi ---
  connectWiFi();

  // --- Configuration summary ---
  Serial.println();
  Serial.println("====================================");
  Serial.println("SERVER CONFIGURATION");
  Serial.println("====================================");
  Serial.println("PROTOCOL: HTTPS");
  Serial.print("SERVER: ");   Serial.println(SERVER_URL);
  Serial.println("QUEUE:   UP TO 3 EVENTS, MAX 5 RETRIES");
  Serial.println("RETRY:   EVERY 30 SECONDS");
  Serial.println("SIM900A: ENABLED");
  Serial.print("CONTACTS:");
  for (int i = 0; i < NUM_EMERGENCY_CONTACTS; i++) {
    Serial.print(" ");
    Serial.print(EMERGENCY_NUMBERS[i]);
  }
  Serial.println();
  Serial.println("GPS:     NOT CONNECTED (FALLBACK)");
  Serial.println("BATTERY: STUB 100%");
  Serial.println();
  Serial.println("====================================");
  Serial.println("SYSTEM READY");
  Serial.println("====================================");
  Serial.println();
  Serial.println("SOS BUTTON  = D0 / GPIO16");
  Serial.println("CANCEL      = D4 / GPIO2");
  Serial.println("BUZZER      = D7 / GPIO13");
  Serial.println("SIM900A RX  = D5 / GPIO14");
  Serial.println("SIM900A TX  = D6 / GPIO12");
  Serial.println("MPU6050     = D2/D1 I2C");
  Serial.println(mpuAvailable ? "MPU STATUS  = REAL SENSOR" : "MPU STATUS  = SIMULATED");
  Serial.println();
  Serial.println("Press SOS button to test.");
  Serial.println("Monitoring for accidents...");
  Serial.println();
}
// LOOP
void loop()
{
  // -- Always tick the sensor buffer (Block 1) --
  tickSensorBuffer();

  // -- Always process the retry queue (Block 5) --
  processRetryQueue();
  // SAFE
  if (currentState == SAFE)
  {
    // -- Manual SOS button --
    if (digitalRead(SOS_BUTTON) == LOW)
    {
      delay(50);

      if (digitalRead(SOS_BUTTON) == LOW)
      {
        startManualSOS();

        while (digitalRead(SOS_BUTTON) == LOW) delay(10);
        delay(100);
      }
    }

    // -- Accident detection --
    if (currentState == SAFE)
    {
      if (detectAccident())
      {
        startAccidentSOS();
      }
    }

    delay(5);  // Reduced from 20 ms to keep buffer ticking at 50 Hz
  }
  // MANUAL COUNTDOWN
  else if (currentState == MANUAL_COUNTDOWN)
  {
    processManualCountdown();
  }
  // ACCIDENT COUNTDOWN
  else if (currentState == ACCIDENT_COUNTDOWN)
  {
    processAccidentCountdown();
  }
  // SOS ACTIVE
  else if (currentState == SOS_ACTIVE)
  {
    // Safety fallback — should not normally reach here
    // because activateSOS() resets state synchronously.
    buzzerOff();
    currentState = SAFE;
    Serial.println("SOS ACTIVE STATE RESET");
    Serial.println("MONITORING...");
  }
}