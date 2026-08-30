# Accident SOS API Documentation

## Sensor Ingestion Server (`server/`, port 8000)

### GET /api/health
Description: Health check for the sensor ingestion server.

```bash
curl -X GET http://localhost:8000/api/health
```

Sample Response (200):
```json
{
  "status": "ok",
  "message": "Server is up and running healthy"
}
```

---

### POST /api/sensor
Description: Raw sensor data ingestion from IoT devices. Appends to local file.

```bash
curl -X POST http://localhost:8000/api/sensor \
  -H "Content-Type: application/json" \
  -d '{
    "accelerometer": {"x": 1.02, "y": -0.45, "z": 9.81},
    "gyroscope": {"x": 0.01, "y": -0.02, "z": 0.00},
    "device_id": "esp32-sensor-01"
  }'
```

Sample Response (200):
```json
{"message": "Sensor data received successfully", "Data : ": {...}}
```

---

### GET /api/sensor
Description: Retrieve stored raw sensor readings.

```bash
curl -X GET http://localhost:8000/api/sensor
```

---

## Classification Engine & ML Subsystems (`ml/`, port 8001)

### GET /api/health
Description: Health check and subsystem status for the classification engine.

```bash
curl -X GET http://localhost:8001/api/health
```

Sample Response (200):
```json
{
  "status": "ok",
  "service": "accident-classification-engine",
  "version": "1.0.0",
  "active_model_version": "v1",
  "subsystems": {
    "model_registry": "healthy",
    "safety_gate": "active",
    "drift_detector": "active",
    "training_pool": "active",
    "rl_policy_optimizer": "active"
  }
}
```

---

### POST /api/heartbeat
Description: Ingest device heartbeat telemetry. Updates speed, GPS cache, battery, and device status. Auto-registers unknown devices.

```bash
curl -X POST http://localhost:8001/api/heartbeat \
  -H "Content-Type: application/json" \
  -d '{
    "device_id": "VEH_001",
    "timestamp": 1724878000,
    "speed_kmph": 45.2,
    "battery_pct": 87,
    "gps_lat": 17.385,
    "gps_lon": 78.4867,
    "gps_fix": true
  }'
```

Sample Response (200):
```json
{"status": "ok", "device_status": "active"}
```

Error Codes: 422 (validation), 500 (server)

---

### POST /api/impact
Description: Process an impact event through the multi-stage intelligence pipeline: Calibrated RF classifier -> Drift Tracker -> Context-Aware Policy -> Deterministic Safety Gate Invariants.

```bash
curl -X POST http://localhost:8001/api/impact \
  -H "Content-Type: application/json" \
  -d '{
    "device_id": "VEH_001",
    "type": "impact",
    "timestamp": 1724878056,
    "impact_g": 8.7,
    "gyro_delta": 145.2,
    "gps_lat": 17.385,
    "gps_lon": 78.4867,
    "gps_fix": true
  }'
```

Sample Response (200) — accident detected:
```json
{
  "event_id": "evt_a1b2c3d4",
  "device_id": "VEH_001",
  "decision": "accident",
  "confidence": 0.85,
  "reason": "impact_g=8.70 | gyro_delta=145.20 | [v1] ML Pipeline (Calibrated RF): crash_prob=0.8408 | Policy: escalate (ML confidence 0.84 >= adjusted threshold 0.60)",
  "policy_action": "escalate",
  "safety_overridden": false,
  "gps": {"lat": 17.385, "lon": 78.4867, "is_approximate": false},
  "status": "PENDING"
}
```

Sample Response (200) — debounced duplicate:
```json
{
  "event_id": "evt_a1b2c3d4",
  "debounced": true,
  "message": "Impact already being processed for this device"
}
```

Error Codes: 422 (validation), 500 (server)

---

### GET /api/events/{event_id}
Description: Fetch event details and status.

```bash
curl -X GET http://localhost:8001/api/events/evt_a1b2c3d4
```

Sample Response (200):
```json
{
  "event_id": "evt_a1b2c3d4",
  "device_id": "VEH_001",
  "decision": "accident",
  "confidence": 0.85,
  "reason": "...",
  "gps": {"lat": 17.385, "lon": 78.4867, "is_approximate": false},
  "status": "PENDING",
  "created_at": 1724878056.123,
  "impact_snapshot": {...}
}
```

Error Codes: 404 (not found)

---

### PATCH /api/events/{event_id}
Description: Transition an event's status via the state machine.

Valid transitions:
- `"cancel"` on PENDING → CANCELLING
- `"cancel"` on CANCELLING → CANCELLED
- `"confirm"` on PENDING → CONFIRMED
- `"confirm"` on CANCELLING → CONFIRMED (override)

```bash
curl -X PATCH http://localhost:8001/api/events/evt_a1b2c3d4 \
  -H "Content-Type: application/json" \
  -d '{"action": "confirm"}'
```

