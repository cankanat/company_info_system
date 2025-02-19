import logging
import sys
from typing import Any
import json
from datetime import datetime
from functools import wraps
from app.config import get_settings

settings = get_settings()

class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        log_obj = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
        }
        
        if hasattr(record, 'props'):
            log_obj.update(record.props)

        return json.dumps(log_obj)

def setup_logger(name: str = __name__) -> logging.Logger:
    logger = logging.getLogger(name)
    
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(JsonFormatter())
        logger.addHandler(handler)
        
    logger.setLevel(settings.LOG_LEVEL)
    return logger

def log_error(logger: logging.Logger):
    def decorator(func: Any):
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                logger.error(
                    "Error in function execution",
                    extra={
                        "props": {
                            "function": func.__name__,
                            "error": str(e),
                            "args": str(args),
                            "kwargs": str(kwargs)
                        }
                    }
                )
                raise
        return wrapper
    return decorator

logger = setup_logger()