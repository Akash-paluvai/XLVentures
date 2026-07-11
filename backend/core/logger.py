import logging
import sys
import contextvars
from backend.core.settings import settings

# Global request ID context variable for structured tracing
request_id_ctx_var: contextvars.ContextVar[str] = contextvars.ContextVar("request_id", default="-")


class RequestIdFilter(logging.Filter):
    def filter(self, record):
        # Set request_id attribute dynamically for the formatter to consume
        record.request_id = request_id_ctx_var.get()
        return True


def setup_logging():
    """
    Configure the root logger. This ensures all modules calling logging.getLogger(__name__)
    will automatically inherit this structured logging configuration.
    """
    log_level_name = settings.LOG_LEVEL.upper()
    log_level = getattr(logging, log_level_name, logging.INFO)
    
    # Clear any existing handlers on root
    root = logging.getLogger()
    for handler in root.handlers[:]:
        root.removeHandler(handler)
        
    # Configure root logger level and handler
    handler = logging.StreamHandler(sys.stdout)
    handler.addFilter(RequestIdFilter())
    
    formatter = logging.Formatter(
        fmt="%(asctime)s [%(levelname)s] [%(request_id)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    handler.setFormatter(formatter)
    
    root.addHandler(handler)
    root.setLevel(log_level)
