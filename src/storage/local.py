"""
Local filesystem storage handler
"""

import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List

from ..utils.logging import get_logger

logger = get_logger(__name__)


class LocalStorage:
    """Handler for local filesystem storage."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize local storage handler.
        
        Args:
            config: Storage configuration dictionary
        """
        self.config = config
        self.base_path = Path(config['path']).expanduser().resolve()
        
        self.base_path.mkdir(parents=True, exist_ok=True)
        logger.info(f"Local storage initialized: {self.base_path}")
    
    def store_backup(self, source_file: str, backup_name: str) -> str:
        """Store a backup file in local storage.
        
        Args:
            source_file: Path to the source backup file
            backup_name: Name for the stored backup file
            
        Returns:
            Path to the stored backup file
            
        Raises:
            FileNotFoundError: If source file doesn't exist
            OSError: If storage operation fails
        """
        source_path = Path(source_file)
        if not source_path.exists():
            raise FileNotFoundError(f"Source backup file not found: {source_file}")
        
        destination_path = self.base_path / backup_name
        
        try:
            shutil.copy2(source_path, destination_path)
            
            file_size = destination_path.stat().st_size
            size_mb = file_size / (1024 * 1024)
            
            logger.info(f"Backup stored locally: {destination_path} ({size_mb:.2f} MB)")
            return str(destination_path)
            
        except Exception as e:
            logger.error(f"Failed to store backup locally: {e}")
            raise OSError(f"Local storage operation failed: {e}")
    
    def retrieve_backup(self, backup_name: str, destination_file: str) -> str:
        """Retrieve a backup file from local storage.
        
        Args:
            backup_name: Name of the backup file to retrieve
            destination_file: Path where to save the retrieved file
            
        Returns:
            Path to the retrieved backup file
            
        Raises:
            FileNotFoundError: If backup file doesn't exist
            OSError: If retrieval operation fails
        """
        backup_path = self.base_path / backup_name
        if not backup_path.exists():
            raise FileNotFoundError(f"Backup file not found: {backup_path}")
        
        destination_path = Path(destination_file)
        destination_path.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            shutil.copy2(backup_path, destination_path)
            logger.info(f"Backup retrieved from local storage: {destination_path}")
            return str(destination_path)
            
        except Exception as e:
            logger.error(f"Failed to retrieve backup from local storage: {e}")
            raise OSError(f"Local retrieval operation failed: {e}")
    
    def list_backups(self) -> List[Dict[str, Any]]:
        """List all backup files in local storage.
        
        Returns:
            List of dictionaries containing backup file information
        """
        backups = []
        
        try:
            for file_path in self.base_path.iterdir():
                if file_path.is_file() and self._is_backup_file(file_path):
                    stat = file_path.stat()
                    
                    backup_info = {
                        'name': file_path.name,
                        'path': str(file_path),
                        'size': self._format_size(stat.st_size),
                        'size_bytes': stat.st_size,
                        'modified': datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M:%S'),
                        'modified_timestamp': stat.st_mtime
                    }
                    backups.append(backup_info)
            
            backups.sort(key=lambda x: x['modified_timestamp'], reverse=True)
            
            logger.info(f"Found {len(backups)} backup files in local storage")
            return backups
            
        except Exception as e:
            logger.error(f"Failed to list local backups: {e}")
            return []
    
    def delete_backup(self, backup_name: str) -> bool:
        """Delete a backup file from local storage.
        
        Args:
            backup_name: Name of the backup file to delete
            
        Returns:
            True if deletion was successful, False otherwise
        """
        backup_path = self.base_path / backup_name
        
        try:
            if backup_path.exists():
                backup_path.unlink()
                logger.info(f"Deleted backup from local storage: {backup_name}")
                return True
            else:
                logger.warning(f"Backup file not found for deletion: {backup_name}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to delete backup from local storage: {e}")
            return False
    
    def get_backup_path(self, backup_name: str) -> str:
        """Get the full path to a backup file.
        
        Args:
            backup_name: Name of the backup file
            
        Returns:
            Full path to the backup file
        """
        return str(self.base_path / backup_name)
    
    def backup_exists(self, backup_name: str) -> bool:
        """Check if a backup file exists in local storage.
        
        Args:
            backup_name: Name of the backup file
            
        Returns:
            True if backup exists, False otherwise
        """
        backup_path = self.base_path / backup_name
        return backup_path.exists() and backup_path.is_file()
    
    def get_available_space(self) -> Dict[str, int]:
        """Get available disk space information.
        
        Returns:
            Dictionary with space information in bytes
        """
        try:
            stat = shutil.disk_usage(self.base_path)
            return {
                'total': stat.total,
                'used': stat.used,
                'free': stat.free
            }
        except Exception as e:
            logger.error(f"Failed to get disk space information: {e}")
            return {'total': 0, 'used': 0, 'free': 0}
    
    def _is_backup_file(self, file_path: Path) -> bool:
        """Check if a file appears to be a backup file.
        
        Args:
            file_path: Path to the file
            
        Returns:
            True if file appears to be a backup file
        """
        backup_extensions = {'.sql', '.gz', '.tar', '.tar.gz', '.tgz', '.bak', '.dump'}
        
        if file_path.suffix.lower() in backup_extensions:
            return True
        
        if len(file_path.suffixes) >= 2:
            compound_suffix = ''.join(file_path.suffixes[-2:]).lower()
            if compound_suffix in {'.sql.gz', '.tar.gz'}:
                return True
        
        name_lower = file_path.name.lower()
        backup_patterns = ['backup', 'dump', 'export']
        
        return any(pattern in name_lower for pattern in backup_patterns)
    
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
    
    def get_storage_info(self) -> Dict[str, Any]:
        """Get storage information and statistics.
        
        Returns:
            Dictionary with storage information
        """
        space_info = self.get_available_space()
        backups = self.list_backups()
        
        total_backup_size = sum(backup['size_bytes'] for backup in backups)
        
        return {
            'type': 'local',
            'path': str(self.base_path),
            'backup_count': len(backups),
            'total_backup_size': self._format_size(total_backup_size),
            'total_backup_size_bytes': total_backup_size,
            'disk_space': {
                'total': self._format_size(space_info['total']),
                'used': self._format_size(space_info['used']),
                'free': self._format_size(space_info['free'])
            }
        }
    
    def __str__(self) -> str:
        """String representation of local storage."""
        return f"LocalStorage({self.base_path})"
