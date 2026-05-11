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
app.include_router(router)

@app.get("/")
def root():
    return {"message": "API Gestão de TI rodando com sucesso!"}


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/db-test")
async def db_test():
    async with engine.connect() as conn:
        result = await conn.execute(text("SELECT 1 AS teste"))
        row = result.fetchone()

    return {"database": "ok", "resultado": row[0]}
