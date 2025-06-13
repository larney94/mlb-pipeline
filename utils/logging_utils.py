# utils/logging_utils.py

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

def get_rotating_logger(
    name: str,
    log_dir: str = "logs",
    level: str = "INFO",
    max_bytes: int = 2_000_000,
    backup_count: int = 3
) -> logging.Logger:
    """
    Creates a rotating logger instance configured with standardized format.

    Args:
        name (str): Name of the logger (used for file naming).
        log_dir (str): Directory where logs are stored.
        level (str): Logging level (e.g., 'INFO', 'DEBUG').
        max_bytes (int): Max log file size before rotation.
        backup_count (int): Number of rotated logs to retain.

    Returns:
        logging.Logger: Configured logger instance.
    """
    log_dir_path = Path(log_dir).resolve()
    log_dir_path.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))

    if not logger.handlers and not logger.hasHandlers():
        log_path = log_dir_path / f"{name}.log"
        handler = RotatingFileHandler(log_path, maxBytes=max_bytes, backupCount=backup_count)
        formatter = logging.Formatter(
            fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    return logger
    
def ensure_dir(path: Path):
    path.mkdir(parents=True, exist_ok=True)
