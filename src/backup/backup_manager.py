"""
Backup manager - orchestrates backup operations
"""

import tempfile
from datetime import datetime
from pathlib import Path
from typing import Union

from ..database.base import DatabaseHandler
from ..storage.local import LocalStorage
from ..storage.aws_s3 import AWSS3Storage
from ..utils.compression import compress_file
from ..utils.logging import get_logger, BackupLogger, log_backup_metrics

logger = get_logger(__name__)


class BackupManager:
    """Manages backup operations across databases and storage backends."""
    
    def __init__(self, database_handler: DatabaseHandler, storage_handler: Union[LocalStorage, AWSS3Storage]):
        """Initialize backup manager.
        
        Args:
            database_handler: Database handler instance
            storage_handler: Storage handler instance
        """
        self.db_handler = database_handler
        self.storage_handler = storage_handler
        self.backup_logger = BackupLogger(__name__)
    
    def create_backup(self, compress: bool = True, custom_name: str = None) -> str:
        """Create a complete backup operation.
        
        Args:
            compress: Whether to compress the backup file
            custom_name: Custom name for the backup file (optional)
            
        Returns:
            Final backup file identifier/path
            
        Raises:
            Exception: If backup operation fails
        """
        start_time = datetime.now()
        
        if custom_name:
            backup_name = custom_name
        else:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            db_type = self.db_handler.get_database_type()
            db_name = self.db_handler.database
            backup_name = f"{db_name}_{db_type}_backup_{timestamp}"
        
        self.backup_logger.start_operation(
            "backup", 
            f"{self.db_handler.get_database_type()}://{self.db_handler.host}/{self.db_handler.database}"
        )
        
        temp_file = None
        compressed_file = None
        
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix='.dump') as temp:
                temp_file = temp.name
            
            self.backup_logger.log_progress("Creating database dump")
            
            if not self.db_handler.create_backup(temp_file):
                raise Exception("Database backup creation failed")
            
            temp_path = Path(temp_file)
            if not temp_path.exists() or temp_path.stat().st_size == 0:
                raise Exception("Backup file was not created or is empty")
            
            backup_size = temp_path.stat().st_size
            self.backup_logger.log_progress(f"Database dump created ({backup_size / (1024*1024):.2f} MB)")
            
            if compress:
                self.backup_logger.log_progress("Compressing backup file")
                compressed_file = compress_file(temp_file, backup_name + '.gz')
                final_backup_file = compressed_file
                final_backup_name = backup_name + '.gz'
            else:
                final_backup_file = temp_file
                final_backup_name = backup_name
            
            storage_type = type(self.storage_handler).__name__.lower()
            if 'local' in storage_type:
                storage_name = 'local'
            elif 's3' in storage_type:
                storage_name = 's3'
            else:
                storage_name = 'unknown'
            
            self.backup_logger.log_progress(f"Storing backup in {storage_name} storage")
            
            result = self.storage_handler.store_backup(final_backup_file, final_backup_name)
            
            duration = (datetime.now() - start_time).total_seconds()
            final_size = Path(final_backup_file).stat().st_size
            
            log_backup_metrics(
                operation='backup',
                database_type=self.db_handler.get_database_type(),
                database_name=self.db_handler.database,
                backup_size=final_size,
                duration=duration,
                storage_type=storage_name
            )
            
            self.backup_logger.log_success(f"Backup stored: {result}")
            return result
            
        except Exception as e:
            self.backup_logger.log_error(str(e), e)
            raise
        finally:
            self._cleanup_temp_files([temp_file, compressed_file])
    
    def verify_backup(self, backup_identifier: str) -> bool:
        """Verify that a backup exists and is accessible.
        
        Args:
            backup_identifier: Backup file name or identifier
            
        Returns:
            True if backup is valid and accessible
        """
        try:
            if hasattr(self.storage_handler, 'backup_exists'):
                return self.storage_handler.backup_exists(backup_identifier)
            else:
                backups = self.storage_handler.list_backups()
                return any(backup['name'] == backup_identifier for backup in backups)
        except Exception as e:
            logger.error(f"Error verifying backup: {e}")
            return False
    
    def estimate_backup_size(self) -> int:
        """Estimate the size of the backup that would be created.
        
        Returns:
            Estimated backup size in bytes, or 0 if unable to estimate
        """
        try:
            db_size = self.db_handler.get_database_size()
            if db_size is not None:
                estimated_compressed_size = int(db_size * 0.2)
                return estimated_compressed_size
            return 0
        except Exception as e:
            logger.warning(f"Unable to estimate backup size: {e}")
            return 0
    
    def get_backup_info(self) -> dict:
        """Get information about the backup configuration.
        
        Returns:
            Dictionary with backup configuration information
        """
        return {
            'database': {
                'type': self.db_handler.get_database_type(),
                'host': self.db_handler.host,
                'port': self.db_handler.port,
                'database': self.db_handler.database,
                'connection_string': self.db_handler.get_connection_string()
            },
            'storage': {
                'type': type(self.storage_handler).__name__,
                'info': self.storage_handler.get_storage_info() if hasattr(self.storage_handler, 'get_storage_info') else {}
            },
            'estimated_size': self.estimate_backup_size()
        }
    
    def _cleanup_temp_files(self, file_paths: list) -> None:
        """Clean up temporary files.
        
        Args:
            file_paths: List of file paths to clean up (can contain None values)
        """
        for file_path in file_paths:
            if file_path and Path(file_path).exists():
                try:
                    Path(file_path).unlink()
                    logger.debug(f"Cleaned up temporary file: {file_path}")
                except Exception as e:
                    logger.warning(f"Failed to clean up temporary file {file_path}: {e}")
    
    def __str__(self) -> str:
        """String representation of backup manager."""
        return f"BackupManager(db={self.db_handler}, storage={self.storage_handler})"
