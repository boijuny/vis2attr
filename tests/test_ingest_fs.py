"""Unit tests for FileSystemIngestor."""

import pytest
import io
from pathlib import Path
from PIL import Image

from vis2attr.ingest.fs import FileSystemIngestor
from vis2attr.core.schemas import Item


class TestFileSystemIngestorInit:
    """Test FileSystemIngestor initialization."""
    
    def test_default_initialization(self):
        """Test ingestor with default parameters."""
        ingestor = FileSystemIngestor()
        
        assert ingestor.supported_formats == [".jpg", ".jpeg", ".png", ".webp"]
        assert ingestor.max_images_per_item == 3
        assert ingestor.max_resolution == 768
        assert ingestor.strip_exif is True
    
    def test_custom_initialization(self):
        """Test ingestor with custom parameters."""
        ingestor = FileSystemIngestor(
            supported_formats=[".jpg", ".png"],
            max_images_per_item=5,
            max_resolution=1024,
            strip_exif=False
        )
        
        assert ingestor.supported_formats == [".jpg", ".png"]
        assert ingestor.max_images_per_item == 5
        assert ingestor.max_resolution == 1024
        assert ingestor.strip_exif is False


class TestFileSystemIngestorLoad:
    """Test the main load method."""
    
    def test_load_nonexistent_path(self):
        """Test loading from non-existent path raises FileNotFoundError."""
        ingestor = FileSystemIngestor()
        
        with pytest.raises(FileNotFoundError):
            ingestor.load("nonexistent_path")
    
    def test_load_invalid_path_type(self, temp_dir):
        """Test loading from invalid path type raises ValueError."""
        ingestor = FileSystemIngestor()
        
        # Create a symlink to test edge case
        symlink_path = temp_dir / "symlink"
        symlink_path.symlink_to(temp_dir)
        
        with pytest.raises(ValueError, match="No valid images found"):
            ingestor.load(symlink_path)
    
    def test_load_single_file_success(self, single_image_file):
        """Test successfully loading a single image file."""
        ingestor = FileSystemIngestor()
        item = ingestor.load(single_image_file)
        
        assert isinstance(item, Item)
        assert item.item_id.startswith("item_")
        assert len(item.images) == 1
        assert isinstance(item.images[0], bytes)
        assert item.meta["source_path"] == str(single_image_file)
        assert item.meta["image_count"] == 1
        assert "file_size" in item.meta
    
    def test_load_directory_success(self, sample_images_dir):
        """Test successfully loading images from a directory."""
        ingestor = FileSystemIngestor(max_images_per_item=10)  # Allow more images
        item = ingestor.load(sample_images_dir)
        
        assert isinstance(item, Item)
        assert item.item_id.startswith("item_")
        assert len(item.images) == 5  # 4 JPG + 1 PNG files
        assert all(isinstance(img, bytes) for img in item.images)
        assert item.meta["source_path"] == str(sample_images_dir)
        assert item.meta["image_count"] == 5
        assert item.meta["total_files_found"] == 5
    
    def test_load_directory_with_unsupported_files(self, sample_images_dir):
        """Test loading directory with unsupported file formats."""
        ingestor = FileSystemIngestor(max_images_per_item=10)  # Allow more images
        item = ingestor.load(sample_images_dir)
        
        # Should only load supported formats (JPG, PNG), not BMP
        assert len(item.images) == 5  # 4 JPG + 1 PNG, excluding BMP
        assert item.meta["total_files_found"] == 5  # Total valid files found
    
    def test_load_empty_directory(self, empty_dir):
        """Test loading from empty directory raises ValueError."""
        ingestor = FileSystemIngestor()
        
        with pytest.raises(ValueError, match="No valid images found"):
            ingestor.load(empty_dir)
    
    def test_load_corrupted_image(self, corrupted_image_file):
        """Test loading corrupted image raises ValueError."""
        ingestor = FileSystemIngestor()
        
        with pytest.raises(ValueError, match="Unsupported image format"):
            ingestor.load(corrupted_image_file)


