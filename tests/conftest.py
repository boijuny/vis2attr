"""Pytest configuration and shared fixtures."""

import pytest
import tempfile
import shutil
from pathlib import Path
from PIL import Image
import io


@pytest.fixture
def temp_dir():
    """Create a temporary directory for tests."""
    temp_path = Path(tempfile.mkdtemp())
    yield temp_path
    shutil.rmtree(temp_path)


@pytest.fixture
def sample_image_data():
    """Create sample image data for testing."""
    # Create a simple 100x100 RGB image
    img = Image.new('RGB', (100, 100), color='red')
    img_bytes = io.BytesIO()
    img.save(img_bytes, format='JPEG', quality=85)
    return img_bytes.getvalue()


@pytest.fixture
def sample_images_dir(temp_dir, sample_image_data):
    """Create a directory with sample images."""
    images_dir = temp_dir / "images"
    images_dir.mkdir()
    
    # Create multiple test images
    for i, color in enumerate(['red', 'green', 'blue', 'yellow']):
        img = Image.new('RGB', (50, 50), color=color)
        img_path = images_dir / f"test_{i}.jpg"
        img.save(img_path, format='JPEG', quality=85)
    
    # Create a PNG image
    img = Image.new('RGB', (75, 75), color='purple')
    img_path = images_dir / "test_png.png"
    img.save(img_path, format='PNG')
    
    # Create an unsupported format (BMP)
    img = Image.new('RGB', (25, 25), color='orange')
    img_path = images_dir / "test_unsupported.bmp"
    img.save(img_path, format='BMP')
    
    return images_dir


@pytest.fixture
def single_image_file(temp_dir, sample_image_data):
    """Create a single image file for testing."""
    img_path = temp_dir / "single_test.jpg"
    with open(img_path, 'wb') as f:
        f.write(sample_image_data)
    return img_path


@pytest.fixture
def large_image_file(temp_dir):
    """Create a large image file for testing resize functionality."""
    # Create a 2000x2000 image (larger than max_resolution)
    img = Image.new('RGB', (2000, 2000), color='cyan')
    img_path = temp_dir / "large_test.jpg"
    img.save(img_path, format='JPEG', quality=85)
    return img_path


@pytest.fixture
def corrupted_image_file(temp_dir):
    """Create a corrupted image file for testing error handling."""
    img_path = temp_dir / "corrupted.jpg"
    with open(img_path, 'wb') as f:
        f.write(b"This is not a valid image file")
    return img_path


@pytest.fixture
def empty_dir(temp_dir):
    """Create an empty directory for testing."""
    empty_dir = temp_dir / "empty"
    empty_dir.mkdir()
    return empty_dir
