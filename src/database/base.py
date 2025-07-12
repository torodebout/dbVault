"""
Abstract base class for database handlers
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional


class DatabaseHandler(ABC):
    """Abstract base class for database handlers."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize the database handler.
        
        Args:
            config: Database configuration dictionary
        """
        self.config = config
        self.host = config['host']
        self.port = config['port']
        self.username = config['username']
        self.password = config.get('password', '')
        self.database = config['database']
    
    @abstractmethod
    def test_connection(self) -> bool:
        """Test the database connection.
        
        Returns:
            True if connection is successful, False otherwise
        """
        pass
    
    @abstractmethod
    def create_backup(self, output_file: str) -> bool:
        """Create a backup of the database.
        
        Args:
            output_file: Path where the backup file should be created
            
        Returns:
            True if backup was successful, False otherwise
        """
        pass
    
    @abstractmethod
    def restore_backup(self, backup_file: str) -> bool:
        """Restore the database from a backup file.
        
        Args:
            backup_file: Path to the backup file
            
        Returns:
            True if restore was successful, False otherwise
        """
        pass
    
    @abstractmethod
    def get_database_size(self) -> Optional[int]:
        """Get the size of the database in bytes.
        
        Returns:
            Database size in bytes, or None if unable to determine
        """
        pass
    
    def get_connection_string(self, mask_password: bool = True) -> str:
        """Get a string representation of the database connection.
        
        Args:
            mask_password: Whether to mask the password in the string
            
        Returns:
            Connection string
        """
        password = "***" if mask_password and self.password else self.password
        return f"{self.get_database_type()}://{self.username}:{password}@{self.host}:{self.port}/{self.database}"
    
    @abstractmethod
    def get_database_type(self) -> str:
        """Get the database type identifier.
        
        Returns:
            Database type string (e.g., 'postgresql', 'mongodb')
        """
        pass
    
    def validate_config(self) -> None:
        """Validate the database configuration.
        
        Raises:
            ValueError: If configuration is invalid
        """
        required_fields = ['host', 'port', 'username', 'database']
        for field in required_fields:
            if field not in self.config:
                raise ValueError(f"Missing required database configuration field: {field}")
        
        if not isinstance(self.port, int) or self.port <= 0:
            raise ValueError("Database port must be a positive integer")
    
    def __str__(self) -> str:
        """String representation of the database handler."""
        return f"{self.__class__.__name__}({self.get_connection_string()})"
    
    def __repr__(self) -> str:
        """Representation of the database handler."""
        return self.__str__()
