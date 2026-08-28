from fastapi import APIRouter, Depends, BackgroundTasks
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.schemas import HeartbeatEvent, ImpactEvent
from app.services.state_manager import StateManager
from app.services.sos_dispatcher import dispatch_sos_task

router = APIRouter()

@router.post("/heartbeat")
def receive_heartbeat(event: HeartbeatEvent, db: Session = Depends(get_db)):
    manager = StateManager(db)
    manager.process_heartbeat(event)
    return {"status": "success", "message": "Heartbeat received"}

@router.post("/impact")
def receive_impact(event: ImpactEvent, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    manager = StateManager(db)
    device, is_new_event = manager.process_impact(event)
    
    if is_new_event:
        background_tasks.add_task(dispatch_sos_task, event.device_id, event.model_dump())
        return {"status": "success", "message": "Impact received, SOS dispatch initiated"}
    
    return {"status": "success", "message": "Impact already processed recently (idempotent)"}
