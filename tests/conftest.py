"""
Test configuration and fixtures
"""
import pytest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, patch
import yaml

@pytest.fixture
def temp_dir():
    """Create a temporary directory for testing."""
    temp_path = Path(tempfile.mkdtemp())
    yield temp_path
    shutil.rmtree(temp_path)

@pytest.fixture
def sample_config():
    """Sample configuration for testing."""
    return {
        'database': {
            'type': 'postgresql',
            'host': 'localhost',
            'port': 5432,
            'username': 'testuser',
            'password': 'testpass',
            'database': 'testdb'
        },
        'storage': {
            'local': {
                'path': '~/test-backups'
            },
            'aws': {
                'bucket': 'test-bucket',
                'region': 'us-west-2',
                'access_key': 'test-key',
                'secret_key': 'test-secret'
            }
        },
        'backup': {
            'compression': True,
            'default_storage': 'local'
        }
    }

@pytest.fixture
def config_file(temp_dir, sample_config):
    """Create a temporary config file."""
    config_path = temp_dir / 'test_config.yaml'
    with open(config_path, 'w') as f:
        yaml.dump(sample_config, f)
    return str(config_path)

@pytest.fixture
def mongo_config():
    """MongoDB configuration for testing."""
    return {
        'database': {
            'type': 'mongodb',
            'host': 'localhost',
            'port': 27017,
            'username': '',
            'password': '',
            'database': 'testdb'
        },
        'storage': {
            'local': {
                'path': '~/test-backups'
            }
        },
        'backup': {
            'compression': True,
            'default_storage': 'local'
        }
    }
