from pathlib import Path
import logging
import sys
from logging.handlers import RotatingFileHandler

# Project root -> .../voicebot-service
ROOT = Path(__file__).resolve().parent.parent

# logs dir -> .../voicebot-service/logging
LOG_DIR = ROOT / "logging"
LOG_DIR.mkdir(parents=True, exist_ok=True)

LOG_FILE = LOG_DIR / "app.log"

FMT = "%(asctime)s - %(levelname)s - %(name)s - %(message)s"

def setup_logging() -> None:
    # Clear any existing handlers (prevents duplicates with --reload)
    for h in logging.root.handlers[:]:
        logging.root.removeHandler(h)

    file_h = RotatingFileHandler(
        LOG_FILE, maxBytes=50*1024*1024, backupCount=5, encoding="utf-8"
    )
    file_h.setFormatter(logging.Formatter(FMT))

    console_h = logging.StreamHandler(sys.stdout)   # no emojis, safe on Windows
    console_h.setFormatter(logging.Formatter(FMT))

    logging.basicConfig(level=logging.INFO, handlers=[file_h, console_h])

    # Make uvicorn logs go to the same  handlers
    for name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        l = logging.getLogger(name)
        l.setLevel(logging.INFO)
        l.handlers = [file_h, console_h]
        l.propagate = False

    logging.getLogger("log_setup").info(f"Logging to: {LOG_FILE}")
