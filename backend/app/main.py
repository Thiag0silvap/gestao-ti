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
from app.routes import tickets
from app.routes.agent import router


def ensure_computer_columns() -> None:
    inspector = inspect(engine)

    if "computers" not in inspector.get_table_names():
        return

    existing_columns = {column["name"] for column in inspector.get_columns("computers")}
    missing_columns = []

    if "memory_type" not in existing_columns:
        missing_columns.append("ALTER TABLE computers ADD memory_type VARCHAR(50) NULL")

    if "memory_speed" not in existing_columns:
        missing_columns.append("ALTER TABLE computers ADD memory_speed VARCHAR(50) NULL")

    if "cpu_usage_percent" not in existing_columns:
        missing_columns.append("ALTER TABLE computers ADD cpu_usage_percent FLOAT NULL")

    if "memory_usage_percent" not in existing_columns:
        missing_columns.append("ALTER TABLE computers ADD memory_usage_percent FLOAT NULL")

    if "disk_free_gb" not in existing_columns:
        missing_columns.append("ALTER TABLE computers ADD disk_free_gb FLOAT NULL")

    if "disk_free_percent" not in existing_columns:
        missing_columns.append("ALTER TABLE computers ADD disk_free_percent FLOAT NULL")

    if "uptime_hours" not in existing_columns:
        missing_columns.append("ALTER TABLE computers ADD uptime_hours FLOAT NULL")

    if not missing_columns:
        return

    with engine.begin() as connection:
        for statement in missing_columns:
            connection.execute(text(statement))


Base.metadata.create_all(bind=engine)
ensure_computer_columns()

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
app.include_router(tickets.router)
app.include_router(router)

@app.get("/")
def root():
    return {"message": "API Gestão de TI rodando com sucesso!"}


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/db-test")
def db_test():
    with engine.connect() as conn:
        result = conn.execute(text("SELECT 1 AS teste"))
        row = result.fetchone()

    return {"database": "ok", "resultado": row[0]}
