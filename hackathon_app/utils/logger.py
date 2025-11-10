"""
Logging Configuration for Tire Whisperer Dashboard

Provides centralized logging with file output and console display.
Logs are saved to hackathon_app/logs/ directory.
"""

import logging
import sys
from pathlib import Path
from datetime import datetime


# Create logs directory if it doesn't exist
LOG_DIR = Path(__file__).parent.parent / "logs"
LOG_DIR.mkdir(exist_ok=True)

# Log file path with timestamp
LOG_FILE = LOG_DIR / f"tire_whisperer_{datetime.now().strftime('%Y%m%d')}.log"


def setup_logger(name: str = "tire_whisperer", level: int = logging.DEBUG) -> logging.Logger:
    """
    Set up logger with file and console handlers.

    Args:
        name: Logger name
        level: Logging level (default: DEBUG)

    Returns:
        Configured logger instance
    """
    # Create logger
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # Avoid duplicate handlers
    if logger.handlers:
        return logger

    # Create formatters
    file_formatter = logging.Formatter(
        '%(asctime)s | %(name)s | %(levelname)s | %(funcName)s:%(lineno)d | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    console_formatter = logging.Formatter(
        '%(levelname)s | %(funcName)s | %(message)s'
    )

    # File handler (detailed logs)
    file_handler = logging.FileHandler(LOG_FILE, encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(file_formatter)

    # Console handler (important logs only)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.WARNING)
    console_handler.setFormatter(console_formatter)

    # Add handlers
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger


def log_exception(logger: logging.Logger, error: Exception, context: str = ""):
    """
    Log exception with full traceback and context.

    Args:
        logger: Logger instance
        error: Exception object
        context: Additional context information
    """
    import traceback

    error_msg = f"{context}\nError Type: {type(error).__name__}\nError Message: {str(error)}"
    logger.error(error_msg)
    logger.debug(f"Full Traceback:\n{traceback.format_exc()}")


def log_data_operation(logger: logging.Logger, operation: str, **kwargs):
    """
    Log data operation with parameters.

    Args:
        logger: Logger instance
        operation: Operation name
        **kwargs: Additional parameters to log
    """
    params_str = ", ".join([f"{k}={v}" for k, v in kwargs.items()])
    logger.debug(f"Data Operation: {operation} | Parameters: {params_str}")


# Global logger instance
app_logger = setup_logger()
