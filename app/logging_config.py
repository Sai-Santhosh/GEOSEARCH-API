"""
Production-grade structured logging configuration.
"""
import logging
import sys
from datetime import datetime, timezone
from typing import Any

import orjson

from .settings import settings


class JSONFormatter(logging.Formatter):
    """JSON log formatter for structured logging."""
    
    def format(self, record: logging.LogRecord) -> str:
        log_data: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        
        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        
        # Add extra fields
        if hasattr(record, "request_id"):
            log_data["request_id"] = record.request_id
        if hasattr(record, "user_agent"):
            log_data["user_agent"] = record.user_agent
        if hasattr(record, "client_ip"):
            log_data["client_ip"] = record.client_ip
        if hasattr(record, "duration_ms"):
            log_data["duration_ms"] = record.duration_ms
        if hasattr(record, "status_code"):
            log_data["status_code"] = record.status_code
        if hasattr(record, "path"):
            log_data["path"] = record.path
        if hasattr(record, "method"):
            log_data["method"] = record.method
        
        return orjson.dumps(log_data).decode("utf-8")


class TextFormatter(logging.Formatter):
    """Human-readable text formatter for development."""
    
    COLORS = {
        "DEBUG": "\033[36m",     # Cyan
        "INFO": "\033[32m",      # Green
        "WARNING": "\033[33m",   # Yellow
        "ERROR": "\033[31m",     # Red
        "CRITICAL": "\033[35m",  # Magenta
    }
    RESET = "\033[0m"
    
    def format(self, record: logging.LogRecord) -> str:
        color = self.COLORS.get(record.levelname, self.RESET)
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        
        base = f"{color}[{timestamp}] {record.levelname:8}{self.RESET} | {record.name} | {record.getMessage()}"
        
        # Add extra context
        extras = []
        if hasattr(record, "request_id"):
            extras.append(f"req_id={record.request_id}")
        if hasattr(record, "duration_ms"):
            extras.append(f"duration={record.duration_ms:.2f}ms")
        if hasattr(record, "status_code"):
            extras.append(f"status={record.status_code}")
        
        if extras:
            base += f" | {' '.join(extras)}"
        
        if record.exc_info:
            base += f"\n{self.formatException(record.exc_info)}"
        
        return base


def setup_logging() -> None:
    """Configure application logging."""
    root_logger = logging.getLogger()
    root_logger.setLevel(settings.log_level)
    
    # Clear existing handlers
    root_logger.handlers.clear()
    
    # Create handler
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(settings.log_level)
    
    # Set formatter based on config
    if settings.log_format == "json":
        formatter = JSONFormatter()
    else:
        formatter = TextFormatter()
    
    handler.setFormatter(formatter)
    root_logger.addHandler(handler)
    
    # Configure third-party loggers
    logging.getLogger("uvicorn").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(
        logging.DEBUG if settings.debug else logging.WARNING
    )


def get_logger(name: str) -> logging.Logger:
    """Get a configured logger instance."""
    return logging.getLogger(name)
