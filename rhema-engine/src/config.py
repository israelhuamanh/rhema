import sys
from pathlib import Path

# Detectar si corre empaquetado con PyInstaller (sys.frozen) o desde código fuente
if getattr(sys, "frozen", False):
    _meipass = getattr(sys, "_MEIPASS", None)
    BASE_DIR = Path(_meipass) if _meipass else Path(sys.executable).resolve().parent
else:
    BASE_DIR = Path(__file__).resolve().parent.parent

MODELS_DIR = BASE_DIR / "models"
DATABASE_DIR = BASE_DIR / "database"

# Fallback adicional si en --onedir los recursos están junto al .exe
if not MODELS_DIR.exists() and getattr(sys, "frozen", False):
    exe_dir = Path(sys.executable).resolve().parent
    if (exe_dir / "models").exists():
        MODELS_DIR = exe_dir / "models"
    if (exe_dir / "database").exists():
        DATABASE_DIR = exe_dir / "database"

# Modelo Vosk oficial requerido
VOSK_MODEL_NAME = "vosk-model-small-es-0.42"
VOSK_MODEL_PATH = MODELS_DIR / VOSK_MODEL_NAME

# Base de datos SQLite
DB_PATH = DATABASE_DIR / "biblia_rv1960.db"
BIBLE_VERSION = "RVR1960"

# Configuración de Audio (Baja latencia)
SAMPLE_RATE = 16000
CHANNELS = 1
DTYPE = "int16"
# 4000 frames @ 16kHz = bloques de 250ms para respuesta < 1.5s
BLOCK_SIZE = 4000

# Configuración del Servidor WebSocket
WS_HOST = "127.0.0.1"
WS_PORT = 8765
