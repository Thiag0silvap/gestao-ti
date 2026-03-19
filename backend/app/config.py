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


settings = Settings()