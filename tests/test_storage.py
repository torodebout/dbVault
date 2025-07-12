"""
Tests for storage handlers
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent / 'src'))

from src.storage.local import LocalStorage
from src.storage.aws_s3 import AWSS3Storage
from src.storage.factory import StorageFactory


class TestStorageHandlers:
    """Test suite for storage handlers."""
    
    def test_local_storage_creation(self, temp_dir):
        """Test local storage handler creation."""
        config = {'path': str(temp_dir)}
        
        handler = LocalStorage(config)
        assert handler.base_path == temp_dir
    
    def test_local_storage_factory(self, temp_dir):
        """Test local storage via factory."""
        config = {'local': {'path': str(temp_dir)}}
        
        handler = StorageFactory.create_handler('local', config)
        assert isinstance(handler, LocalStorage)
    
    @patch('boto3.client')
    def test_s3_storage_creation(self, mock_boto3):
        """Test S3 storage handler creation."""
        config = {
            'bucket': 'test-bucket',
            'region': 'us-west-2',
            'access_key': 'test-key',
            'secret_key': 'test-secret'
        }
        
        mock_s3_client = Mock()
        mock_boto3.return_value = mock_s3_client
        mock_s3_client.head_bucket.return_value = None
        
        handler = AWSS3Storage(config)
        assert handler.bucket_name == 'test-bucket'
        assert handler.region == 'us-west-2'
    
    @patch('boto3.client')
    def test_s3_storage_factory(self, mock_boto3):
        """Test S3 storage via factory."""
        config = {
            'aws': {
                'bucket': 'test-bucket',
                'region': 'us-west-2',
                'access_key': 'test-key',
                'secret_key': 'test-secret'
            }
        }
        
        mock_s3_client = Mock()
        mock_boto3.return_value = mock_s3_client
        mock_s3_client.head_bucket.return_value = None
        
        handler = StorageFactory.create_handler('s3', config)
        assert isinstance(handler, AWSS3Storage)
    
    def test_storage_factory_invalid_type(self):
        """Test storage factory with invalid type."""
        config = {'invalid': {'setting': 'value'}}
        
        with pytest.raises(ValueError, match="Unsupported storage type"):
            StorageFactory.create_handler('invalid_storage', config)
    
    def test_local_storage_store_backup(self, temp_dir):
        """Test local storage backup store."""
        config = {'path': str(temp_dir)}
        handler = LocalStorage(config)
        
        test_file = temp_dir / 'test_backup.sql'
        test_file.write_text('test backup content')
        
        result = handler.store_backup(str(test_file), 'stored_backup.sql')
        
        stored_file = temp_dir / 'stored_backup.sql'
        assert stored_file.exists()
        assert result == str(stored_file)
    
    def test_local_storage_list_backups(self, temp_dir):
        """Test local storage backup listing."""
        config = {'path': str(temp_dir)}
        handler = LocalStorage(config)
        
        (temp_dir / 'backup1.gz').write_text('backup1')
        (temp_dir / 'backup2.gz').write_text('backup2')
        (temp_dir / 'not_backup.txt').write_text('not a backup')
        
        backups = handler.list_backups()
        
        backup_names = [backup['name'] for backup in backups]
        assert 'backup1.gz' in backup_names
        assert 'backup2.gz' in backup_names
        assert 'not_backup.txt' not in backup_names
    
    @patch('boto3.client')
    def test_s3_storage_list_backups(self, mock_boto3):
        """Test S3 storage backup listing."""
        config = {
            'bucket': 'test-bucket',
            'region': 'us-west-2',
            'access_key': 'test-key',
            'secret_key': 'test-secret'
        }
        
        mock_s3_client = Mock()
        mock_boto3.return_value = mock_s3_client
        mock_s3_client.head_bucket.return_value = None
        
        mock_paginator = Mock()
        mock_s3_client.get_paginator.return_value = mock_paginator
        mock_paginator.paginate.return_value = [
            {
                'Contents': [
                    {
                        'Key': 'dbvault/backups/backup1.gz',
                        'Size': 1024,
                        'LastModified': Mock()
                    }
                ]
            }
        ]
        
        from datetime import datetime
        mock_paginator.paginate.return_value[0]['Contents'][0]['LastModified'].strftime.return_value = '2025-07-07 12:00:00'
        mock_paginator.paginate.return_value[0]['Contents'][0]['LastModified'].timestamp.return_value = 1720353600
        
        handler = AWSS3Storage(config)
        backups = handler.list_backups()
        
        assert len(backups) == 1
        assert backups[0]['name'] == 'backup1.gz'
        assert backups[0]['size_bytes'] == 1024
