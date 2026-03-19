from urllib.parse import quote_plus
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from app.config import settings

connection_string = (
    f"DRIVER={{{settings.DB_DRIVER}}};"
    f"SERVER={settings.DB_SERVER};"
    f"DATABASE={settings.DB_DATABASE};"
    f"Trusted_Connection={settings.DB_TRUSTED_CONNECTION};"
    "TrustServerCertificate=yes;"
)

DATABASE_URL = f"mssql+pyodbc:///?odbc_connect={quote_plus(connection_string)}"

engine = create_engine(DATABASE_URL, echo=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()