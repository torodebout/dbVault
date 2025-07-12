"""
Input validation utilities
"""

import re
from pathlib import Path
from typing import Optional, Union


def validate_database_name(name: str) -> bool:
    """Validate database name format.
    
    Args:
        name: Database name to validate
        
    Returns:
        True if name is valid, False otherwise
    """
    if not name or not isinstance(name, str):
        return False
    
    pattern = r'^[a-zA-Z0-9_-]+$'
    return bool(re.match(pattern, name)) and len(name) <= 63


def validate_hostname(hostname: str) -> bool:
    """Validate hostname or IP address format.
    
    Args:
        hostname: Hostname or IP to validate
        
    Returns:
        True if hostname is valid, False otherwise
    """
    if not hostname or not isinstance(hostname, str):
        return False
    
    if hostname == 'localhost':
        return True
    
    hostname_pattern = r'^[a-zA-Z0-9.-]+$'
    if not re.match(hostname_pattern, hostname):
        return False
    
    if len(hostname) > 253:
        return False
    
    return True


def validate_port(port: Union[int, str]) -> bool:
    """Validate port number.
    
    Args:
        port: Port number to validate
        
    Returns:
        True if port is valid, False otherwise
    """
    try:
        port_num = int(port)
        return 1 <= port_num <= 65535
    except (ValueError, TypeError):
        return False


def validate_file_path(path: str, must_exist: bool = False) -> bool:
    """Validate file path format and optionally existence.
    
    Args:
        path: File path to validate
        must_exist: Whether the file must exist
        
    Returns:
        True if path is valid, False otherwise
    """
    if not path or not isinstance(path, str):
        return False
    
    try:
        path_obj = Path(path).expanduser()
        
        if must_exist:
            return path_obj.exists()
        else:
            return True
    except (OSError, ValueError):
        return False


def validate_s3_bucket_name(bucket_name: str) -> bool:
    """Validate AWS S3 bucket name format.
    
    Args:
        bucket_name: S3 bucket name to validate
        
    Returns:
        True if bucket name is valid, False otherwise
    """
    if not bucket_name or not isinstance(bucket_name, str):
        return False
    
    if len(bucket_name) < 3 or len(bucket_name) > 63:
        return False
    
    if not (bucket_name[0].isalnum() and bucket_name[-1].isalnum()):
        return False
    
    pattern = r'^[a-z0-9.-]+$'
    if not re.match(pattern, bucket_name):
        return False
    
    if '..' in bucket_name or '--' in bucket_name:
        return False
    
    ip_pattern = r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$'
    if re.match(ip_pattern, bucket_name):
        return False
    
    return True


def validate_backup_name(name: str) -> bool:
    """Validate backup file name format.
    
    Args:
        name: Backup file name to validate
        
    Returns:
        True if name is valid, False otherwise
    """
    if not name or not isinstance(name, str):
        return False
    
    if len(name) > 255:
        return False
    
    pattern = r'^[a-zA-Z0-9._-]+$'
    return bool(re.match(pattern, name))


def validate_database_config(config: dict) -> list:
    """Validate complete database configuration.
    
    Args:
        config: Database configuration dictionary
        
    Returns:
        List of validation error messages (empty if valid)
    """
    errors = []
    
    required_fields = ['type', 'host', 'username', 'database']
    for field in required_fields:
        if field not in config:
            errors.append(f"Missing required field: {field}")
    
    if 'type' in config:
        valid_types = ['postgresql', 'postgres', 'mongodb', 'mongo']
        if config['type'] not in valid_types:
            errors.append(f"Invalid database type: {config['type']}")
    
    if 'host' in config and not validate_hostname(config['host']):
        errors.append(f"Invalid hostname: {config['host']}")
    
    if 'port' in config and not validate_port(config['port']):
        errors.append(f"Invalid port: {config['port']}")
    
    if 'database' in config and not validate_database_name(config['database']):
        errors.append(f"Invalid database name: {config['database']}")
    
    if 'username' in config and not config['username']:
        errors.append("Username cannot be empty")
    
    return errors


def validate_storage_config(config: dict) -> list:
    """Validate storage configuration.
    
    Args:
        config: Storage configuration dictionary
        
    Returns:
        List of validation error messages (empty if valid)
    """
    errors = []
    
    if 'local' not in config and 'aws' not in config:
        errors.append("At least one storage type (local or aws) must be configured")
    
    if 'local' in config:
        local_config = config['local']
        if 'path' not in local_config:
            errors.append("Local storage missing required field: path")
        elif not validate_file_path(local_config['path']):
            errors.append(f"Invalid local storage path: {local_config['path']}")
    
    if 'aws' in config:
        aws_config = config['aws']
        required_aws_fields = ['bucket', 'region']
        for field in required_aws_fields:
            if field not in aws_config:
                errors.append(f"AWS storage missing required field: {field}")
        
        if 'bucket' in aws_config and not validate_s3_bucket_name(aws_config['bucket']):
            errors.append(f"Invalid S3 bucket name: {aws_config['bucket']}")
    
    return errors


def sanitize_filename(filename: str) -> str:
    """Sanitize a filename by removing problematic characters.
    
    Args:
        filename: Original filename
        
    Returns:
        Sanitized filename safe for filesystem use
    """
    if not filename:
        return "unnamed_backup"
    
    sanitized = re.sub(r'[<>:"/\\|?*]', '_', filename)
    
    sanitized = re.sub(r'[\x00-\x1f\x7f]', '', sanitized)
    
    if len(sanitized) > 200:
        sanitized = sanitized[:200]
    
    if not sanitized.strip():
        return "unnamed_backup"
    
    return sanitized.strip()


def validate_environment_variables(required_vars: list) -> list:
    """Validate that required environment variables are set.
    
    Args:
        required_vars: List of required environment variable names
        
    Returns:
        List of missing environment variables
    """
    import os
    missing_vars = []
    
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    return missing_vars
