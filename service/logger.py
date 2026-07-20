import json
import logging
from datetime import datetime, timezone
import os
from pathlib import Path
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # not installed in this environment (e.g. Docker)

_default = os.getenv("LOG_FILE")
if _default is None:
    raise RuntimeError("LOG_FILE environment variable must be set")

LOG_FILE = Path(_default)
LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    

class JSONFormatter(logging.Formatter):
    RESERVED = logging.LogRecord(
        "", 0, "", 0, "", (), None
    ).__dict__.keys()

    def format(self, record):
        log = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "message": record.getMessage(),
        }
        for key, value in record.__dict__.items():
            if key not in self.RESERVED and key not in log:
                log[key] = value
        return json.dumps(log, default=str)
    
logger = logging.getLogger("aiops")

logger.setLevel(logging.INFO)

logger.propagate = False

handler = logging.FileHandler(LOG_FILE)
handler.setFormatter(JSONFormatter())

logger.addHandler(handler)