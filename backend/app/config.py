import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    DB_SERVER = os.getenv("DB_SERVER", r".\SQLEXPRESS")
    DB_DATABASE = os.getenv("DB_DATABASE", "GestaoTI")
    DB_TRUSTED_CONNECTION = os.getenv("DB_TRUSTED_CONNECTION", "yes")
    DB_DRIVER = os.getenv("DB_DRIVER", "ODBC Driver 17 for SQL Server")

    SECRET_KEY = os.getenv("SECRET_KEY", "changeme")
    ALGORITHM = os.getenv("ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))
    AGENT_API_KEY = os.getenv("AGENT_API_KEY", "changeme")
    API_HOST = os.getenv("API_HOST", "127.0.0.1")
    API_PORT = int(os.getenv("API_PORT", "8000"))
    API_RELOAD = os.getenv("API_RELOAD", "false").strip().lower() in {"1", "true", "yes", "sim", "on"}
    BACKEND_CORS_ORIGINS = [
        origin.strip()
        for origin in os.getenv(
            "BACKEND_CORS_ORIGINS",
            "http://localhost:5173,http://127.0.0.1:5173",
        ).split(",")
        if origin.strip()
    ]

settings = Settings()
