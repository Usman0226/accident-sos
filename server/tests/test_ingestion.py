import time
from tests.conftest import client

def test_heartbeat():
    payload = {
        "device_id": "TEST_001",
        "sos_type": "NONE",
        "timestamp": int(time.time() * 1000),
        "accel_x": 0.1, "accel_y": 0.1, "accel_z": 9.8,
        "gyro_x": 0.0, "gyro_y": 0.0, "gyro_z": 0.0,
        "impact_g": 0.0, "vibration": False,
        "temperature": 25.0, "humidity": 50.0,
        "gps_lat": 17.3850, "gps_lon": 78.4867,
        "gps_fix": True, "gps_speed_kmph": 45.0, "battery_pct": 85
    }
    response = client.post("/api/sensor", json=payload)
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    
def test_impact():
    payload = {
        "device_id": "TEST_001",
        "sos_type": "ACCIDENT",
        "timestamp": int(time.time() * 1000),
        "accel_x": 4.5, "accel_y": -2.3, "accel_z": 12.1,
        "gyro_x": 45.2, "gyro_y": -12.0, "gyro_z": 145.2,
        "impact_g": 5.2, "vibration": True,
        "temperature": 28.0, "humidity": 55.0,
        "gps_lat": 17.3850, "gps_lon": 78.4867,
        "gps_fix": True, "gps_speed_kmph": 45.0, "battery_pct": 85
    }
    response = client.post("/api/sensor", json=payload)
    assert response.status_code == 200
    assert "dispatch initiated" in response.json()["message"]
    
    # Test Idempotency
    response2 = client.post("/api/sensor", json=payload)
    assert response2.status_code == 200
    assert "idempotent" in response2.json()["message"]

def test_get_devices():
    response = client.get("/api/devices")
    assert response.status_code == 200
    devices = response.json().get("devices", [])
    assert len(devices) > 0
    assert devices[0]["device_id"] == "TEST_001"
