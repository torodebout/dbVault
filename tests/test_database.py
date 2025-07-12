"""
Tests for database handlers
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent / 'src'))

from src.database.postgresql import PostgreSQLHandler
from src.database.mongodb import MongoDBHandler
from src.database.factory import DatabaseFactory


class TestDatabaseHandlers:
    """Test suite for database handlers."""
    
    def test_postgresql_handler_creation(self):
        """Test PostgreSQL handler creation."""
        config = {
            'type': 'postgresql',
            'host': 'localhost',
            'port': 5432,
            'username': 'testuser',
            'password': 'testpass',
            'database': 'testdb'
        }
        
        handler = PostgreSQLHandler(config)
        assert handler.host == 'localhost'
        assert handler.port == 5432
        assert handler.username == 'testuser'
        assert handler.database == 'testdb'
    
    def test_mongodb_handler_creation(self):
        """Test MongoDB handler creation."""
        config = {
            'type': 'mongodb',
            'host': 'localhost',
            'port': 27017,
            'username': '',
            'password': '',
            'database': 'testdb'
        }
        
        handler = MongoDBHandler(config)
        assert handler.host == 'localhost'
        assert handler.port == 27017
        assert handler.database == 'testdb'
    
    def test_database_factory_postgresql(self):
        """Test database factory for PostgreSQL."""
        config = {
            'type': 'postgresql',
            'host': 'localhost',
            'port': 5432,
            'username': 'testuser',
            'password': 'testpass',
            'database': 'testdb'
        }
        
        handler = DatabaseFactory.create_handler(config)
        assert isinstance(handler, PostgreSQLHandler)
    
    def test_database_factory_mongodb(self):
        """Test database factory for MongoDB."""
        config = {
            'type': 'mongodb',
            'host': 'localhost',
            'port': 27017,
            'username': '',
            'password': '',
            'database': 'testdb'
        }
        
        handler = DatabaseFactory.create_handler(config)
        assert isinstance(handler, MongoDBHandler)
    
    def test_database_factory_invalid_type(self):
        """Test database factory with invalid type."""
        config = {
            'type': 'invalid_db_type',
            'host': 'localhost'
        }
        
        with pytest.raises(ValueError, match="Unsupported database type"):
            DatabaseFactory.create_handler(config)
    
    @patch('psycopg2.connect')
    def test_postgresql_connection_test_success(self, mock_connect):
        """Test PostgreSQL connection test success."""
        mock_conn = Mock()
        mock_connect.return_value = mock_conn
        
        config = {
            'type': 'postgresql',
            'host': 'localhost',
            'port': 5432,
            'username': 'testuser',
            'password': 'testpass',
            'database': 'testdb'
        }
        
        handler = PostgreSQLHandler(config)
        result = handler.test_connection()
        
        assert result is True
        mock_connect.assert_called_once()
        mock_conn.close.assert_called_once()
    
    @patch('psycopg2.connect')
    def test_postgresql_connection_test_failure(self, mock_connect):
        """Test PostgreSQL connection test failure."""
        mock_connect.side_effect = Exception("Connection failed")
        
        config = {
            'type': 'postgresql',
            'host': 'localhost',
            'port': 5432,
            'username': 'testuser',
            'password': 'testpass',
            'database': 'testdb'
        }
        
        handler = PostgreSQLHandler(config)
        result = handler.test_connection()
        
        assert result is False
    
    @patch('pymongo.MongoClient')
    def test_mongodb_connection_test_success(self, mock_client):
        """Test MongoDB connection test success."""
        mock_client_instance = Mock()
        mock_client.return_value = mock_client_instance
        mock_client_instance.admin.command.return_value = {'ok': 1}
        
        config = {
            'type': 'mongodb',
            'host': 'localhost',
            'port': 27017,
            'username': '',
            'password': '',
            'database': 'testdb'
        }
        
        handler = MongoDBHandler(config)
        result = handler.test_connection()
        
        assert result is True
        mock_client.assert_called_once()
    
    @patch('pymongo.MongoClient')
    def test_mongodb_connection_test_failure(self, mock_client):
        """Test MongoDB connection test failure."""
        mock_client.side_effect = Exception("Connection failed")
        
        config = {
            'type': 'mongodb',
            'host': 'localhost',
            'port': 27017,
            'username': '',
            'password': '',
            'database': 'testdb'
        }
        
        handler = MongoDBHandler(config)
        result = handler.test_connection()
        
        assert result is False