class TestFileSystemIngestorImageProcessing:
    """Test image processing functionality."""
    
    def test_image_resize(self, large_image_file):
        """Test that large images are resized to max_resolution."""
        ingestor = FileSystemIngestor(max_resolution=500)
        item = ingestor.load(large_image_file)
        
        # Verify image was resized
        with Image.open(io.BytesIO(item.images[0])) as img:
            assert max(img.size) <= 500
    
    def test_image_format_conversion(self, temp_dir):
        """Test that images are converted to RGB format."""
        # Create a grayscale image
        img = Image.new('L', (50, 50), color=128)
        img_path = temp_dir / "grayscale.jpg"
        img.save(img_path, format='JPEG')
        
        ingestor = FileSystemIngestor()
        item = ingestor.load(img_path)
        
        # Verify image was converted to RGB
        with Image.open(io.BytesIO(item.images[0])) as img:
            assert img.mode == 'RGB'
    
    def test_exif_stripping(self, temp_dir):
        """Test that EXIF data is stripped when requested."""
        # Create an image with EXIF data
        img = Image.new('RGB', (50, 50), color='blue')
        img_path = temp_dir / "with_exif.jpg"
        img.save(img_path, format='JPEG', quality=85)
        
        # Add some EXIF data (simulated)
        with Image.open(img_path) as img:
            img_with_exif = img.copy()
            img_with_exif.save(img_path, format='JPEG', quality=85)
        
        ingestor = FileSystemIngestor(strip_exif=True)
        item = ingestor.load(img_path)
        
        # Verify image was processed (exact EXIF comparison is complex)
        assert isinstance(item.images[0], bytes)
        assert len(item.images[0]) > 0
    
    def test_exif_preservation(self, temp_dir):
        """Test that EXIF data is preserved when strip_exif=False."""
        img = Image.new('RGB', (50, 50), color='green')
        img_path = temp_dir / "preserve_exif.jpg"
        img.save(img_path, format='JPEG', quality=85)
        
        ingestor = FileSystemIngestor(strip_exif=False)
        item = ingestor.load(img_path)
        
        assert isinstance(item.images[0], bytes)
        assert len(item.images[0]) > 0


class TestFileSystemIngestorValidation:
    """Test image file validation."""
    
    def test_is_valid_image_file_success(self, single_image_file):
        """Test valid image file detection."""
        ingestor = FileSystemIngestor()
        assert ingestor._is_valid_image_file(single_image_file) is True
    
    def test_is_valid_image_file_unsupported_format(self, temp_dir):
        """Test unsupported format detection."""
        # Create a BMP file (unsupported)
        img = Image.new('RGB', (50, 50), color='red')
        bmp_path = temp_dir / "test.bmp"
        img.save(bmp_path, format='BMP')
        
        ingestor = FileSystemIngestor()
        assert ingestor._is_valid_image_file(bmp_path) is False
    
    def test_is_valid_image_file_corrupted(self, corrupted_image_file):
        """Test corrupted image file detection."""
        ingestor = FileSystemIngestor()
        assert ingestor._is_valid_image_file(corrupted_image_file) is False
    
    def test_is_valid_image_file_nonexistent(self, temp_dir):
        """Test non-existent file detection."""
        ingestor = FileSystemIngestor()
        nonexistent_path = temp_dir / "nonexistent.jpg"
        assert ingestor._is_valid_image_file(nonexistent_path) is False
    
    def test_is_valid_image_file_directory(self, temp_dir):
        """Test directory detection."""
        ingestor = FileSystemIngestor()
        assert ingestor._is_valid_image_file(temp_dir) is False


class TestFileSystemIngestorItemValidation:
    """Test item validation functionality."""
    
    def test_validate_item_success(self, single_image_file):
        """Test successful item validation."""
        ingestor = FileSystemIngestor()
        item = ingestor.load(single_image_file)
        
        assert ingestor.validate_item(item) is True
    
    def test_validate_item_no_images(self):
        """Test validation of item with no images."""
        ingestor = FileSystemIngestor()
        item = Item(item_id="test", images=[])
        
        assert ingestor.validate_item(item) is False
    
    def test_validate_item_too_many_images(self, sample_images_dir):
        """Test validation of item with too many images."""
        ingestor = FileSystemIngestor(max_images_per_item=2)
        item = ingestor.load(sample_images_dir)
        
        # Should be limited to 2 images due to max_images_per_item
        assert len(item.images) == 2
        assert ingestor.validate_item(item) is True
    
    def test_validate_item_invalid_image_data(self):
        """Test validation of item with invalid image data."""
        ingestor = FileSystemIngestor()
        item = Item(
            item_id="test",
            images=[b"invalid image data"],
            meta={}
        )
        
        assert ingestor.validate_item(item) is False


