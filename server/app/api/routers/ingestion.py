from fastapi import APIRouter, Depends, BackgroundTasks
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.schemas import SensorDataPayload
from app.services.state_manager import StateManager
from app.services.sos_dispatcher import dispatch_sos_task

router = APIRouter()

@router.post("/sensor")
def receive_sos(event: SensorDataPayload, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    manager = StateManager(db)
    
    if event.sos_type == "NONE":
        # It's a heartbeat
        manager.process_heartbeat(event)
        return {"status": "success", "message": "Heartbeat received"}
    else:
        # It's an impact / SOS
        device, is_new_event = manager.process_impact(event)
        
        if is_new_event:
            background_tasks.add_task(dispatch_sos_task, event.device_id, event.model_dump())
            return {"status": "success", "message": "SOS received, dispatch initiated"}
        
        return {"status": "success", "message": "SOS already processed recently (idempotent)"}
