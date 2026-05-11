import uvicorn

from app.config import settings


def main() -> None:
    try:
        uvicorn.run(
            "app.main:app",
            host=settings.API_HOST,
            port=settings.API_PORT,
            reload=settings.API_RELOAD,
            log_level="info",
        )
    except KeyboardInterrupt:
        print("\n[INFO]  Desligando o servidor Gestão T.I...")


if __name__ == "__main__":
    main()
