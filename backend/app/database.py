import os
from urllib.parse import quote_plus
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from app.config import settings

# Determinar a URL do banco de dados de forma flexível (Async)
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    if "sqlite" in settings.DB_DRIVER.lower():
        # Suporte para SQLite assíncrono
        DATABASE_URL = f"sqlite+aiosqlite:///./{settings.DB_DATABASE}.db"
    else:
        # Suporte para SQL Server assíncrono (Padrão Produção/Homologação)
        connection_string = (
            f"DRIVER={{{settings.DB_DRIVER}}};"
            f"SERVER={settings.DB_SERVER};"
            f"DATABASE={settings.DB_DATABASE};"
            f"Trusted_Connection={settings.DB_TRUSTED_CONNECTION};"
            "TrustServerCertificate=yes;"
        )
        DATABASE_URL = f"mssql+aioodbc:///?odbc_connect={quote_plus(connection_string)}"

# Create async engine
# pool_size: número de conexões mantidas abertas
# max_overflow: conexões extras permitidas em picos de carga
engine = create_async_engine(
    DATABASE_URL, 
    echo=os.getenv("DB_ECHO", "false").lower() == "true",
    pool_size=20,
    max_overflow=10,
    pool_timeout=10,
    pool_recycle=3600,
    pool_pre_ping=True
)

# Create async session factory
AsyncSessionLocal = async_sessionmaker(
    autocommit=False, 
    autoflush=False, 
    bind=engine, 
    class_=AsyncSession,
    expire_on_commit=False  # Important for Async to avoid lazy-loading/greenlet issues after commit
)

Base = declarative_base()


async def get_db():
    async with AsyncSessionLocal() as db:
        try:
            yield db
        finally:
            await db.close()