"""
Restore manager - orchestrates restore operations
"""

import tempfile
from datetime import datetime
from pathlib import Path
from typing import Union

from ..database.base import DatabaseHandler
from ..utils.compression import decompress_file
from ..utils.logging import get_logger, BackupLogger, log_backup_metrics

logger = get_logger(__name__)


class RestoreManager:
    """Manages restore operations for databases."""
    
    def __init__(self, database_handler: DatabaseHandler):
        """Initialize restore manager.
        
        Args:
            database_handler: Database handler instance
        """
        self.db_handler = database_handler
        self.backup_logger = BackupLogger(__name__)
    
    def restore_backup(self, backup_file: str) -> bool:
        """Restore database from a backup file.
        
        Args:
            backup_file: Path to the backup file
            
        Returns:
            True if restore was successful, False otherwise
            
        Raises:
            FileNotFoundError: If backup file doesn't exist
            Exception: If restore operation fails
        """
        start_time = datetime.now()
        backup_path = Path(backup_file)
        
        if not backup_path.exists():
            raise FileNotFoundError(f"Backup file not found: {backup_file}")
        
        self.backup_logger.start_operation(
            "restore",
            f"{self.db_handler.get_database_type()}://{self.db_handler.host}/{self.db_handler.database}"
        )
        
        decompressed_file = None
        
        try:
            if self._is_compressed_file(backup_file):
                self.backup_logger.log_progress("Decompressing backup file")
                
                with tempfile.NamedTemporaryFile(delete=False, suffix='.dump') as temp:
                    decompressed_file = temp.name
                
                decompress_file(backup_file, decompressed_file)
                restore_file = decompressed_file
            else:
                restore_file = backup_file
            
            self.backup_logger.log_progress("Testing database connection")
            if not self.db_handler.test_connection():
                raise Exception("Database connection test failed before restore")
            
            self.backup_logger.log_progress("Restoring database from backup")
            
            if not self.db_handler.restore_backup(restore_file):
                raise Exception("Database restore operation failed")
            
            duration = (datetime.now() - start_time).total_seconds()
            backup_size = backup_path.stat().st_size
            
            log_backup_metrics(
                operation='restore',
                database_type=self.db_handler.get_database_type(),
                database_name=self.db_handler.database,
                backup_size=backup_size,
                duration=duration,
                storage_type='local'
            )
            
            self.backup_logger.log_success(f"Database restored from: {backup_file}")
            return True
            
        except Exception as e:
            self.backup_logger.log_error(str(e), e)
            return False
        finally:
            if decompressed_file and Path(decompressed_file).exists():
                try:
                    Path(decompressed_file).unlink()
                    logger.debug(f"Cleaned up temporary file: {decompressed_file}")
                except Exception as e:
                    logger.warning(f"Failed to clean up temporary file: {e}")
    
    def validate_backup_file(self, backup_file: str) -> dict:
        """Validate a backup file and return information about it.
        
        Args:
            backup_file: Path to the backup file
            
        Returns:
            Dictionary with validation results and file information
        """
        backup_path = Path(backup_file)
        result = {
            'valid': False,
            'exists': backup_path.exists(),
            'size': 0,
            'size_formatted': '0 B',
            'compressed': False,
            'database_type': None,
            'errors': []
        }
        
        try:
            if not backup_path.exists():
                result['errors'].append(f"File does not exist: {backup_file}")
                return result
            
            stat = backup_path.stat()
            result['size'] = stat.st_size
            result['size_formatted'] = self._format_size(stat.st_size)
            
            if stat.st_size == 0:
                result['errors'].append("Backup file is empty")
                return result
            
            result['compressed'] = self._is_compressed_file(backup_file)
            
            result['database_type'] = self._identify_database_type(backup_file)
            
            if result['database_type']:
                db_validation = self._validate_database_backup(backup_file, result['database_type'])
                result['errors'].extend(db_validation.get('errors', []))
                if not db_validation.get('valid', False):
                    return result
            
            result['valid'] = len(result['errors']) == 0
            
        except Exception as e:
            result['errors'].append(f"Error validating backup file: {e}")
            logger.error(f"Error validating backup file {backup_file}: {e}")
        
        return result
    
    def _is_compressed_file(self, file_path: str) -> bool:
        """Check if a file is compressed.
        
        Args:
            file_path: Path to the file
            
        Returns:
            True if file appears to be compressed
        """
        path = Path(file_path)
        
        compressed_extensions = {'.gz', '.tar.gz', '.tgz', '.bz2', '.xz'}
        if path.suffix.lower() in compressed_extensions:
            return True
        
        if len(path.suffixes) >= 2:
            compound_suffix = ''.join(path.suffixes[-2:]).lower()
            if compound_suffix in {'.tar.gz', '.sql.gz'}:
                return True
        
        try:
            with open(file_path, 'rb') as f:
                header = f.read(10)
                if header.startswith(b'\x1f\x8b'):
                    return True
                if header.startswith(b'BZ'):
                    return True
        except Exception:
            pass
        
        return False
    
    def _identify_database_type(self, backup_file: str) -> str:
        """Try to identify the database type from the backup file.
        
        Args:
            backup_file: Path to the backup file
            
        Returns:
            Database type string or None if unable to identify
        """
        path = Path(backup_file)
        filename = path.name.lower()
        
        if 'postgres' in filename or 'pg_' in filename:
            return 'postgresql'
        elif 'mongo' in filename:
            return 'mongodb'
        
        if not self._is_compressed_file(backup_file):
            try:
                with open(backup_file, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read(1024)
                    if 'PostgreSQL' in content or 'pg_dump' in content:
                        return 'postgresql'
                    elif 'mongodump' in content or 'db.collection' in content:
                        return 'mongodb'
            except Exception:
                pass
        
        return None
    
    def _validate_database_backup(self, backup_file: str, db_type: str) -> dict:
        """Validate backup file for specific database type.
        
        Args:
            backup_file: Path to backup file
            db_type: Database type ('postgresql', 'mongodb')
            
        Returns:
            Dictionary with validation results
        """
        result = {'valid': True, 'errors': []}
        
        try:
            if db_type == 'postgresql':
                if self._is_compressed_file(backup_file):
                    pass
                else:
                    with open(backup_file, 'r', encoding='utf-8', errors='ignore') as f:
                        first_line = f.readline()
                        if not ('PostgreSQL' in first_line or 'pg_dump' in first_line or first_line.startswith('--')):
                            result['errors'].append("File does not appear to be a PostgreSQL dump")
                            result['valid'] = False
            
            elif db_type == 'mongodb':
                if backup_file.endswith('.tar.gz') or backup_file.endswith('.tgz'):
                    pass
                else:
                    result['errors'].append("MongoDB backup should be a .tar.gz archive")
                    result['valid'] = False
        
        except Exception as e:
            result['errors'].append(f"Error validating {db_type} backup: {e}")
            result['valid'] = False
        
        return result
    
    def _format_size(self, size_bytes: int) -> str:
        """Format file size in human-readable format.
        
        Args:
            size_bytes: Size in bytes
            
        Returns:
            Formatted size string
        """
        if size_bytes == 0:
            return "0 B"
        
        units = ['B', 'KB', 'MB', 'GB', 'TB']
        unit_index = 0
        size = float(size_bytes)
        
        while size >= 1024 and unit_index < len(units) - 1:
            size /= 1024
            unit_index += 1
        
        if unit_index == 0:
            return f"{int(size)} {units[unit_index]}"
        else:
            return f"{size:.1f} {units[unit_index]}"
    
    def __str__(self) -> str:
        """String representation of restore manager."""
        return f"RestoreManager(db={self.db_handler})"
