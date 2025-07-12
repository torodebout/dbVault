#!/usr/bin/env python3
"""
dbVault CLI - Main entry point
"""

import sys
from pathlib import Path
from typing import Optional

import click
from rich.console import Console
from rich.table import Table

from .config.config_manager import ConfigManager
from .database.factory import DatabaseFactory
from .storage.factory import StorageFactory
from .backup.backup_manager import BackupManager
from .restore.restore_manager import RestoreManager
from .utils.logging import setup_logging, get_logger

console = Console()
logger = get_logger(__name__)


@click.group()
@click.version_option(version="1.0.0")
@click.option('--verbose', '-v', is_flag=True, help='Enable verbose output')
def cli(verbose: bool):
    """dbVault - Database Backup Utility
    
    A command-line tool for backing up PostgreSQL and MongoDB databases
    to local storage or AWS S3.
    """
    setup_logging(verbose)


@cli.command()
@click.option('--output', '-o', default='config.yaml', help='Output configuration file name')
def init(output: str):
    """Initialize a new configuration file."""
    try:
        config_manager = ConfigManager()
        config_path = Path(output)
        
        if config_path.exists():
            if not click.confirm(f"Configuration file '{output}' already exists. Overwrite?"):
                console.print("❌ Configuration initialization cancelled.", style="yellow")
                return
        
        config_manager.create_default_config(config_path)
        console.print(f"✅ Configuration file created: {output}", style="green")
        console.print(f"📝 Please edit {output} with your database and storage settings.", style="blue")
        
    except Exception as e:
        console.print(f"❌ Error creating configuration: {e}", style="red")
        sys.exit(1)


@cli.command()
@click.option('--config', '-c', required=True, help='Configuration file path')
@click.option('--type', '-t', type=click.Choice(['database', 'storage', 'all']), 
              default='all', help='Type of connection to test')
@click.option('--storage', '-s', type=click.Choice(['local', 's3', 'aws', 'all']), 
              help='Storage backend to test (only used when --type is storage or all)')
def test(config: str, type: str, storage: Optional[str]):
    """Test database and/or storage connections."""
    try:
        config_manager = ConfigManager()
        config_data = config_manager.load_config(config)
        
        success = True
        
        if type in ['database', 'all']:
            console.print("🔍 Testing database connection...", style="blue")
            try:
                db_handler = DatabaseFactory.create_handler(config_data['database'])
                if db_handler.test_connection():
                    console.print("✅ Database connection successful!", style="green")
                else:
                    console.print("❌ Database connection failed!", style="red")
                    success = False
            except Exception as e:
                console.print(f"❌ Database connection failed: {e}", style="red")
                success = False
        
        if type in ['storage', 'all']:
            storage_backends = []
            
            if storage == 'all' or storage is None:
                if 'storage' in config_data:
                    if 'local' in config_data['storage']:
                        storage_backends.append('local')
                    if 'aws' in config_data['storage']:
                        storage_backends.append('s3')
            else:
                storage_type = storage if storage != 'aws' else 's3'
                storage_backends.append(storage_type)
            
            for backend in storage_backends:
                if backend == 'local':
                    console.print("🔍 Testing local storage...", style="blue")
                    try:
                        if 'storage' not in config_data or 'local' not in config_data['storage']:
                            console.print("❌ No local storage configuration found", style="red")
                            success = False
                            continue
                        
                        local_handler = StorageFactory.create_handler('local', config_data['storage'])
                        backup_path = Path(local_handler.base_path)
                        backup_path.mkdir(parents=True, exist_ok=True)
                        
                        console.print("✅ Local storage accessible!", style="green")
                        console.print(f"📁 Backup directory: {backup_path}", style="cyan")
                        
                        backups = local_handler.list_backups()
                        console.print(f"� Found {len(backups)} backup(s) in local storage", style="blue")
                        
                    except Exception as e:
                        console.print(f"❌ Local storage test failed: {e}", style="red")
                        success = False
                
                elif backend == 's3':
                    console.print("🔍 Testing S3 storage...", style="blue")
                    try:
                        if 'storage' not in config_data or 'aws' not in config_data['storage']:
                            console.print("❌ No AWS S3 configuration found in config file", style="red")
                            success = False
                            continue
                        
                        s3_handler = StorageFactory.create_handler('s3', config_data['storage'])
                        
                        console.print("📡 Checking bucket access...", style="blue")
                        backups = s3_handler.list_backups()
                        
                        console.print("✅ S3 connection successful!", style="green")
                        bucket_name = config_data['storage']['aws']['bucket']
                        console.print(f"🪣 Bucket: {bucket_name}", style="cyan")
                        console.print(f"📋 Found {len(backups)} backup(s) in S3", style="blue")
                        
                        if backups:
                            console.print("📋 Recent backups:", style="blue")
                            for backup in backups[:3]:
                                console.print(f"  • {backup['name']} ({backup.get('size', 'Unknown')})", style="dim")
                        
                    except Exception as e:
                        console.print(f"❌ S3 connection test failed: {e}", style="red")
                        success = False
        
        if success:
            console.print("🎉 All tests passed!", style="bold green")
        else:
            console.print("❌ Some tests failed!", style="bold red")
            sys.exit(1)
            
    except Exception as e:
        console.print(f"❌ Error during testing: {e}", style="red")
        logger.error(f"Test failed: {e}", exc_info=True)
        sys.exit(1)


