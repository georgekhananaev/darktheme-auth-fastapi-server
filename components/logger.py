import logging
from logging.handlers import RotatingFileHandler
import os

# Base log directory
log_dir = "logs"

# Ensure the log directory exists
os.makedirs(log_dir, exist_ok=True)

# Log file path
log_file = os.path.join(log_dir, "app.log")

# Set up logger
logger = logging.getLogger("app_logger")
logger.setLevel(logging.INFO)  # Set the logging level

# Create a file handler with rotation
handler = RotatingFileHandler(log_file, maxBytes=10 * 1024 * 1024, backupCount=1)  # 10MB per file, 1 backup
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)

# Add the handler to the logger
logger.addHandler(handler)


# Logging utility functions
def log_info(message: str):
    """
    Logs an informational message.

    This function logs the given message with INFO level using the configured logger.

    Args:
        message (str): The message to log.
    """
    logger.info(message)


def log_warning(message: str):
    """
    Logs a warning message.

    This function logs the given message with WARNING level using the configured logger.

    Args:
        message (str): The message to log.
    """
    logger.warning(message)


def log_error(message: str):
    """
    Logs an error message.

    This function logs the given message with ERROR level using the configured logger.

    Args:
        message (str): The message to log.
    """
    logger.error(message)
