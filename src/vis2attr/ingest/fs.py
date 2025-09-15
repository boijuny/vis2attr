"""File system image ingestion module."""

import os
from pathlib import Path
from typing import List, Union, Optional, Dict, Any
from PIL import Image
import hashlib
import uuid

from ..core.schemas import Item
from ..core.exceptions import IngestError, create_ingest_error
from ..core.constants import (
    DEFAULT_MAX_RESOLUTION,
    DEFAULT_MAX_IMAGES_PER_ITEM,
    DEFAULT_SUPPORTED_FORMATS,
    DEFAULT_STRIP_EXIF
)


class FileSystemIngestor:
    """Ingests images from the local file system."""
    
    def __init__(
        self,
        supported_formats: List[str] = None,
        max_images_per_item: int = DEFAULT_MAX_IMAGES_PER_ITEM,
        max_resolution: int = DEFAULT_MAX_RESOLUTION,
        strip_exif: bool = DEFAULT_STRIP_EXIF
    ):
        """Initialize the file system ingestor.
        
        Args:
            supported_formats: List of supported image file extensions
            max_images_per_item: Maximum number of images per item
            max_resolution: Maximum image resolution (width or height)
            strip_exif: Whether to strip EXIF data from images
        """
        self.supported_formats = supported_formats or DEFAULT_SUPPORTED_FORMATS
        self.max_images_per_item = max_images_per_item
        self.max_resolution = max_resolution
        self.strip_exif = strip_exif
    
    def load(self, source: Union[str, Path]) -> Item:
        """Load images from a file system source.
        
        Args:
            source: Path to a directory or single image file
            
        Returns:
            Item object containing loaded images and metadata
            
        Raises:
            FileNotFoundError: If source path doesn't exist
            ValueError: If no valid images found or validation fails
        """
        source_path = Path(source)
        
        if not source_path.exists():
            raise FileNotFoundError(f"Source path does not exist: {source_path}")
        
        if source_path.is_file():
            return self._load_single_file(source_path)
        elif source_path.is_dir():
            return self._load_directory(source_path)
        else:
            raise ValueError(f"Source must be a file or directory: {source_path}")
    
    def _load_single_file(self, file_path: Path) -> Item:
        """Load a single image file."""
        if not self._is_valid_image_file(file_path):
            raise ValueError(f"Unsupported image format: {file_path}")
        
        image_data = self._load_and_process_image(file_path)
        item_id = self._generate_item_id(file_path)
        
        return Item(
            item_id=item_id,
            images=[image_data],
            meta={
                "source_path": str(file_path),
                "file_size": file_path.stat().st_size,
                "image_count": 1
            }
        )
    
    def _load_directory(self, dir_path: Path) -> Item:
        """Load images from a directory."""
        image_files = self._find_image_files(dir_path)
        
        if not image_files:
            raise ValueError(f"No valid images found in directory: {dir_path}")
        
        if len(image_files) > self.max_images_per_item:
            image_files = image_files[:self.max_images_per_item]
        
        images = []
        for file_path in image_files:
            image_data = self._load_and_process_image(file_path)
            images.append(image_data)
        
        item_id = self._generate_item_id(dir_path)
        
        return Item(
            item_id=item_id,
            images=images,
            meta={
                "source_path": str(dir_path),
                "image_count": len(images),
                "total_files_found": len(self._find_image_files(dir_path))
            }
        )
    
    def _find_image_files(self, dir_path: Path) -> List[Path]:
        """Find all valid image files in a directory."""
        image_files = []
        
        for file_path in dir_path.iterdir():
            if file_path.is_file() and self._is_valid_image_file(file_path):
                image_files.append(file_path)
        
        # Sort for consistent ordering
        return sorted(image_files)
    
    def _is_valid_image_file(self, file_path: Path) -> bool:
        """Check if a file is a valid image file."""
        if not file_path.is_file():
            return False
        
        # Check file extension
        if file_path.suffix.lower() not in self.supported_formats:
            return False
        
        # Try to open with PIL to validate it's actually an image
        try:
            with Image.open(file_path) as img:
                img.verify()
            return True
        except Exception:
            return False
    
    def _load_and_process_image(self, file_path: Path) -> bytes:
        """Load and process an image file."""
        try:
            with Image.open(file_path) as img:
                # Convert to RGB if necessary
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                
                # Resize if too large
                if max(img.size) > self.max_resolution:
                    img.thumbnail((self.max_resolution, self.max_resolution), Image.Resampling.LANCZOS)
                
                # Strip EXIF if requested
                if self.strip_exif:
                    # Create new image without EXIF
                    data = list(img.getdata())
                    img_without_exif = Image.new(img.mode, img.size)
                    img_without_exif.putdata(data)
                    img = img_without_exif
                
                # Convert to bytes
                import io
                img_bytes = io.BytesIO()
                img.save(img_bytes, format='JPEG', quality=85)
                return img_bytes.getvalue()
                
        except Exception as e:
            raise create_ingest_error(
                f"Failed to process image: {e}",
                file_path=str(file_path),
                file_type=file_path.suffix
            ) from e
    
    def _generate_item_id(self, path: Path) -> str:
        """Generate a unique item ID based on the path."""
        # Use path hash for deterministic IDs
        path_str = str(path.absolute())
        path_hash = hashlib.md5(path_str.encode()).hexdigest()[:8]
        return f"item_{path_hash}"
    
    def validate_item(self, item: Item) -> bool:
        """Validate an item meets quality requirements.
        
        Args:
            item: Item to validate
            
        Returns:
            True if item is valid, False otherwise
        """
        if not item.images:
            return False
        
        if len(item.images) > self.max_images_per_item:
            return False
        
        # Validate each image
        for image_data in item.images:
            if not isinstance(image_data, bytes):
                return False
            
            # Check if image data is valid
            try:
                import io
                with Image.open(io.BytesIO(image_data)) as img:
                    img.verify()
            except Exception:
                return False
        
        return True
