from pydantic import BaseModel, Field
from typing import Optional

class SensorDataPayload(BaseModel):
    device_id: str
    sos_type: str = "NONE"  # "ACCIDENT", "NONE", "FALL", "MANUAL"
    accel_x: float
    accel_y: float
    accel_z: float
    gyro_x: float
    gyro_y: float
    gyro_z: float
    impact_g: float
    vibration: bool = False
    temperature: float
    humidity: float
    gps_lat: float
    gps_lon: float
    gps_speed_kmph: float
    gps_fix: bool = True
    timestamp: Optional[int] = None
    battery_pct: Optional[int] = 85



class ClassificationDecision(BaseModel):
    device_id: str
    decision: str
    confidence: float
    reason: str
