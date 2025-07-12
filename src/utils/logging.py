"""
Logging utilities for dbVault
"""

import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional


class ColoredFormatter(logging.Formatter):
    """Custom formatter with colors for different log levels."""
    
    COLORS = {
        'DEBUG': '\033[36m',
        'INFO': '\033[32m',
        'WARNING': '\033[33m',
        'ERROR': '\033[31m',
        'CRITICAL': '\033[35m',
        'RESET': '\033[0m'
    }
    
    def format(self, record):
        if hasattr(record, 'levelname'):
            color = self.COLORS.get(record.levelname, self.COLORS['RESET'])
            record.levelname = f"{color}{record.levelname}{self.COLORS['RESET']}"
        
        return super().format(record)


def setup_logging(verbose: bool = False, log_file: Optional[str] = None) -> None:
    """Setup logging configuration.
    
    Args:
        verbose: Enable debug logging
        log_file: Optional file to write logs to
    """
    log_level = logging.DEBUG if verbose else logging.INFO
    
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    colored_formatter = ColoredFormatter(
        '%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%H:%M:%S'
    )
    
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_handler.setFormatter(colored_formatter)
    root_logger.addHandler(console_handler)
    
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        file_handler = logging.FileHandler(log_path)
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)
    
    default_log_dir = Path.home() / '.dbvault' / 'logs'
    default_log_dir.mkdir(parents=True, exist_ok=True)
    
    log_filename = f"dbvault_{datetime.now().strftime('%Y%m%d')}.log"
    default_log_file = default_log_dir / log_filename
    
    file_handler = logging.FileHandler(default_log_file)
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance for the given name.
    
    Args:
        name: Logger name (usually __name__)
        
    Returns:
        Logger instance
    """
    return logging.getLogger(name)


class BackupLogger:
    """Specialized logger for backup operations."""
    
    def __init__(self, logger_name: str):
        self.logger = get_logger(logger_name)
        self.start_time = None
        self.operation = None
    
    def start_operation(self, operation: str, details: str = "") -> None:
        """Log the start of a backup operation.
        
        Args:
            operation: Operation name (e.g., 'backup', 'restore')
            details: Additional details about the operation
        """
        self.operation = operation
        self.start_time = datetime.now()
        
        message = f"Starting {operation}"
        if details:
            message += f": {details}"
            
        self.logger.info(message)
    
    def log_progress(self, message: str) -> None:
        """Log progress during an operation.
        
        Args:
            message: Progress message
        """
        self.logger.info(f"[{self.operation}] {message}")
    
    def log_success(self, result: str = "") -> None:
        """Log successful completion of an operation.
        
        Args:
            result: Result details
        """
        if self.start_time:
            duration = datetime.now() - self.start_time
            duration_str = f" (took {duration.total_seconds():.2f}s)"
        else:
            duration_str = ""
            
        message = f"{self.operation.title()} completed successfully{duration_str}"
        if result:
            message += f": {result}"
            
        self.logger.info(message)
    
    def log_error(self, error: str, exception: Optional[Exception] = None) -> None:
        """Log an error during an operation.
        
        Args:
            error: Error message
            exception: Optional exception for stack trace
        """
        if self.start_time:
            duration = datetime.now() - self.start_time
            duration_str = f" (failed after {duration.total_seconds():.2f}s)"
        else:
            duration_str = ""
            
        message = f"{self.operation.title()} failed{duration_str}: {error}"
        
        if exception:
            self.logger.error(message, exc_info=True)
        else:
            self.logger.error(message)
    
    def log_warning(self, warning: str) -> None:
        """Log a warning during an operation.
        
        Args:
            warning: Warning message
        """
        self.logger.warning(f"[{self.operation}] {warning}")


def log_backup_metrics(operation: str, database_type: str, database_name: str, 
                      backup_size: Optional[int] = None, duration: Optional[float] = None,
                      storage_type: str = "unknown") -> None:
    """Log backup metrics for monitoring purposes.
    
    Args:
        operation: Operation type ('backup' or 'restore')
        database_type: Type of database ('postgresql', 'mongodb')
        database_name: Name of the database
        backup_size: Size of backup file in bytes
        duration: Operation duration in seconds
        storage_type: Storage backend used
    """
    logger = get_logger('dbvault.metrics')
    
    metrics = {
        'operation': operation,
        'database_type': database_type,
        'database_name': database_name,
        'storage_type': storage_type,
        'timestamp': datetime.now().isoformat(),
    }
    
    if backup_size is not None:
        metrics['backup_size_bytes'] = backup_size
        metrics['backup_size_mb'] = round(backup_size / (1024 * 1024), 2)
    
    if duration is not None:
        metrics['duration_seconds'] = round(duration, 2)
    
    logger.info(f"METRICS: {metrics}")


def log_database_connection(database_type: str, host: str, database: str, success: bool) -> None:
    """Log database connection attempt.
    
    Args:
        database_type: Type of database
        host: Database host
        database: Database name
        success: Whether connection was successful
    """
    logger = get_logger('dbvault.connection')
    status = "successful" if success else "failed"
    logger.info(f"Database connection {status}: {database_type}://{host}/{database}")


def log_storage_operation(operation: str, storage_type: str, path: str, success: bool) -> None:
    """Log storage operation.
    
    Args:
        operation: Operation type ('upload', 'download', 'list')
        storage_type: Storage backend type
        path: File or directory path
        success: Whether operation was successful
    """
    logger = get_logger('dbvault.storage')
    status = "successful" if success else "failed"
    logger.info(f"Storage {operation} {status}: {storage_type}://{path}")
