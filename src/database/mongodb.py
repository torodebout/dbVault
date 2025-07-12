"""
MongoDB database handler
"""

import subprocess
import os
import json
from typing import Dict, Any, Optional
from pathlib import Path

from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, PyMongoError

from .base import DatabaseHandler
from ..utils.logging import get_logger, BackupLogger

logger = get_logger(__name__)


class MongoDBHandler(DatabaseHandler):
    """Handler for MongoDB databases."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize MongoDB handler.
        
        Args:
            config: Database configuration dictionary
        """
        super().__init__(config)
        self.validate_config()
        
        self.auth_database = config.get('auth_database', self.database)
        
        if self.password:
            self.connection_uri = f"mongodb://{self.username}:{self.password}@{self.host}:{self.port}/{self.auth_database}"
        else:
            self.connection_uri = f"mongodb://{self.host}:{self.port}/{self.auth_database}"
        
        self.backup_logger = BackupLogger(__name__)
        
        if self.auth_database != self.database:
            logger.info(f"Using authentication database: {self.auth_database} for database: {self.database}")
    
    def test_connection(self) -> bool:
        """Test MongoDB connection.
        
        Returns:
            True if connection is successful, False otherwise
        """
        try:
            client = MongoClient(self.connection_uri, serverSelectionTimeoutMS=5000)
            
            db = client[self.database]
            db.command('ping')
            
            client.close()
            logger.info(f"MongoDB connection test successful: {self.host}:{self.port}/{self.database}")
            return True
        except ConnectionFailure as e:
            logger.error(f"MongoDB connection test failed: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error during MongoDB connection test: {e}")
            return False
    
    def create_backup(self, output_file: str) -> bool:
        """Create a MongoDB backup using mongodump.
        
        Args:
            output_file: Path where the backup archive should be created
            
        Returns:
            True if backup was successful, False otherwise
        """
        self.backup_logger.start_operation("backup", f"MongoDB database: {self.database}")
        
        try:
            output_path = Path(output_file)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            temp_dir = output_path.parent / f"temp_mongodump_{self.database}"
            temp_dir.mkdir(exist_ok=True)
            
            cmd = [
                'mongodump',
                '--host', f"{self.host}:{str(self.port)}",
                '--db', self.database,
                '--out', str(temp_dir)
            ]
            
            if self.username:
                cmd.extend(['--username', str(self.username)])
            if self.password:
                cmd.extend(['--password', str(self.password)])
            if self.username and self.auth_database:
                cmd.extend(['--authenticationDatabase', str(self.auth_database)])
            
            self.backup_logger.log_progress("Executing mongodump command")
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=3600
            )
            
            if result.returncode == 0:
                self.backup_logger.log_progress("Creating backup archive")
                
                tar_cmd = [
                    'tar',
                    '-czf', str(output_path),
                    '-C', str(temp_dir),
                    self.database
                ]
                
                tar_result = subprocess.run(
                    tar_cmd,
                    capture_output=True,
                    text=True
                )
                
                if tar_result.returncode == 0:
                    self._cleanup_directory(temp_dir)
                    
                    backup_size = output_path.stat().st_size if output_path.exists() else 0
                    size_mb = backup_size / (1024 * 1024)
                    
                    self.backup_logger.log_success(f"Backup created: {output_file} ({size_mb:.2f} MB)")
                    return True
                else:
                    self._cleanup_directory(temp_dir)
                    self.backup_logger.log_error(f"Failed to create backup archive: {tar_result.stderr}")
                    return False
            else:
                self._cleanup_directory(temp_dir)
                error_msg = f"mongodump failed with return code {result.returncode}"
                if result.stderr:
                    error_msg += f": {result.stderr}"
                self.backup_logger.log_error(error_msg)
                return False
                
        except subprocess.TimeoutExpired:
            self.backup_logger.log_error("Backup operation timed out after 1 hour")
            return False
        except FileNotFoundError:
            self.backup_logger.log_error("mongodump command not found. Please ensure MongoDB tools are installed.")
            return False
        except Exception as e:
            self.backup_logger.log_error(f"Unexpected error during backup: {e}", e)
            return False
    
    def restore_backup(self, backup_file: str) -> bool:
        """Restore MongoDB database from backup using mongorestore.
        
        Args:
            backup_file: Path to the backup archive file
            
        Returns:
            True if restore was successful, False otherwise
        """
        self.backup_logger.start_operation("restore", f"MongoDB database: {self.database}")
        
        try:
            backup_path = Path(backup_file)
            if not backup_path.exists():
                self.backup_logger.log_error(f"Backup file not found: {backup_file}")
                return False
            
            temp_dir = backup_path.parent / f"temp_mongorestore_{self.database}"
            temp_dir.mkdir(exist_ok=True)
            
            self.backup_logger.log_progress("Extracting backup archive")
            
            tar_cmd = [
                'tar',
                '-xzf', str(backup_path),
                '-C', str(temp_dir)
            ]
            
            tar_result = subprocess.run(
                tar_cmd,
                capture_output=True,
                text=True
            )
            
            if tar_result.returncode != 0:
                self._cleanup_directory(temp_dir)
                self.backup_logger.log_error(f"Failed to extract backup archive: {tar_result.stderr}")
                return False
            
            extracted_dirs = [d for d in temp_dir.iterdir() if d.is_dir()]
            if not extracted_dirs:
                self._cleanup_directory(temp_dir)
                self.backup_logger.log_error("No database directory found in backup archive")
                return False
            
            database_backup_dir = extracted_dirs[0]
            
            cmd = [
                'mongorestore',
                '--host', f"{self.host}:{str(self.port)}",
                '--db', self.database,
                '--drop',
                str(database_backup_dir)
            ]
            
            if self.username:
                cmd.extend(['--username', str(self.username)])
            if self.password:
                cmd.extend(['--password', str(self.password)])
            if self.username and self.auth_database:
                cmd.extend(['--authenticationDatabase', str(self.auth_database)])
            
            self.backup_logger.log_progress("Executing mongorestore command")
            
            logger.debug(f"mongorestore command: {cmd}")
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=3600
            )
            
            self._cleanup_directory(temp_dir)
            
            if result.returncode == 0:
                self.backup_logger.log_success(f"Database restored from: {backup_file}")
                return True
            else:
                error_msg = f"mongorestore failed with return code {result.returncode}"
                if result.stderr:
                    error_msg += f": {result.stderr}"
                self.backup_logger.log_error(error_msg)
                return False
                
        except subprocess.TimeoutExpired:
            self.backup_logger.log_error("Restore operation timed out after 1 hour")
            return False
        except FileNotFoundError:
            self.backup_logger.log_error("mongorestore command not found. Please ensure MongoDB tools are installed.")
            return False
        except Exception as e:
            self.backup_logger.log_error(f"Unexpected error during restore: {e}", e)
            return False
    
    def get_database_size(self) -> Optional[int]:
        """Get the size of the MongoDB database in bytes.
        
        Returns:
            Database size in bytes, or None if unable to determine
        """
        try:
            client = MongoClient(self.connection_uri)
            db = client[self.database]
            
            stats = db.command("dbStats")
            size = stats.get('dataSize', 0) + stats.get('indexSize', 0)
            
            client.close()
            logger.debug(f"MongoDB database size: {size} bytes")
            return size
            
        except PyMongoError as e:
            logger.error(f"Failed to get MongoDB database size: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error getting database size: {e}")
            return None
    
    def get_database_type(self) -> str:
        """Get the database type identifier.
        
        Returns:
            Database type string
        """
        return 'mongodb'
    
    def get_collections(self) -> Optional[list]:
        """Get list of collections in the database.
        
        Returns:
            List of collection names, or None if unable to retrieve
        """
        try:
            client = MongoClient(self.connection_uri)
            db = client[self.database]
            
            collections = db.list_collection_names()
            client.close()
            
            return collections
            
        except PyMongoError as e:
            logger.error(f"Failed to get collection list: {e}")
            return None
    
    def _cleanup_directory(self, directory: Path) -> None:
        """Remove directory and all its contents.
        
        Args:
            directory: Directory path to remove
        """
        try:
            import shutil
            if directory.exists():
                shutil.rmtree(directory)
                logger.debug(f"Cleaned up temporary directory: {directory}")
        except Exception as e:
            logger.warning(f"Failed to clean up temporary directory {directory}: {e}")
    
    def validate_config(self) -> None:
        """Validate MongoDB-specific configuration.
        
        Raises:
            ValueError: If configuration is invalid
        """
        super().validate_config()
        
        if self.port != 27017:
            logger.info(f"Using non-standard MongoDB port: {self.port}")
        
        if not self.username:
            logger.info("No username provided - attempting connection without authentication")
