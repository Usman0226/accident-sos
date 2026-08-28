from pydantic import BaseModel, Field
from typing import Optional

class HeartbeatEvent(BaseModel):
    device_id: str
    type: str = "heartbeat"
    timestamp: int
    gps_lat: float
    gps_lon: float
    gps_fix: bool
    speed_kmph: float
    battery_pct: int
    
class ImpactEvent(BaseModel):
    device_id: str
    type: str = "impact"
    timestamp: int
    impact_g: float
    gyro_delta: float
    gps_lat: float
    gps_lon: float
    gps_fix: bool
    
class ClassificationDecision(BaseModel):
    device_id: str
    decision: str
    confidence: float
    reason: str
