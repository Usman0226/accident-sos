import time
from tests.conftest import client

def test_heartbeat():
    payload = {
        "device_id": "TEST_001",
        "type": "heartbeat",
        "timestamp": int(time.time() * 1000),
        "gps_lat": 17.3850,
        "gps_lon": 78.4867,
        "gps_fix": True,
        "speed_kmph": 45.0,
        "battery_pct": 85
    }
    response = client.post("/api/heartbeat", json=payload)
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    
def test_impact():
    payload = {
        "device_id": "TEST_001",
        "type": "impact",
        "timestamp": int(time.time() * 1000),
        "impact_g": 5.2,
        "gyro_delta": 150.0,
        "gps_lat": 17.3850,
        "gps_lon": 78.4867,
        "gps_fix": True
    }
    response = client.post("/api/impact", json=payload)
    assert response.status_code == 200
    assert "SOS dispatch initiated" in response.json()["message"]
    
    # Test Idempotency
    response2 = client.post("/api/impact", json=payload)
    assert response2.status_code == 200
    assert "idempotent" in response2.json()["message"]

def test_get_devices():
    response = client.get("/api/devices")
    assert response.status_code == 200
    devices = response.json().get("devices", [])
    assert len(devices) > 0
    assert devices[0]["device_id"] == "TEST_001"
