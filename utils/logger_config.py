import logging
from pathlib import Path

# Crear carpeta de logs si no existe
Path("logs").mkdir(exist_ok=True)

# Configurar logger global
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.FileHandler("logs/api.log", encoding="utf-8"),
        logging.StreamHandler()
    ]
)

# Exportar logger
logger = logging.getLogger("ocr_api")