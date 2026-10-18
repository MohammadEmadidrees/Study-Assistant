import logging
import sys
import json
import time
from contextvars import ContextVar
from typing import Optional, Any

# Context variable for tracking request ID across async tasks
request_id_ctx: ContextVar[Optional[str]] = ContextVar("request_id", default=None)


class StructuredJsonFormatter(logging.Formatter):
    """
    Outputs log records as structured JSON dictionaries containing:
    timestamp, level, message, request_id, logger, and extra metric attributes.
    Ensures message prompts/bodies are never exposed at INFO level.
    """
    def format(self, record: logging.LogRecord) -> str:
        log_obj: dict[str, Any] = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": request_id_ctx.get() or getattr(record, "request_id", "N/A"),
        }

        # Include structured metrics if present
        for metric in ["latency_ms", "prompt_tokens", "completion_tokens", "total_tokens", "provider", "status_code"]:
            val = getattr(record, metric, None)
            if val is not None:
                log_obj[metric] = val

        if record.exc_info:
            log_obj["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_obj)


def setup_logging(debug: bool = False) -> logging.Logger:
    level = logging.DEBUG if debug else logging.INFO
    logger = logging.getLogger("study_assistant")
    logger.setLevel(level)

    # Avoid duplicate handlers if reloaded
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(level)
        formatter = StructuredJsonFormatter()
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    # Set root logger level
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.error").setLevel(logging.INFO)

    return logger


logger = setup_logging()
