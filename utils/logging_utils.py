import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

def setup_logger(
    name: str,
    log_dir: str = "logs",
    level: str = "INFO",
    max_bytes: int = 2_000_000,
    backup_count: int = 3
) -> logging.Logger:
    """
    Standard rotating logger setup used across the MLB pipeline.

    Args:
        name (str): Logger name (used for file naming and instance).
        log_dir (str): Directory where logs are written.
        level (str): Logging level ('DEBUG', 'INFO', 'WARNING', etc.)
        max_bytes (int): Maximum log file size before rotation.
        backup_count (int): Number of rotated log files to retain.

    Returns:
        logging.Logger: Configured logger instance.
    """
    log_dir_path = Path(log_dir).resolve()
    log_dir_path.mkdir(parents=True, exist_ok=True)
    log_path = log_dir_path / f"{name}.log"

    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))
    logger.handlers.clear()  # Ensure no duplicate handlers

    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    file_handler = RotatingFileHandler(log_path, maxBytes=max_bytes, backupCount=backup_count)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)

    return logger

def ensure_dir(path: Path):
    """
    Ensures a directory exists.
    """
    path.mkdir(parents=True, exist_ok=True)

# Alias for backward compatibility with legacy modules (e.g. cli_utils)
get_rotating_logger = setup_logger
