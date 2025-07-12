"""
AWS S3 storage handler
"""

import os
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional

import boto3
from botocore.exceptions import ClientError, NoCredentialsError

from ..utils.logging import get_logger

logger = get_logger(__name__)


class AWSS3Storage:
    """Handler for AWS S3 storage."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize AWS S3 storage handler.
        
        Args:
            config: Storage configuration dictionary
        """
        self.config = config
        self.bucket_name = config['bucket']
        self.region = config.get('region', 'us-west-2')
        
        self.s3_client = self._create_s3_client(config)
        
        self._verify_bucket_access()
        
        logger.info(f"AWS S3 storage initialized: s3://{self.bucket_name}")
    
    def _create_s3_client(self, config: Dict[str, Any]):
        """Create S3 client with credentials.
        
        Args:
            config: Storage configuration dictionary
            
        Returns:
            Boto3 S3 client
            
        Raises:
            NoCredentialsError: If AWS credentials are not found
        """
        try:
            aws_access_key = config.get('access_key')
            aws_secret_key = config.get('secret_key')
            
            if aws_access_key and aws_secret_key:
                return boto3.client(
                    's3',
                    region_name=self.region,
                    aws_access_key_id=aws_access_key,
                    aws_secret_access_key=aws_secret_key
                )
            else:
                return boto3.client('s3', region_name=self.region)
                
        except NoCredentialsError:
            logger.error("AWS credentials not found. Please configure AWS credentials.")
            raise
        except Exception as e:
            logger.error(f"Failed to create S3 client: {e}")
            raise
    
    def _verify_bucket_access(self) -> None:
        """Verify that the S3 bucket is accessible.
        
        Raises:
            ClientError: If bucket is not accessible
        """
        try:
            self.s3_client.head_bucket(Bucket=self.bucket_name)
            logger.info(f"S3 bucket access verified: {self.bucket_name}")
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == '404':
                logger.error(f"S3 bucket not found: {self.bucket_name}")
            elif error_code == '403':
                logger.error(f"Access denied to S3 bucket: {self.bucket_name}")
            else:
                logger.error(f"S3 bucket access error: {e}")
            raise
    
    def store_backup(self, source_file: str, backup_name: str) -> str:
        """Store a backup file in S3.
        
        Args:
            source_file: Path to the source backup file
            backup_name: Name for the stored backup file (S3 key)
            
        Returns:
            S3 URI of the stored backup file
            
        Raises:
            FileNotFoundError: If source file doesn't exist
            ClientError: If S3 operation fails
        """
        source_path = Path(source_file)
        if not source_path.exists():
            raise FileNotFoundError(f"Source backup file not found: {source_file}")
        
        s3_key = f"dbvault/backups/{backup_name}"
        
        try:
            file_size = source_path.stat().st_size
            size_mb = file_size / (1024 * 1024)
            
            logger.info(f"Uploading backup to S3: {backup_name} ({size_mb:.2f} MB)")
            
            extra_args = {
                'Metadata': {
                    'uploaded-by': 'dbvault',
                    'upload-timestamp': datetime.utcnow().isoformat(),
                    'original-filename': source_path.name
                }
            }
            
            self.s3_client.upload_file(
                str(source_path),
                self.bucket_name,
                s3_key,
                ExtraArgs=extra_args
            )
            
            s3_uri = f"s3://{self.bucket_name}/{s3_key}"
            logger.info(f"Backup uploaded to S3: {s3_uri}")
            return s3_uri
            
        except ClientError as e:
            logger.error(f"Failed to upload backup to S3: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error uploading to S3: {e}")
            raise
    
    def download_backup(self, backup_name: str, destination_file: str) -> str:
        """Download a backup file from S3.
        
        Args:
            backup_name: Name of the backup file to download (S3 key basename)
            destination_file: Path where to save the downloaded file
            
        Returns:
            Path to the downloaded backup file
            
        Raises:
            ClientError: If S3 operation fails
        """
        return self.retrieve_backup(backup_name, destination_file)
    
    def retrieve_backup(self, backup_name: str, destination_file: str) -> str:
        """Retrieve a backup file from S3.
        
        Args:
            backup_name: Name of the backup file to retrieve (S3 key basename)
            destination_file: Path where to save the retrieved file
            
        Returns:
            Path to the retrieved backup file
            
        Raises:
            ClientError: If S3 operation fails
        """
        s3_key = f"dbvault/backups/{backup_name}"
        destination_path = Path(destination_file)
        destination_path.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            self.s3_client.head_object(Bucket=self.bucket_name, Key=s3_key)
            
            self.s3_client.download_file(
                self.bucket_name,
                s3_key,
                str(destination_path)
            )
            
            logger.info(f"Backup downloaded from S3: {destination_path}")
            return str(destination_path)
            
        except ClientError as e:
            if e.response['Error']['Code'] == '404':
                raise FileNotFoundError(f"Backup not found in S3: {backup_name}")
            else:
                logger.error(f"Failed to download backup from S3: {e}")
                raise
        except Exception as e:
            logger.error(f"Unexpected error downloading from S3: {e}")
            raise
    
    def list_backups(self) -> List[Dict[str, Any]]:
        """List all backup files in S3.
        
        Returns:
            List of dictionaries containing backup file information
        """
        backups = []
        prefix = "dbvault/backups/"
        
        try:
            paginator = self.s3_client.get_paginator('list_objects_v2')
            page_iterator = paginator.paginate(
                Bucket=self.bucket_name,
                Prefix=prefix
            )
            
            for page in page_iterator:
                if 'Contents' in page:
                    for obj in page['Contents']:
                        if obj['Key'] == prefix:
                            continue
                        
                        backup_name = obj['Key'][len(prefix):]
                        
                        backup_info = {
                            'name': backup_name,
                            'key': obj['Key'],
                            'size': self._format_size(obj['Size']),
                            'size_bytes': obj['Size'],
                            'modified': obj['LastModified'].strftime('%Y-%m-%d %H:%M:%S'),
                            'modified_timestamp': obj['LastModified'].timestamp(),
                            's3_uri': f"s3://{self.bucket_name}/{obj['Key']}"
                        }
                        backups.append(backup_info)
            
            backups.sort(key=lambda x: x['modified_timestamp'], reverse=True)
            
            logger.info(f"Found {len(backups)} backup files in S3")
            return backups
            
        except ClientError as e:
            logger.error(f"Failed to list S3 backups: {e}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error listing S3 backups: {e}")
            return []
    
    def delete_backup(self, backup_name: str) -> bool:
        """Delete a backup file from S3.
        
        Args:
            backup_name: Name of the backup file to delete
            
        Returns:
            True if deletion was successful, False otherwise
        """
        s3_key = f"dbvault/backups/{backup_name}"
        
        try:
            self.s3_client.delete_object(Bucket=self.bucket_name, Key=s3_key)
            logger.info(f"Deleted backup from S3: {backup_name}")
            return True
            
        except ClientError as e:
            logger.error(f"Failed to delete backup from S3: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error deleting from S3: {e}")
            return False
    
    def backup_exists(self, backup_name: str) -> bool:
        """Check if a backup file exists in S3.
        
        Args:
            backup_name: Name of the backup file
            
        Returns:
            True if backup exists, False otherwise
        """
        s3_key = f"dbvault/backups/{backup_name}"
        
        try:
            self.s3_client.head_object(Bucket=self.bucket_name, Key=s3_key)
            return True
        except ClientError as e:
            if e.response['Error']['Code'] == '404':
                return False
            else:
                logger.error(f"Error checking backup existence in S3: {e}")
                return False
    
    def get_backup_url(self, backup_name: str, expiration: int = 3600) -> Optional[str]:
        """Generate a presigned URL for a backup file.
        
        Args:
            backup_name: Name of the backup file
            expiration: URL expiration time in seconds (default: 1 hour)
            
        Returns:
            Presigned URL string, or None if generation fails
        """
        s3_key = f"dbvault/backups/{backup_name}"
        
        try:
            url = self.s3_client.generate_presigned_url(
                'get_object',
                Params={'Bucket': self.bucket_name, 'Key': s3_key},
                ExpiresIn=expiration
            )
            logger.info(f"Generated presigned URL for backup: {backup_name}")
            return url
            
        except ClientError as e:
            logger.error(f"Failed to generate presigned URL: {e}")
            return None
    
    def _format_size(self, size_bytes: int) -> str:
        """Format file size in human-readable format.
        
        Args:
            size_bytes: Size in bytes
            
        Returns:
            Formatted size string
        """
        if size_bytes == 0:
            return "0 B"
        
        units = ['B', 'KB', 'MB', 'GB', 'TB']
        unit_index = 0
        size = float(size_bytes)
        
        while size >= 1024 and unit_index < len(units) - 1:
            size /= 1024
            unit_index += 1
        
        if unit_index == 0:
            return f"{int(size)} {units[unit_index]}"
        else:
            return f"{size:.1f} {units[unit_index]}"
    
    def get_storage_info(self) -> Dict[str, Any]:
        """Get storage information and statistics.
        
        Returns:
            Dictionary with storage information
        """
        backups = self.list_backups()
        total_backup_size = sum(backup['size_bytes'] for backup in backups)
        
        return {
            'type': 's3',
            'bucket': self.bucket_name,
            'region': self.region,
            'backup_count': len(backups),
            'total_backup_size': self._format_size(total_backup_size),
            'total_backup_size_bytes': total_backup_size
        }
    
    def __str__(self) -> str:
        """String representation of S3 storage."""
        return f"AWSS3Storage(s3://{self.bucket_name})"
