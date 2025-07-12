"""
Compression utilities for backup files
"""

import gzip
import shutil
from pathlib import Path
from typing import Optional

from .logging import get_logger

logger = get_logger(__name__)


def compress_file(source_file: str, output_file: Optional[str] = None) -> str:
    """Compress a file using gzip compression.
    
    Args:
        source_file: Path to the source file to compress
        output_file: Output path for compressed file (optional)
        
    Returns:
        Path to the compressed file
        
    Raises:
        FileNotFoundError: If source file doesn't exist
        OSError: If compression operation fails
    """
    source_path = Path(source_file)
    if not source_path.exists():
        raise FileNotFoundError(f"Source file not found: {source_file}")
    
    if output_file is None:
        output_file = str(source_path) + '.gz'
    
    output_path = Path(output_file)
    
    try:
        logger.info(f"Compressing file: {source_file} -> {output_file}")
        
        with open(source_path, 'rb') as f_in:
            with gzip.open(output_path, 'wb') as f_out:
                shutil.copyfileobj(f_in, f_out)
        
        original_size = source_path.stat().st_size
        compressed_size = output_path.stat().st_size
        ratio = (1 - compressed_size / original_size) * 100 if original_size > 0 else 0
        
        logger.info(f"Compression completed: {original_size} -> {compressed_size} bytes "
                   f"({ratio:.1f}% reduction)")
        
        return str(output_path)
        
    except Exception as e:
        logger.error(f"Compression failed: {e}")
        if output_path.exists():
            try:
                output_path.unlink()
            except Exception:
                pass
        raise OSError(f"Compression operation failed: {e}")


def decompress_file(source_file: str, output_file: str) -> str:
    """Decompress a gzip-compressed file.
    
    Args:
        source_file: Path to the compressed source file
        output_file: Path where to save the decompressed file
        
    Returns:
        Path to the decompressed file
        
    Raises:
        FileNotFoundError: If source file doesn't exist
        OSError: If decompression operation fails
    """
    source_path = Path(source_file)
    if not source_path.exists():
        raise FileNotFoundError(f"Source file not found: {source_file}")
    
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    try:
        logger.info(f"Decompressing file: {source_file} -> {output_file}")
        
        with gzip.open(source_path, 'rb') as f_in:
            with open(output_path, 'wb') as f_out:
                shutil.copyfileobj(f_in, f_out)
        
        compressed_size = source_path.stat().st_size
        decompressed_size = output_path.stat().st_size
        
        logger.info(f"Decompression completed: {compressed_size} -> {decompressed_size} bytes")
        
        return str(output_path)
        
    except Exception as e:
        logger.error(f"Decompression failed: {e}")
        if output_path.exists():
            try:
                output_path.unlink()
            except Exception:
                pass
        raise OSError(f"Decompression operation failed: {e}")


def is_compressed(file_path: str) -> bool:
    """Check if a file is gzip compressed.
    
    Args:
        file_path: Path to the file to check
        
    Returns:
        True if file is gzip compressed, False otherwise
    """
    try:
        with open(file_path, 'rb') as f:
            magic = f.read(2)
            return magic == b'\x1f\x8b'
    except Exception:
        return False


def get_compression_ratio(original_file: str, compressed_file: str) -> float:
    """Calculate compression ratio between two files.
    
    Args:
        original_file: Path to original file
        compressed_file: Path to compressed file
        
    Returns:
        Compression ratio as percentage (0-100)
    """
    try:
        original_size = Path(original_file).stat().st_size
        compressed_size = Path(compressed_file).stat().st_size
        
        if original_size == 0:
            return 0.0
        
        ratio = (1 - compressed_size / original_size) * 100
        return max(0.0, min(100.0, ratio))
        
    except Exception as e:
        logger.error(f"Error calculating compression ratio: {e}")
        return 0.0


def estimate_compressed_size(file_path: str, compression_ratio: float = 0.2) -> int:
    """Estimate the compressed size of a file.
    
    Args:
        file_path: Path to the file
        compression_ratio: Expected compression ratio (default: 0.2 = 20% of original)
        
    Returns:
        Estimated compressed size in bytes
    """
    try:
        original_size = Path(file_path).stat().st_size
        estimated_size = int(original_size * compression_ratio)
        return estimated_size
    except Exception:
        return 0


def compress_multiple_files(file_paths: list, output_dir: str) -> list:
    """Compress multiple files to a directory.
    
    Args:
        file_paths: List of file paths to compress
        output_dir: Directory where to save compressed files
        
    Returns:
        List of compressed file paths
    """
    output_directory = Path(output_dir)
    output_directory.mkdir(parents=True, exist_ok=True)
    
    compressed_files = []
    
    for file_path in file_paths:
        try:
            source_path = Path(file_path)
            if not source_path.exists():
                logger.warning(f"Skipping non-existent file: {file_path}")
                continue
            
            output_file = output_directory / (source_path.name + '.gz')
            
            compressed_file = compress_file(str(source_path), str(output_file))
            compressed_files.append(compressed_file)
            
        except Exception as e:
            logger.error(f"Failed to compress {file_path}: {e}")
    
    return compressed_files
