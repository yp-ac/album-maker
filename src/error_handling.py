"""
Basic error handling and logging infrastructure for the Smart Album Maker.
"""

import logging
import sys
from typing import Optional
from pathlib import Path

# Configure logging
def setup_logging(log_level: str = "INFO", log_file: Optional[str] = None):
    """
    Setup logging configuration for the application.

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Optional log file path
    """
    # Create logger
    logger = logging.getLogger('album_maker')
    logger.setLevel(getattr(logging, log_level.upper()))

    # Remove existing handlers
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)

    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # File handler (if specified)
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        file_handler = logging.FileHandler(log_path)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger

# Global logger instance
logger = setup_logging()

class AlbumMakerError(Exception):
    """Base exception class for Album Maker errors."""
    pass

class ImageProcessingError(AlbumMakerError):
    """Exception raised for image processing errors."""
    pass

class DatabaseError(AlbumMakerError):
    """Exception raised for database operation errors."""
    pass

class ClusteringError(AlbumMakerError):
    """Exception raised for clustering algorithm errors."""
    pass

def handle_error(error: Exception, context: str = "", raise_error: bool = True):
    """
    Handle and log errors consistently.

    Args:
        error: The exception that occurred
        context: Additional context about where the error occurred
        raise_error: Whether to re-raise the error after logging
    """
    error_msg = f"Error in {context}: {str(error)}" if context else f"Error: {str(error)}"
    logger.error(error_msg, exc_info=True)

    if raise_error:
        raise error

def validate_image_file(file_path: str) -> bool:
    """
    Validate that a file exists and is a valid image.

    Args:
        file_path: Path to the image file

    Returns:
        bool: True if valid image file

    Raises:
        ImageProcessingError: If file is invalid
    """
    path = Path(file_path)

    if not path.exists():
        raise ImageProcessingError(f"Image file does not exist: {file_path}")

    if not path.is_file():
        raise ImageProcessingError(f"Path is not a file: {file_path}")

    # Check file extension (basic validation)
    valid_extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.webp'}
    if path.suffix.lower() not in valid_extensions:
        raise ImageProcessingError(f"Unsupported image format: {path.suffix}")

    return True

def safe_file_operation(operation_func, *args, **kwargs):
    """
    Wrapper for file operations with error handling.

    Args:
        operation_func: Function to execute
        *args, **kwargs: Arguments for the function

    Returns:
        Result of the operation

    Raises:
        AlbumMakerError: If operation fails
    """
    try:
        return operation_func(*args, **kwargs)
    except FileNotFoundError as e:
        raise ImageProcessingError(f"File not found: {e}")
    except PermissionError as e:
        raise ImageProcessingError(f"Permission denied: {e}")
    except OSError as e:
        raise ImageProcessingError(f"File system error: {e}")
    except Exception as e:
        raise AlbumMakerError(f"Unexpected error during file operation: {e}")