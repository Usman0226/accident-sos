from sqlalchemy import Column, Integer, String, Float, Boolean
from sqlalchemy.orm import declarative_base

Base = declarative_base()

class DeviceState(Base):
    __tablename__ = "device_states"
    
    device_id = Column(String, primary_key=True, index=True)
    last_heartbeat_time = Column(Integer)
    last_gps_lat = Column(Float)
    last_gps_lon = Column(Float)
    last_speed_kmph = Column(Float)
    battery_pct = Column(Integer)
    
    status = Column(String, default="ok")
    
class EventLog(Base):
    __tablename__ = "event_logs"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    device_id = Column(String, index=True)
    timestamp = Column(Integer)
    event_type = Column(String)
    payload = Column(String)
