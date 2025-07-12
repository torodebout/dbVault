"""
PostgreSQL database handler
"""

import subprocess
import os
from typing import Dict, Any, Optional
from pathlib import Path

import psycopg2
from psycopg2 import sql

from .base import DatabaseHandler
from ..utils.logging import get_logger, BackupLogger

logger = get_logger(__name__)


class PostgreSQLHandler(DatabaseHandler):
    """Handler for PostgreSQL databases."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize PostgreSQL handler.
        
        Args:
            config: Database configuration dictionary
        """
        super().__init__(config)
        self.validate_config()
        
        self.connection_params = {
            'host': self.host,
            'port': self.port,
            'user': self.username,
            'password': self.password,
            'database': self.database
        }
        
        self.backup_logger = BackupLogger(__name__)
    
    def test_connection(self) -> bool:
        """Test PostgreSQL connection.
        
        Returns:
            True if connection is successful, False otherwise
        """
        try:
            conn = psycopg2.connect(**self.connection_params)
            conn.close()
            logger.info(f"PostgreSQL connection test successful: {self.host}:{self.port}/{self.database}")
            return True
        except psycopg2.Error as e:
            logger.error(f"PostgreSQL connection test failed: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error during PostgreSQL connection test: {e}")
            return False
    
    def create_backup(self, output_file: str) -> bool:
        """Create a PostgreSQL backup using pg_dump.
        
        Args:
            output_file: Path where the backup file should be created
            
        Returns:
            True if backup was successful, False otherwise
        """
        self.backup_logger.start_operation("backup", f"PostgreSQL database: {self.database}")
        
        try:
            output_path = Path(output_file)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            pg_dump_paths = [
                '/opt/homebrew/opt/postgresql@17/bin/pg_dump',
                '/opt/homebrew/bin/pg_dump',
                'pg_dump'
            ]
            
            pg_dump_cmd = None
            for path in pg_dump_paths:
                try:
                    if path.startswith('/'):
                        if Path(path).exists():
                            pg_dump_cmd = path
                            break
                    else:
                        subprocess.run([path, '--version'], capture_output=True, check=True)
                        pg_dump_cmd = path
                        break
                except (subprocess.CalledProcessError, FileNotFoundError):
                    continue
            
            if not pg_dump_cmd:
                raise FileNotFoundError("pg_dump command not found. Please ensure PostgreSQL client tools are installed.")
            
            cmd = [
                pg_dump_cmd,
                '--host', str(self.host),
                '--port', str(self.port),
                '--username', self.username,
                '--dbname', self.database,
                '--verbose',
                '--no-password',
                '--format=custom',
                '--file', output_file
            ]
            
            env = os.environ.copy()
            env['PGPASSWORD'] = self.password
            
            self.backup_logger.log_progress("Executing pg_dump command")
            
            result = subprocess.run(
                cmd,
                env=env,
                capture_output=True,
                text=True,
                timeout=3600
            )
            
            if result.returncode == 0:
                backup_size = output_path.stat().st_size if output_path.exists() else 0
                size_mb = backup_size / (1024 * 1024)
                
                self.backup_logger.log_success(f"Backup created: {output_file} ({size_mb:.2f} MB)")
                logger.info(f"pg_dump output: {result.stderr}")
                return True
            else:
                error_msg = f"pg_dump failed with return code {result.returncode}"
                if result.stderr:
                    error_msg += f": {result.stderr}"
                self.backup_logger.log_error(error_msg)
                return False
                
        except subprocess.TimeoutExpired:
            self.backup_logger.log_error("Backup operation timed out after 1 hour")
            return False
        except FileNotFoundError:
            self.backup_logger.log_error("pg_dump command not found. Please ensure PostgreSQL client tools are installed.")
            return False
        except Exception as e:
            self.backup_logger.log_error(f"Unexpected error during backup: {e}", e)
            return False
    
    def restore_backup(self, backup_file: str) -> bool:
        """Restore PostgreSQL database from backup using pg_restore.
        
        Args:
            backup_file: Path to the backup file
            
        Returns:
            True if restore was successful, False otherwise
        """
        self.backup_logger.start_operation("restore", f"PostgreSQL database: {self.database}")
        
        try:
            backup_path = Path(backup_file)
            if not backup_path.exists():
                self.backup_logger.log_error(f"Backup file not found: {backup_file}")
                return False
            
            is_custom_format = self._is_custom_format(backup_file)
            
            if is_custom_format:
                pg_restore_paths = [
                    '/opt/homebrew/opt/postgresql@17/bin/pg_restore',
                    '/opt/homebrew/bin/pg_restore',
                    'pg_restore'
                ]
                
                pg_restore_cmd = None
                for path in pg_restore_paths:
                    try:
                        if path.startswith('/'):
                            if Path(path).exists():
                                pg_restore_cmd = path
                                break
                        else:
                            subprocess.run([path, '--version'], capture_output=True, check=True)
                            pg_restore_cmd = path
                            break
                    except (subprocess.CalledProcessError, FileNotFoundError):
                        continue
                
                if not pg_restore_cmd:
                    raise FileNotFoundError("pg_restore command not found. Please ensure PostgreSQL client tools are installed.")
                
                cmd = [
                    pg_restore_cmd,
                    '--host', str(self.host),
                    '--port', str(self.port),
                    '--username', self.username,
                    '--dbname', self.database,
                    '--verbose',
                    '--no-password',
                    '--clean',
                    '--if-exists',
                    backup_file
                ]
            else:
                cmd = [
                    'psql',
                    '--host', str(self.host),
                    '--port', str(self.port),
                    '--username', self.username,
                    '--dbname', self.database,
                    '--file', backup_file,
                    '--no-password'
                ]
            
            env = os.environ.copy()
            env['PGPASSWORD'] = self.password
            
            command_name = 'pg_restore' if is_custom_format else 'psql'
            self.backup_logger.log_progress(f"Executing {command_name} command")
            
            result = subprocess.run(
                cmd,
                env=env,
                capture_output=True,
                text=True,
                timeout=3600
            )
            
            if result.returncode == 0:
                self.backup_logger.log_success(f"Database restored from: {backup_file}")
                if result.stderr:
                    logger.info(f"{command_name} output: {result.stderr}")
                return True
            else:
                error_msg = f"{command_name} failed with return code {result.returncode}"
                if result.stderr:
                    error_msg += f": {result.stderr}"
                self.backup_logger.log_error(error_msg)
                return False
                
        except subprocess.TimeoutExpired:
            self.backup_logger.log_error("Restore operation timed out after 1 hour")
            return False
        except FileNotFoundError as e:
            command = "pg_restore/psql"
            self.backup_logger.log_error(f"{command} command not found. Please ensure PostgreSQL client tools are installed.")
            return False
        except Exception as e:
            self.backup_logger.log_error(f"Unexpected error during restore: {e}", e)
            return False
    
    def get_database_size(self) -> Optional[int]:
        """Get the size of the PostgreSQL database in bytes.
        
        Returns:
            Database size in bytes, or None if unable to determine
        """
        try:
            conn = psycopg2.connect(**self.connection_params)
            cursor = conn.cursor()
            
            cursor.execute(
                sql.SQL("SELECT pg_database_size(%s)"),
                [self.database]
            )
            
            size = cursor.fetchone()[0]
            cursor.close()
            conn.close()
            
            logger.debug(f"PostgreSQL database size: {size} bytes")
            return size
            
        except psycopg2.Error as e:
            logger.error(f"Failed to get PostgreSQL database size: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error getting database size: {e}")
            return None
    
    def get_database_type(self) -> str:
        """Get the database type identifier.
        
        Returns:
            Database type string
        """
        return 'postgresql'
    
    def _is_custom_format(self, backup_file: str) -> bool:
        """Check if backup file is in PostgreSQL custom format.
        
        Args:
            backup_file: Path to backup file
            
        Returns:
            True if custom format, False if SQL format
        """
        try:
            with open(backup_file, 'rb') as f:
                header = f.read(5)
                return header == b'PGDMP'
        except Exception:
            return False
    
    def get_tables(self) -> Optional[list]:
        """Get list of tables in the database.
        
        Returns:
            List of table names, or None if unable to retrieve
        """
        try:
            conn = psycopg2.connect(**self.connection_params)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_type = 'BASE TABLE'
                ORDER BY table_name
            """)
            
            tables = [row[0] for row in cursor.fetchall()]
            cursor.close()
            conn.close()
            
            return tables
            
        except psycopg2.Error as e:
            logger.error(f"Failed to get table list: {e}")
            return None
