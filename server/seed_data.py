import httpx
import time
import asyncio

async def seed_data():
    base_url = "http://127.0.0.1:8000/api"
    
    current_time = int(time.time() * 1000)
    
    print("Seeding device VEH_001 (Normal Heartbeat)...")
    httpx.post(f"{base_url}/heartbeat", json={
        "device_id": "VEH_001",
        "type": "heartbeat",
        "timestamp": current_time,
        "gps_lat": 17.3850,
        "gps_lon": 78.4867,
        "gps_fix": True,
        "speed_kmph": 42.0,
        "battery_pct": 87
    })
    
    print("Seeding device VEH_002 (Impact Detected)...")
    httpx.post(f"{base_url}/impact", json={
        "device_id": "VEH_002",
        "type": "impact",
        "timestamp": current_time,
        "impact_g": 8.7,
        "gyro_delta": 145.2,
        "gps_lat": 28.6139,
        "gps_lon": 77.2090,
        "gps_fix": True
    })
    
    await asyncio.sleep(2)
    
    print("Seeding device VEH_003 (Unreachable/Old Heartbeat)...")
    httpx.post(f"{base_url}/heartbeat", json={
        "device_id": "VEH_003",
        "type": "heartbeat",
        "timestamp": current_time - 60000, 
        "gps_lat": 19.0760,
        "gps_lon": 72.8777,
        "gps_fix": True,
        "speed_kmph": 0.0,
        "battery_pct": 12
    })
    
    print("Fake data successfully seeded!")

if __name__ == "__main__":
    asyncio.run(seed_data())
