import logging
import sys

def setup_logging():
    # Remover handlers existentes do root logger para evitar duplicidade
    root = logging.getLogger()
    if root.handlers:
        for handler in root.handlers:
            root.removeHandler(handler)

    # Formato profissional e limpo
    log_format = "%(asctime)s | %(levelname)-8s | %(name)s - %(message)s"
    date_format = "%Y-%m-%d %H:%M:%S"

    # Configuração básica
    logging.basicConfig(
        level=logging.INFO,
        format=log_format,
        datefmt=date_format,
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )

    # Silenciar logs muito barulhentos de bibliotecas de terceiros
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("aioodbc").setLevel(logging.WARNING)

    # Personalizar o logger da aplicação
    logger = logging.getLogger("app")
    logger.setLevel(logging.INFO)
    
    logger.info("Sistema de logs profissional inicializado.")