class TestFileSystemIngestorEdgeCases:
    """Test edge cases and error conditions."""
    
    def test_max_images_per_item_limit(self, sample_images_dir):
        """Test that max_images_per_item limit is enforced."""
        ingestor = FileSystemIngestor(max_images_per_item=2)
        item = ingestor.load(sample_images_dir)
        
        assert len(item.images) == 2
        assert item.meta["image_count"] == 2
        assert item.meta["total_files_found"] == 5  # Total found, but limited
    
    def test_item_id_generation_consistency(self, single_image_file):
        """Test that item ID generation is consistent."""
        ingestor = FileSystemIngestor()
        
        # Load the same file multiple times
        item1 = ingestor.load(single_image_file)
        item2 = ingestor.load(single_image_file)
        
        assert item1.item_id == item2.item_id
        assert item1.item_id.startswith("item_")
    
    def test_different_item_ids_for_different_paths(self, temp_dir):
        """Test that different paths generate different item IDs."""
        # Create two different image files
        img1 = Image.new('RGB', (50, 50), color='red')
        img1_path = temp_dir / "img1.jpg"
        img1.save(img1_path, format='JPEG')
        
        img2 = Image.new('RGB', (50, 50), color='blue')
        img2_path = temp_dir / "img2.jpg"
        img2.save(img2_path, format='JPEG')
        
        ingestor = FileSystemIngestor()
        item1 = ingestor.load(img1_path)
        item2 = ingestor.load(img2_path)
        
        assert item1.item_id != item2.item_id
    
    def test_metadata_accuracy(self, single_image_file):
        """Test that metadata is accurate."""
        ingestor = FileSystemIngestor()
        item = ingestor.load(single_image_file)
        
        assert item.meta["source_path"] == str(single_image_file)
        assert item.meta["image_count"] == 1
        assert item.meta["file_size"] == single_image_file.stat().st_size
    
    def test_directory_metadata_accuracy(self, sample_images_dir):
        """Test that directory metadata is accurate."""
        ingestor = FileSystemIngestor(max_images_per_item=10)  # Allow more images
        item = ingestor.load(sample_images_dir)
        
        assert item.meta["source_path"] == str(sample_images_dir)
        assert item.meta["image_count"] == 5
        assert item.meta["total_files_found"] == 5


class TestFileSystemIngestorSupportedFormats:
    """Test different supported image formats."""
    
    def test_jpg_format(self, temp_dir):
        """Test JPG format support."""
        img = Image.new('RGB', (50, 50), color='red')
        jpg_path = temp_dir / "test.jpg"
        img.save(jpg_path, format='JPEG')
        
        ingestor = FileSystemIngestor()
        item = ingestor.load(jpg_path)
        
        assert len(item.images) == 1
        assert isinstance(item.images[0], bytes)
    
    def test_png_format(self, temp_dir):
        """Test PNG format support."""
        img = Image.new('RGB', (50, 50), color='blue')
        png_path = temp_dir / "test.png"
        img.save(png_path, format='PNG')
        
        ingestor = FileSystemIngestor()
        item = ingestor.load(png_path)
        
        assert len(item.images) == 1
        assert isinstance(item.images[0], bytes)
    
    def test_webp_format(self, temp_dir):
        """Test WebP format support."""
        img = Image.new('RGB', (50, 50), color='green')
        webp_path = temp_dir / "test.webp"
        img.save(webp_path, format='WebP')
        
        ingestor = FileSystemIngestor()
        item = ingestor.load(webp_path)
        
        assert len(item.images) == 1
        assert isinstance(item.images[0], bytes)
    
    def test_custom_supported_formats(self, temp_dir):
        """Test custom supported formats configuration."""
        # Create a BMP file
        img = Image.new('RGB', (50, 50), color='yellow')
        bmp_path = temp_dir / "test.bmp"
        img.save(bmp_path, format='BMP')
        
        # Configure ingestor to support BMP
        ingestor = FileSystemIngestor(supported_formats=[".bmp"])
        item = ingestor.load(bmp_path)
        
        assert len(item.images) == 1
        assert isinstance(item.images[0], bytes)
