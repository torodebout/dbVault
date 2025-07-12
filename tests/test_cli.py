"""
Tests for CLI commands
"""
import pytest
import tempfile
import os
from pathlib import Path
from click.testing import CliRunner
from unittest.mock import Mock, patch, MagicMock
import yaml

import sys
sys.path.append(str(Path(__file__).parent.parent / 'src'))

from src.main import cli


class TestCLICommands:
    """Test suite for CLI commands."""
    
    def setup_method(self):
        """Setup for each test method."""
        self.runner = CliRunner()
    
    def test_cli_help(self):
        """Test CLI help command."""
        result = self.runner.invoke(cli, ['--help'])
        assert result.exit_code == 0
        assert 'dbVault - Database Backup' in result.output
        assert 'backup' in result.output
        assert 'restore' in result.output
        assert 'test' in result.output
        assert 'init' in result.output
        assert 'list-backups' in result.output
    
    def test_init_command(self, temp_dir):
        """Test init command."""
        config_file = temp_dir / 'test_config.yaml'
        
        with self.runner.isolated_filesystem():
            result = self.runner.invoke(cli, ['init', '--output', str(config_file)])
            assert result.exit_code == 0
            assert config_file.exists()
            
            with open(config_file) as f:
                config = yaml.safe_load(f)
            assert 'database' in config
            assert 'storage' in config
            assert 'backup' in config
    
    def test_init_command_existing_file(self, temp_dir):
        """Test init command with existing file."""
        config_file = temp_dir / 'existing_config.yaml'
        config_file.write_text("existing: content")
        
        with self.runner.isolated_filesystem():
            result = self.runner.invoke(cli, ['init', '--output', str(config_file)], input='n\n')
            assert result.exit_code == 0
            assert 'cancelled' in result.output.lower()
    
    @patch('src.database.factory.DatabaseFactory.create_handler')
    def test_test_command_database_only(self, mock_db_factory, config_file):
        """Test test command for database only."""
        mock_db_handler = Mock()
        mock_db_handler.test_connection.return_value = True
        mock_db_factory.return_value = mock_db_handler
        
        result = self.runner.invoke(cli, ['test', '--config', config_file, '--type', 'database'])
        assert result.exit_code == 0
        assert '✅ Database connection successful!' in result.output
        mock_db_handler.test_connection.assert_called_once()
    
    @patch('src.storage.factory.StorageFactory.create_handler')
    def test_test_command_storage_local(self, mock_storage_factory, config_file):
        """Test test command for local storage."""
        mock_storage_handler = Mock()
        mock_storage_handler.base_path = Path('/test/path')
        mock_storage_handler.list_backups.return_value = []
        mock_storage_factory.return_value = mock_storage_handler
        
        with patch('pathlib.Path.mkdir'):
            result = self.runner.invoke(cli, ['test', '--config', config_file, '--type', 'storage', '--storage', 'local'])
            assert result.exit_code == 0
            assert '✅ Local storage accessible!' in result.output
    
    @patch('src.storage.factory.StorageFactory.create_handler')
    def test_test_command_storage_s3(self, mock_storage_factory, config_file):
        """Test test command for S3 storage."""
        mock_s3_handler = Mock()
        mock_s3_handler.list_backups.return_value = [
            {'name': 'test_backup.gz', 'size': '1.2 KB'}
        ]
        mock_storage_factory.return_value = mock_s3_handler
        
        result = self.runner.invoke(cli, ['test', '--config', config_file, '--type', 'storage', '--storage', 's3'])
        assert result.exit_code == 0
        assert '✅ S3 connection successful!' in result.output
    
    @patch('src.backup.backup_manager.BackupManager')
    @patch('src.storage.factory.StorageFactory.create_handler')
    @patch('src.database.factory.DatabaseFactory.create_handler')
    def test_backup_command(self, mock_db_factory, mock_storage_factory, mock_backup_manager, config_file):
        """Test backup command."""
        mock_db_handler = Mock()
        mock_storage_handler = Mock()
        mock_backup_instance = Mock()
        
        mock_db_factory.return_value = mock_db_handler
        mock_storage_factory.return_value = mock_storage_handler
        mock_backup_manager.return_value = mock_backup_instance
        mock_backup_instance.create_backup.return_value = '/path/to/backup.gz'
        
        result = self.runner.invoke(cli, ['backup', '--config', config_file, '--storage', 'local'])
        assert result.exit_code == 0
        assert '✅ Backup completed:' in result.output
        mock_backup_instance.create_backup.assert_called_once()
    
    @patch('src.restore.restore_manager.RestoreManager')
    @patch('src.database.factory.DatabaseFactory.create_handler')
    def test_restore_command_local(self, mock_db_factory, mock_restore_manager, config_file, temp_dir):
        """Test restore command with local backup."""
        mock_db_handler = Mock()
        mock_restore_instance = Mock()
        
        mock_db_factory.return_value = mock_db_handler
        mock_restore_manager.return_value = mock_restore_instance
        
        backup_file = temp_dir / 'test_backup.gz'
        backup_file.write_text('dummy backup content')
        
        result = self.runner.invoke(cli, ['restore', '--backup', str(backup_file), '--config', config_file])
        assert result.exit_code == 0
        assert '✅ Restore completed successfully!' in result.output
        mock_restore_instance.restore_backup.assert_called_once()
    
    @patch('src.storage.factory.StorageFactory.create_handler')
    def test_list_backups_local(self, mock_storage_factory, config_file):
        """Test list-backups command for local storage."""
        mock_storage_handler = Mock()
        mock_storage_handler.list_backups.return_value = [
            {'name': 'backup1.gz', 'size': '1.2 KB', 'modified': '2025-07-07 12:00:00'},
            {'name': 'backup2.gz', 'size': '2.4 KB', 'modified': '2025-07-07 13:00:00'}
        ]
        mock_storage_factory.return_value = mock_storage_handler
        
        result = self.runner.invoke(cli, ['list-backups', '--storage', 'local', '--config', config_file])
        assert result.exit_code == 0
        assert 'backup1.gz' in result.output
        assert 'backup2.gz' in result.output
    
    @patch('src.storage.factory.StorageFactory.create_handler')
    def test_list_backups_s3(self, mock_storage_factory, config_file):
        """Test list-backups command for S3 storage."""
        mock_s3_handler = Mock()
        mock_s3_handler.list_backups.return_value = [
            {'name': 's3_backup.gz', 'size': '5.0 MB', 'modified': '2025-07-07 14:00:00'}
        ]
        mock_storage_factory.return_value = mock_s3_handler
        
        result = self.runner.invoke(cli, ['list-backups', '--storage', 's3', '--config', config_file])
        assert result.exit_code == 0
        assert 's3_backup.gz' in result.output
    
    def test_list_backups_no_config_for_s3(self):
        """Test list-backups command for S3 without config should fail."""
        result = self.runner.invoke(cli, ['list-backups', '--storage', 's3'])
        assert result.exit_code == 1
        assert 'Configuration file required for S3 storage' in result.output
    
    def test_invalid_config_file(self):
        """Test commands with invalid config file."""
        result = self.runner.invoke(cli, ['test', '--config', '/nonexistent/config.yaml'])
        assert result.exit_code == 1
    
    @patch('src.database.factory.DatabaseFactory.create_handler')
    def test_test_command_database_failure(self, mock_db_factory, config_file):
        """Test test command when database connection fails."""
        mock_db_handler = Mock()
        mock_db_handler.test_connection.return_value = False
        mock_db_factory.return_value = mock_db_handler
        
        result = self.runner.invoke(cli, ['test', '--config', config_file, '--type', 'database'])
        assert result.exit_code == 1
        assert '❌ Database connection failed!' in result.output
