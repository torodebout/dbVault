"""
Storage factory for creating storage handlers
"""

from typing import Dict, Any, Union
from ..storage.local import LocalStorage
from ..storage.aws_s3 import AWSS3Storage
from ..utils.logging import get_logger

logger = get_logger(__name__)


class StorageFactory:
    """Factory for creating storage handler instances."""
    
    _storage_handlers = {
        'local': LocalStorage,
        's3': AWSS3Storage,
        'aws': AWSS3Storage,
    }
    
    @classmethod
    def create_handler(cls, storage_type: str, config: Dict[str, Any]) -> Union[LocalStorage, AWSS3Storage]:
        """Create a storage handler instance.
        
        Args:
            storage_type: Type of storage ('local', 's3', 'aws')
            config: Storage configuration dictionary
            
        Returns:
            Storage handler instance
            
        Raises:
            ValueError: If storage type is not supported
        """
        storage_type = storage_type.lower()
        if storage_type == 'aws':
            storage_type = 's3'
        
        if storage_type not in cls._storage_handlers:
            available_types = list(cls._storage_handlers.keys())
            raise ValueError(f"Unsupported storage type: {storage_type}. Available: {available_types}")
        
        handler_class = cls._storage_handlers[storage_type]
        
        if storage_type == 'local':
            handler_config = config.get('local', config)
        elif storage_type == 's3':
            handler_config = config.get('aws', config)
        else:
            handler_config = config
        
        logger.info(f"Creating {storage_type} storage handler")
        return handler_class(handler_config)
    
    @classmethod
    def get_available_types(cls) -> list:
        """Get list of available storage types.
        
        Returns:
            List of supported storage type names
        """
        return list(cls._storage_handlers.keys())
    
    @classmethod
    def register_handler(cls, storage_type: str, handler_class):
        """Register a new storage handler class.
        
        Args:
            storage_type: Name of the storage type
            handler_class: Storage handler class
        """
        cls._storage_handlers[storage_type] = handler_class
        logger.info(f"Registered storage handler: {storage_type}")


