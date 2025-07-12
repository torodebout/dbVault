"""
Database factory for creating database handlers
"""

from typing import Dict, Any

from .base import DatabaseHandler
from .postgresql import PostgreSQLHandler
from .mongodb import MongoDBHandler
from ..utils.logging import get_logger

logger = get_logger(__name__)


class DatabaseFactory:
    """Factory class for creating database handlers."""
    
    _handlers = {
        'postgresql': PostgreSQLHandler,
        'postgres': PostgreSQLHandler,
        'mongodb': MongoDBHandler,
        'mongo': MongoDBHandler,
    }
    
    @classmethod
    def create_handler(cls, config: Dict[str, Any]) -> DatabaseHandler:
        """Create a database handler based on the configuration.
        
        Args:
            config: Database configuration dictionary
            
        Returns:
            Database handler instance
            
        Raises:
            ValueError: If database type is not supported
        """
        if 'type' not in config:
            raise ValueError("Database type not specified in configuration")
        
        db_type = config['type'].lower()
        
        if db_type not in cls._handlers:
            supported_types = list(cls._handlers.keys())
            raise ValueError(f"Unsupported database type: {db_type}. "
                           f"Supported types: {', '.join(supported_types)}")
        
        handler_class = cls._handlers[db_type]
        logger.info(f"Creating {handler_class.__name__} for database: {config.get('database', 'unknown')}")
        
        return handler_class(config)
    
    @classmethod
    def get_supported_types(cls) -> list:
        """Get list of supported database types.
        
        Returns:
            List of supported database type strings
        """
        return list(cls._handlers.keys())
    
    @classmethod
    def register_handler(cls, db_type: str, handler_class: type) -> None:
        """Register a new database handler.
        
        Args:
            db_type: Database type identifier
            handler_class: Handler class that inherits from DatabaseHandler
        """
        if not issubclass(handler_class, DatabaseHandler):
            raise ValueError("Handler class must inherit from DatabaseHandler")
        
        cls._handlers[db_type.lower()] = handler_class
        logger.info(f"Registered new database handler: {db_type} -> {handler_class.__name__}")
