import logging
import sys
from backend.core.settings import settings

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
    formatter = logging.Formatter(
        fmt="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    handler.setFormatter(formatter)
    
    root.addHandler(handler)
    root.setLevel(log_level)
