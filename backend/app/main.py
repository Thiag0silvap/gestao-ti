from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import inspect, text

from app.config import settings
from app.database import Base, engine
import app.models  # noqa: F401
from app.routes import computers
from app.routes import assets
from app.routes import dashboard
from app.routes import alerts
from app.routes import auth
from app.routes import remote_actions
from app.routes import tickets
from app.core.logging import setup_logging
from app.routes.agent import router
from app.routes import audit
from app.routes import monitoring
from datetime import datetime

# Inicializar logs profissionais
setup_logging()


app = FastAPI(

    title="Gestão de TI API",
    version="0.1.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(computers.router)
app.include_router(assets.router)
app.include_router(dashboard.router)
app.include_router(alerts.router)
app.include_router(auth.router)
app.include_router(remote_actions.router)
app.include_router(tickets.router)
app.include_router(audit.router)
app.include_router(monitoring.router)
app.include_router(router)

from app.services.audit_service import log_action
from app.database import AsyncSessionLocal

@app.on_event("startup")
async def startup_event():
    # Registrar tempo de início para cálculo de uptime
    app.state.start_time = datetime.now()
    
    async with AsyncSessionLocal() as db:
        await log_action(
            db, 
            "SYSTEM_STARTUP", 
            details={"version": "0.1.0"},
            status="SUCCESS"
        )
        await db.commit()


@app.get("/")
def root():
    return {"message": "API Gestão de TI rodando com sucesso!"}
