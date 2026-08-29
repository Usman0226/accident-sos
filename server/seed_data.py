import httpx
import time
import asyncio

async def seed_data():
    base_url = "http://127.0.0.1:8000/api"
    
    current_time = int(time.time() * 1000)
    
    print("Seeding device VEH_001 (Normal Heartbeat)...")
    httpx.post(f"{base_url}/sensor", json={
        "device_id": "VEH_001",
        "sos_type": "NONE",
        "timestamp": current_time,
        "accel_x": 0.1, "accel_y": 0.1, "accel_z": 9.8,
        "gyro_x": 0.0, "gyro_y": 0.0, "gyro_z": 0.0,
        "impact_g": 0.0, "vibration": False,
        "temperature": 25.0, "humidity": 50.0,
        "gps_lat": 17.3850, "gps_lon": 78.4867,
        "gps_fix": True, "gps_speed_kmph": 42.0, "battery_pct": 87
    })
    
    print("Seeding device VEH_002 (Impact Detected)...")
    httpx.post(f"{base_url}/sensor", json={
        "device_id": "VEH_002",
        "sos_type": "ACCIDENT",
        "timestamp": current_time,
        "accel_x": 4.5, "accel_y": -2.3, "accel_z": 12.1,
        "gyro_x": 45.2, "gyro_y": -12.0, "gyro_z": 145.2,
        "impact_g": 8.7, "vibration": True,
        "temperature": 28.0, "humidity": 55.0,
        "gps_lat": 28.6139, "gps_lon": 77.2090,
        "gps_fix": True, "gps_speed_kmph": 48.5, "battery_pct": 74
    })
    
    await asyncio.sleep(2)
    
    print("Seeding device VEH_003 (Unreachable/Old Heartbeat)...")
    httpx.post(f"{base_url}/sensor", json={
        "device_id": "VEH_003",
        "sos_type": "NONE",
        "timestamp": current_time - 60000, 
        "accel_x": 0.0, "accel_y": 0.0, "accel_z": 9.8,
        "gyro_x": 0.0, "gyro_y": 0.0, "gyro_z": 0.0,
        "impact_g": 0.0, "vibration": False,
        "temperature": 24.0, "humidity": 45.0,
        "gps_lat": 19.0760, "gps_lon": 72.8777,
        "gps_fix": True, "gps_speed_kmph": 0.0, "battery_pct": 12
    })
    
    print("Fake data successfully seeded!")

if __name__ == "__main__":
    asyncio.run(seed_data())
