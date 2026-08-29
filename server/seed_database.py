import sqlite3
import json
import time

def reset_and_seed_db():
    conn = sqlite3.connect("accident_sos.db")
    cursor = conn.cursor()

    # Clear existing tables
    cursor.execute("DELETE FROM device_states")
    cursor.execute("DELETE FROM event_logs")
    conn.commit()

    now = int(time.time() * 1000)

    # 1. Seed Clean Device States
    devices = [
        ("VEH_001", now - 2000, 17.3850, 78.4867, 42.5, 88, "ok"),
        ("VEH_002", now - 5000, 28.6139, 77.2090, 48.5, 74, "sos_confirmed"),
        ("VEH_003", now - 15000, 19.0760, 72.8777, 0.0, 15, "ok"),
        ("VEH_004", now - 3000, 12.9716, 77.5946, 55.2, 92, "ok"),
    ]

    cursor.executemany(
        "INSERT INTO device_states (device_id, last_heartbeat_time, last_gps_lat, last_gps_lon, last_speed_kmph, battery_pct, status) VALUES (?, ?, ?, ?, ?, ?, ?)",
        devices
    )

    # 2. Seed Clean Structured Event Logs
    events = [
        (
            "VEH_002",
            now - 5000,
            "impact",
            json.dumps({
                "device_id": "VEH_002",
                "sos_type": "ACCIDENT",
                "timestamp": now - 5000,
                "accel_x": 4.5, "accel_y": -2.3, "accel_z": 12.1,
                "gyro_x": 45.2, "gyro_y": -12.0, "gyro_z": 145.2,
                "impact_g": 8.7, "vibration": True,
                "temperature": 28.0, "humidity": 55.0,
                "gps_lat": 28.6139, "gps_lon": 77.2090,
                "gps_fix": True, "gps_speed_kmph": 48.5, "battery_pct": 74
            })
        ),
        (
            "VEH_002",
            now - 4500,
            "sos_dispatch",
            json.dumps({
                "device_id": "VEH_002",
                "type": "sos_dispatch",
                "timestamp": now - 4500,
                "method": "sms_and_cloud_api",
                "success": True,
                "recipient": "+91-9876543210",
                "attempt": 1,
                "emergency_service": "112_relay"
            })
        ),
        (
            "VEH_001",
            now - 2000,
            "heartbeat",
            json.dumps({
                "device_id": "VEH_001",
                "sos_type": "NONE",
                "timestamp": now - 2000,
                "accel_x": 0.1, "accel_y": 0.1, "accel_z": 9.8,
                "gyro_x": 0.0, "gyro_y": 0.0, "gyro_z": 0.0,
                "impact_g": 0.0, "vibration": False,
                "temperature": 25.0, "humidity": 50.0,
                "gps_lat": 17.3850, "gps_lon": 78.4867,
                "gps_fix": True, "gps_speed_kmph": 42.5, "battery_pct": 88
            })
        ),
        (
            "VEH_004",
            now - 3000,
            "heartbeat",
            json.dumps({
                "device_id": "VEH_004",
                "sos_type": "NONE",
                "timestamp": now - 3000,
                "accel_x": 0.1, "accel_y": 0.1, "accel_z": 9.8,
                "gyro_x": 0.0, "gyro_y": 0.0, "gyro_z": 0.0,
                "impact_g": 0.0, "vibration": False,
                "temperature": 25.0, "humidity": 50.0,
                "gps_lat": 12.9716, "gps_lon": 77.5946,
                "gps_fix": True, "gps_speed_kmph": 55.2, "battery_pct": 92
            })
        ),
        (
            "VEH_003",
            now - 15000,
            "heartbeat",
            json.dumps({
                "device_id": "VEH_003",
                "sos_type": "NONE",
                "timestamp": now - 15000,
                "accel_x": 0.1, "accel_y": 0.1, "accel_z": 9.8,
                "gyro_x": 0.0, "gyro_y": 0.0, "gyro_z": 0.0,
                "impact_g": 0.0, "vibration": False,
                "temperature": 25.0, "humidity": 50.0,
                "gps_lat": 19.0760, "gps_lon": 72.8777,
                "gps_fix": True, "gps_speed_kmph": 0.0, "battery_pct": 15
            })
        ),
        (
            "VEH_001",
            now - 32000,
            "heartbeat",
            json.dumps({
                "device_id": "VEH_001",
                "sos_type": "NONE",
                "timestamp": now - 32000,
                "accel_x": 0.1, "accel_y": 0.1, "accel_z": 9.8,
                "gyro_x": 0.0, "gyro_y": 0.0, "gyro_z": 0.0,
                "impact_g": 0.0, "vibration": False,
                "temperature": 25.0, "humidity": 50.0,
                "gps_lat": 17.3842, "gps_lon": 78.4855,
                "gps_fix": True, "gps_speed_kmph": 39.0, "battery_pct": 89
            })
        ),
    ]

    cursor.executemany(
        "INSERT INTO event_logs (device_id, timestamp, event_type, payload) VALUES (?, ?, ?, ?)",
        events
    )

    conn.commit()
    conn.close()
    print("Database successfully reset and seeded with valid formatted sensor records!")

    # Write clean sensor_data.json as well
    with open("sensor_data.json", "w") as f:
        f.write(json.dumps({
            "sensor_type": "mpu6050_imu_6dof",
            "device_id": "VEH_002",
            "timestamp": now - 5000,
            "readings": [6.80, 4.20, 1.90, 145.2, 32.4, 18.1],
            "total_g": 8.70,
            "status": "IMPACT_DETECTED"
        }) + "\n")
        f.write(json.dumps({
            "sensor_type": "mpu6050_imu_6dof",
            "device_id": "VEH_001",
            "timestamp": now - 2000,
            "readings": [0.08, 0.14, 0.99, 4.8, 1.2, 0.6],
            "total_g": 1.01,
            "status": "NORMAL_STREAM"
        }) + "\n")
    print("sensor_data.json updated!")

if __name__ == "__main__":
    reset_and_seed_db()