Sample Response (200):
```json
{
  "event_id": "evt_a1b2c3d4",
  "status": "CONFIRMED",
  "message": "Transitioned PENDING → CONFIRMED"
}
```

Error Codes: 404 (not found), 409 (invalid transition), 422 (validation)

---

### GET /api/devices
Description: List all registered devices with current status.

```bash
curl -X GET http://localhost:8001/api/devices
```

---

### GET /api/devices/{device_id}
Description: Get a specific device's registry info.

```bash
curl -X GET http://localhost:8001/api/devices/VEH_001
```

Error Codes: 404 (not found)

---

### GET /api/devices/{device_id}/events
Description: List all events for a specific device, newest first.

```bash
curl -X GET http://localhost:8001/api/devices/VEH_001/events
```

Error Codes: 404 (device not found)

---

## ML Subsystem APIs

### GET /api/ml/drift
Description: Fetch feature distribution drift evaluated via Population Stability Index (PSI).

```bash
curl -X GET http://localhost:8001/api/ml/drift
```

Sample Response (200):
```json
{
  "status": "stable",
  "is_drifted": false,
  "reports": [
    {
      "feature_name": "impact_g",
      "psi_score": 0.0215,
      "is_drifted": false,
      "sample_count": 120,
      "timestamp": 1724878100.0
    }
  ],
  "stats": {
    "features_tracked": ["impact_g", "gyro_delta", "Speed_kmh"],
    "window_size": 500,
    "psi_threshold": 0.2
  }
}
```

---

### GET /api/ml/models
Description: List all model versions and manifest summary from the Model Registry.

```bash
curl -X GET http://localhost:8001/api/ml/models
```

Sample Response (200):
```json
{
  "active_version": "v1",
  "previous_version": null,
  "total_versions": 1,
  "versions": [
    {
      "version": "v1",
      "created_at": "2026-08-30T08:13:47Z",
      "dataset_hash": "8b7796fbab458470",
      "metrics": {"accuracy": 1.0, "f1_score": 0.996},
      "is_active": true,
      "promoted_at": "2026-08-30T08:13:47Z"
    }
  ]
}
```

---

### GET /api/ml/models/active
Description: Fetch metadata of the active production model.

```bash
curl -X GET http://localhost:8001/api/ml/models/active
```

---

### POST /api/ml/models/{version}/promote
Description: Promote a registered version to active status.

```bash
curl -X POST http://localhost:8001/api/ml/models/v2/promote
```

---

### POST /api/ml/models/rollback
Description: Roll back active model to the previously active version.

```bash
curl -X POST http://localhost:8001/api/ml/models/rollback
```

---

### GET /api/ml/models/compare
Description: Compare performance metrics between two model versions.

```bash
curl -X GET "http://localhost:8001/api/ml/models/compare?v1=v1&v2=v2"
```

---

### GET /api/ml/training/pool/stats
Description: Query the state of the continual learning training pool.

```bash
curl -X GET http://localhost:8001/api/ml/training/pool/stats
```

Sample Response (200):
```json
{
  "total_samples": 45,
  "crash_count": 15,
  "normal_count": 30,
  "crash_ratio": 0.3333,
  "is_ready_for_retraining": false,
  "sources": {
    "high_confidence_ml": 40,
    "manual_feedback": 5
  }
}
```

---

### POST /api/ml/training/retrain
Description: Trigger a continual retraining cycle against base data and pool signals with regression safety checks.

```bash
curl -X POST "http://localhost:8001/api/ml/training/retrain?auto_promote=false&force=true"
```

Sample Response (200):
```json
{
  "success": true,
  "candidate_version": "v2",
  "candidate_metrics": {"accuracy": 1.0, "f1_score": 0.996},
  "safety_check_passed": true,
  "reason": "Candidate model successfully trained and registered as v2."
}
```

---

### GET /api/ml/rl/stats
Description: Inspect Q-learning policy optimization and exploration metrics.

```bash
curl -X GET http://localhost:8001/api/ml/rl/stats
```

Sample Response (200):
```json
{
  "total_steps": 12,
  "total_rewards": 8.5,
  "average_reward": 0.7083,
  "epsilon": 0.1,
  "num_states": 256,
  "num_actions": 3
}
```

---

### POST /api/ml/rl/feedback
Description: Submit ground-truth operational feedback to update the RL Q-policy.

```bash
curl -X POST http://localhost:8001/api/ml/rl/feedback \
  -H "Content-Type: application/json" \
  -d '{
    "state_idx": 100,
    "action": "escalate",
    "actual_is_accident": true
  }'
```

Sample Response (200):
```json
{
  "status": "updated",
  "state_idx": 100,
  "action": "escalate",
  "reward": 1.0,
  "updated_q_value": 0.82
}
```
