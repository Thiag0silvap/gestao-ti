from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.database import Base, engine
from app.models.computer import Computer
from app.routes import computers
from app.routes import assets
from app.routes import dashboard
from app.routes import auth
from app.routes import tickets


Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Gestão de TI API",
    version="0.1.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(computers.router)
app.include_router(assets.router)
app.include_router(dashboard.router)
app.include_router(auth.router)
app.include_router(tickets.router)

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