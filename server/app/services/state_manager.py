import json
from sqlalchemy.orm import Session
from app.models.domain import DeviceState, EventLog
from app.models.schemas import SensorDataPayload

class StateManager:
    def __init__(self, db: Session):
        self.db = db
        
    def _log_event(self, device_id: str, event_type: str, payload: dict, timestamp: int):
        log_entry = EventLog(
            device_id=device_id,
            timestamp=timestamp,
            event_type=event_type,
            payload=json.dumps(payload)
        )
        self.db.add(log_entry)

    def process_heartbeat(self, event: SensorDataPayload):
        device = self.db.query(DeviceState).filter(DeviceState.device_id == event.device_id).first()
        
        if not device:
            device = DeviceState(
                device_id=event.device_id,
                status="ok"
            )
            self.db.add(device)
            
        device.last_heartbeat_time = event.timestamp
        device.last_gps_lat = event.gps_lat
        device.last_gps_lon = event.gps_lon
        device.last_speed_kmph = event.gps_speed_kmph
        device.battery_pct = event.battery_pct
        
        self._log_event(event.device_id, "heartbeat", event.model_dump(), event.timestamp)
        self.db.commit()
        return device

    def process_impact(self, event: SensorDataPayload):
        device = self.db.query(DeviceState).filter(DeviceState.device_id == event.device_id).first()
        is_new_event = False
        
        if not device:
            device = DeviceState(
                device_id=event.device_id,
                status="impact_detected",
                last_gps_lat=event.gps_lat,
                last_gps_lon=event.gps_lon
            )
            self.db.add(device)
            is_new_event = True
        else:
            if device.status != "impact_detected" and device.status != "sos_confirmed":
                device.status = "impact_detected"
                is_new_event = True
                
            device.last_gps_lat = event.gps_lat
            device.last_gps_lon = event.gps_lon
            
        if is_new_event:
            self._log_event(event.device_id, "impact", event.model_dump(), event.timestamp)
            self.db.commit()
            
        return device, is_new_event