@cli.command()
@click.option('--config', '-c', required=True, help='Configuration file path')
@click.option('--storage', '-s', type=click.Choice(['local', 's3', 'aws']), 
              help='Storage backend (overrides config default)')
def backup(config: str, storage: Optional[str]):
    """Create a database backup."""
    try:
        config_manager = ConfigManager()
        config_data = config_manager.load_config(config)
        
        storage_type = storage or config_data.get('backup', {}).get('default_storage', 'local')
        if storage_type == 'aws':
            storage_type = 's3' 
            
        console.print(f"🚀 Starting backup to {storage_type} storage...", style="blue")
        
        db_handler = DatabaseFactory.create_handler(config_data['database'])
        storage_handler = StorageFactory.create_handler(storage_type, config_data['storage'])
        
        backup_manager = BackupManager(db_handler, storage_handler)
        backup_file = backup_manager.create_backup(
            compress=config_data.get('backup', {}).get('compression', True)
        )
        
        console.print(f"✅ Backup completed: {backup_file}", style="green")
        
    except Exception as e:
        console.print(f"❌ Backup failed: {e}", style="red")
        logger.error(f"Backup failed: {e}", exc_info=True)
        sys.exit(1)


@cli.command()
@click.option('--backup', '-b', required=True, help='Backup file to restore from (local path or S3 backup name)')
@click.option('--config', '-c', required=True, help='Configuration file path')
@click.option('--storage', '-s', type=click.Choice(['local', 's3', 'aws']), 
              help='Storage backend (auto-detected from backup path if not specified)')
def restore(backup: str, config: str, storage: Optional[str]):
    """Restore database from backup."""
    import tempfile
    
    try:
        config_manager = ConfigManager()
        config_data = config_manager.load_config(config)
        
        storage_type = storage
        if not storage_type:
            if backup.startswith('s3://') or not Path(backup).exists():
                storage_type = 's3'
            else:
                storage_type = 'local'
        
        if storage_type == 'aws':
            storage_type = 's3' 
        
        console.print(f"🔄 Starting restore from {backup} ({storage_type} storage)...", style="blue")
        
        db_handler = DatabaseFactory.create_handler(config_data['database'])
        
        local_backup_file = backup
        temp_file = None
        
        if storage_type == 's3':
            console.print("📥 Downloading backup from S3...", style="blue")
            s3_handler = StorageFactory.create_handler('s3', config_data['storage'])
            
            with tempfile.NamedTemporaryFile(delete=False, suffix='.backup') as temp:
                temp_file = temp.name
            
            backup_name = backup
            if backup.startswith('s3://'):
                backup_name = backup.split('/')[-1]
            
            s3_handler.download_backup(backup_name, temp_file)
            local_backup_file = temp_file
            console.print(f"📥 Downloaded to temporary file", style="blue")
        
        restore_manager = RestoreManager(db_handler)
        restore_manager.restore_backup(local_backup_file)
        
        console.print("✅ Restore completed successfully!", style="green")
        
    except Exception as e:
        console.print(f"❌ Restore failed: {e}", style="red")
        logger.error(f"Restore failed: {e}", exc_info=True)
        sys.exit(1)
    finally:
        if temp_file and Path(temp_file).exists():
            try:
                Path(temp_file).unlink()
                logger.debug(f"Cleaned up temporary file: {temp_file}")
            except Exception as e:
                logger.warning(f"Failed to clean up temporary file {temp_file}: {e}")


@cli.command()
@click.option('--storage', '-s', type=click.Choice(['local', 's3', 'aws']), 
              default='local', help='Storage backend to list')
@click.option('--config', '-c', help='Configuration file path (required for S3)')
def list_backups(storage: str, config: Optional[str]):
    """List available backups."""
    try:
        storage_type = storage
        if storage_type == 'aws':
            storage_type = 's3'
            
        if storage_type == 's3' and not config:
            console.print("❌ Configuration file required for S3 storage", style="red")
            sys.exit(1)
            
        config_data = None
        if config:
            config_manager = ConfigManager()
            config_data = config_manager.load_config(config)
        
        if storage_type == 'local':
            if config_data:
                storage_handler = StorageFactory.create_handler('local', config_data['storage'])
            else:
                storage_handler = StorageFactory.create_handler('local', {'local': {'path': '~/backups'}})
        elif storage_type == 's3':
            storage_handler = StorageFactory.create_handler('s3', config_data['storage'])
        
        backups = storage_handler.list_backups()
        
        if not backups:
            console.print("📁 No backups found.", style="yellow")
            return
            
        table = Table(title=f"Available Backups ({storage_type.upper()})")
        table.add_column("Filename", style="cyan")
        table.add_column("Size", style="magenta")
        table.add_column("Modified", style="green")
        
        for backup_info in backups:
            table.add_row(
                backup_info['name'],
                backup_info.get('size', 'Unknown'),
                backup_info.get('modified', 'Unknown')
            )
            
        console.print(table)
        
    except Exception as e:
        console.print(f"❌ Error listing backups: {e}", style="red")
        sys.exit(1)


if __name__ == '__main__':
    cli()
