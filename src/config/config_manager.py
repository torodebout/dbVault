"""
Configuration manager for dbVault
"""

import os
from pathlib import Path
from typing import Dict, Any

import yaml
from dotenv import load_dotenv

from ..utils.logging import get_logger

logger = get_logger(__name__)


class ConfigManager:
    """Manages configuration files and environment variables."""
    
    DEFAULT_CONFIG = {
        'database': {
            'type': 'postgresql',
            'host': 'localhost',
            'port': 5432,
            'username': 'user',
            'password': 'password',
            'database': 'mydb'
        },
        'storage': {
            'local': {
                'path': '~/backups'
            },
            'aws': {
                'bucket': 'my-backup-bucket',
                'region': 'us-west-2',
                'access_key': '${AWS_ACCESS_KEY_ID}',
                'secret_key': '${AWS_SECRET_ACCESS_KEY}'
            }
        },
        'backup': {
            'compression': True,
            'default_storage': 'local'
        }
    }
    
    def __init__(self):
        """Initialize the configuration manager."""
        load_dotenv()
        
    def create_default_config(self, config_path: Path) -> None:
        """Create a default configuration file.
        
        Args:
            config_path: Path where to create the configuration file
        """
        try:
            with open(config_path, 'w') as f:
                yaml.dump(self.DEFAULT_CONFIG, f, default_flow_style=False, indent=2)
            logger.info(f"Created default configuration file: {config_path}")
        except Exception as e:
            logger.error(f"Failed to create configuration file: {e}")
            raise
    
    def load_config(self, config_path: str) -> Dict[str, Any]:
        """Load configuration from file and resolve environment variables.
        
        Args:
            config_path: Path to the configuration file
            
        Returns:
            Dictionary containing the configuration
            
        Raises:
            FileNotFoundError: If configuration file doesn't exist
            yaml.YAMLError: If configuration file is invalid
        """
        config_file = Path(config_path)
        
        if not config_file.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_path}")
        
        try:
            with open(config_file, 'r') as f:
                config = yaml.safe_load(f)
            
            config = self._resolve_env_vars(config)
            
            self._validate_config(config)
            
            logger.info(f"Loaded configuration from: {config_path}")
            return config
            
        except yaml.YAMLError as e:
            logger.error(f"Invalid YAML in configuration file: {e}")
            raise
        except Exception as e:
            logger.error(f"Failed to load configuration: {e}")
            raise
    
    def _resolve_env_vars(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Recursively resolve environment variables in configuration.
        
        Args:
            config: Configuration dictionary
            
        Returns:
            Configuration with environment variables resolved
        """
        if isinstance(config, dict):
            return {k: self._resolve_env_vars(v) for k, v in config.items()}
        elif isinstance(config, list):
            return [self._resolve_env_vars(item) for item in config]
        elif isinstance(config, str) and config.startswith('${') and config.endswith('}'):
            env_expression = config[2:-1]
            
            if ':-' in env_expression:
                env_var, default_value = env_expression.split(':-', 1)
                value = os.getenv(env_var)
                if value is None:
                    logger.debug(f"Environment variable {env_var} not found, using default: {default_value}")
                    return default_value
                return value
            else:
                env_var = env_expression
                value = os.getenv(env_var)
                if value is None:
                    logger.warning(f"Environment variable {env_var} not found, using original value")
                    return config
                return value
        else:
            return config
    
    def _validate_config(self, config: Dict[str, Any]) -> None:
        """Validate configuration structure and required fields.
        
        Args:
            config: Configuration dictionary to validate
            
        Raises:
            ValueError: If configuration is invalid
        """
        required_sections = ['database', 'storage']
        for section in required_sections:
            if section not in config:
                raise ValueError(f"Missing required configuration section: {section}")
        
        db_config = config['database']
        required_db_fields = ['type', 'host', 'username', 'database']
        for field in required_db_fields:
            if field not in db_config:
                raise ValueError(f"Missing required database field: {field}")
        
        supported_db_types = ['postgresql', 'mongodb']
        if db_config['type'] not in supported_db_types:
            raise ValueError(f"Unsupported database type: {db_config['type']}. "
                           f"Supported types: {', '.join(supported_db_types)}")
        
        if 'port' not in db_config:
            if db_config['type'] == 'postgresql':
                db_config['port'] = 5432
            elif db_config['type'] == 'mongodb':
                db_config['port'] = 27017
        
        storage_config = config['storage']
        if 'local' not in storage_config and 'aws' not in storage_config:
            raise ValueError("At least one storage backend (local or aws) must be configured")
        
        if 'aws' in storage_config:
            aws_config = storage_config['aws']
            required_aws_fields = ['bucket', 'region']
            for field in required_aws_fields:
                if field not in aws_config:
                    raise ValueError(f"Missing required AWS storage field: {field}")
        
        if 'local' in storage_config:
            local_config = storage_config['local']
            if 'path' not in local_config:
                raise ValueError("Missing required local storage field: path")
        
        logger.info("Configuration validation passed")
    
    def get_database_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Get database configuration section.
        
        Args:
            config: Full configuration dictionary
            
        Returns:
            Database configuration section
        """
        return config['database']
    
    def get_storage_config(self, config: Dict[str, Any], storage_type: str) -> Dict[str, Any]:
        """Get storage configuration for specified type.
        
        Args:
            config: Full configuration dictionary
            storage_type: Type of storage ('local' or 'aws')
            
        Returns:
            Storage configuration section
            
        Raises:
            ValueError: If storage type is not configured
        """
        storage_config = config['storage']
        if storage_type not in storage_config:
            raise ValueError(f"Storage type '{storage_type}' not configured")
        
        return storage_config[storage_type]
