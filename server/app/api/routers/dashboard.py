from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import desc
from app.db.session import get_db
from app.models.domain import DeviceState, EventLog
import json
import time

router = APIRouter()

@router.get("/devices")
def get_devices(db: Session = Depends(get_db)):
    devices = db.query(DeviceState).all()
    current_time = int(time.time() * 1000)
    
    result = []
    for d in devices:
        status = d.status
        if status == "ok" and (current_time - d.last_heartbeat_time) > 30000:
            status = "unreachable"
            
        result.append({
            "device_id": d.device_id,
            "status": status,
            "last_heartbeat_time": d.last_heartbeat_time,
            "last_gps_lat": d.last_gps_lat,
            "last_gps_lon": d.last_gps_lon,
            "battery_pct": d.battery_pct
        })
    return {"devices": result}

@router.get("/events")
def get_events(limit: int = 50, db: Session = Depends(get_db)):
    events = db.query(EventLog).order_by(desc(EventLog.timestamp)).limit(limit).all()
    
    result = []
    for e in events:
        result.append({
            "id": e.id,
            "device_id": e.device_id,
            "timestamp": e.timestamp,
            "type": e.event_type,
            "payload": json.loads(e.payload)
        })
    return {"events": result}

@router.post("/devices/{device_id}/acknowledge")
def acknowledge_alert(device_id: str, db: Session = Depends(get_db)):
    device = db.query(DeviceState).filter(DeviceState.device_id == device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
        
    device.status = "ok"
    
    log_entry = EventLog(
        device_id=device_id,
        timestamp=int(time.time() * 1000),
        event_type="alert_acknowledged",
        payload=json.dumps({"actor": "human_operator"})
    )
    db.add(log_entry)
    db.commit()
    
    return {"status": "success", "message": f"Alert for {device_id} dismissed"}
