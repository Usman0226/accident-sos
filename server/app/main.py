from fastapi import FastAPI
from app.db.session import engine
from app.models import domain
from app.core.config import settings

domain.Base.metadata.create_all(bind=engine)

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "message": "Server is up and running healthy"
    }

from app.api.routers import ingestion, dashboard
app.include_router(ingestion.router, prefix="/api", tags=["ingestion"])
app.include_router(dashboard.router, prefix="/api", tags=["dashboard"])
