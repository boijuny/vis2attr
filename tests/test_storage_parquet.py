"""Tests for file storage backend."""

import pytest
import tempfile
import shutil
from pathlib import Path
from datetime import datetime, timezone

from vis2attr.storage import ParquetStorage, StorageError
from vis2attr.core.schemas import Attributes, VLMRaw


class TestParquetStorage:
    """Test cases for ParquetStorage backend."""
    
    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for testing."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def storage(self, temp_dir):
        """Create a ParquetStorage instance for testing."""
        config = {
            'file_path': str(Path(temp_dir) / 'test.parquet'),
            'create_dirs': True
        }
        return ParquetStorage(config)
    
    @pytest.fixture
    def sample_attributes(self):
        """Create sample attributes for testing."""
        return Attributes(
            data={'brand': 'Nike', 'color': 'red'},
            confidences={'brand': 0.9, 'color': 0.8},
            tags={'high_confidence'},
            notes='Test attributes',
            lineage={'parser': 'json', 'version': '1.0'}
        )
    
    @pytest.fixture
    def sample_raw_response(self):
        """Create sample raw response for testing."""
        return VLMRaw(
            content='{"brand": "Nike", "color": "red"}',
            usage={'tokens': 100, 'cost': 0.01},
            latency_ms=1500.0,
            provider='test_provider',
            model='test_model',
            timestamp=datetime.now(timezone.utc)
        )
    
    def test_store_and_retrieve_attributes(self, storage, sample_attributes):
        """Test storing and retrieving attributes."""
        item_id = "test_item_1"
        
        # Store attributes
        storage_id = storage.store_attributes(item_id, sample_attributes)
        assert storage_id is not None
        assert item_id in storage_id
        
        # Retrieve attributes
        retrieved = storage.retrieve_attributes(storage_id)
        assert retrieved is not None
        assert retrieved.data == sample_attributes.data
        assert retrieved.confidences == sample_attributes.confidences
        assert retrieved.tags == sample_attributes.tags
        assert retrieved.notes == sample_attributes.notes
        assert retrieved.lineage == sample_attributes.lineage
    
    def test_store_and_retrieve_raw_response(self, storage, sample_raw_response):
        """Test storing and retrieving raw response."""
        item_id = "test_item_2"
        
        # Store raw response
        storage_id = storage.store_raw_response(item_id, sample_raw_response)
        assert storage_id is not None
        assert item_id in storage_id
        
        # Retrieve raw response
        retrieved = storage.retrieve_raw_response(storage_id)
        assert retrieved is not None
        assert retrieved.content == sample_raw_response.content
        assert retrieved.usage == sample_raw_response.usage
        assert retrieved.latency_ms == sample_raw_response.latency_ms
        assert retrieved.provider == sample_raw_response.provider
        assert retrieved.model == sample_raw_response.model
    
    def test_store_and_retrieve_lineage(self, storage):
        """Test storing and retrieving lineage."""
        item_id = "test_item_3"
        lineage = {
            'parser': 'json',
            'version': '1.0',
            'processing_time': 1.5,
            'steps': ['parse', 'validate', 'store']
        }
        
        # Store lineage
        storage_id = storage.store_lineage(item_id, lineage)
        assert storage_id is not None
        assert item_id in storage_id
        
        # Retrieve lineage
        retrieved = storage.retrieve_lineage(storage_id)
        assert retrieved is not None
        assert retrieved == lineage
    
    def test_list_items(self, storage, sample_attributes, sample_raw_response):
        """Test listing stored items."""
        # Store data for multiple items
        storage.store_attributes("item_1", sample_attributes)
        storage.store_raw_response("item_2", sample_raw_response)
        storage.store_lineage("item_3", {'test': 'data'})
        
        # List items
        items = storage.list_items()
        assert len(items) == 3
        
        # Check item metadata
        item_ids = [item['item_id'] for item in items]
        assert 'item_1' in item_ids
        assert 'item_2' in item_ids
        assert 'item_3' in item_ids
        
        # Check specific item metadata
        item_1 = next(item for item in items if item['item_id'] == 'item_1')
        assert item_1['has_attributes'] is True
        assert item_1['has_raw_response'] is False
        assert item_1['has_lineage'] is False
    
    def test_delete_item(self, storage, sample_attributes):
        """Test deleting an item."""
        item_id = "test_item_delete"
        
        # Store attributes
        storage.store_attributes(item_id, sample_attributes)
        
        # Verify item exists
        items = storage.list_items()
        item_ids = [item['item_id'] for item in items]
        assert item_id in item_ids
        
        # Delete item
        result = storage.delete_item(item_id)
        assert result is True
        
        # Verify item is deleted
        items = storage.list_items()
        item_ids = [item['item_id'] for item in items]
        assert item_id not in item_ids
    
    def test_delete_nonexistent_item(self, storage):
        """Test deleting a non-existent item."""
        result = storage.delete_item("nonexistent_item")
        assert result is False
    
    def test_invalid_item_id(self, storage, sample_attributes):
        """Test handling of invalid item IDs."""
        with pytest.raises(StorageError):
            storage.store_attributes("", sample_attributes)
        
        with pytest.raises(StorageError):
            storage.store_attributes("invalid/id", sample_attributes)
    
    def test_retrieve_nonexistent_data(self, storage):
        """Test retrieving non-existent data."""
        result = storage.retrieve_attributes("nonexistent/storage/id")
        assert result is None
        
        result = storage.retrieve_raw_response("nonexistent/storage/id")
        assert result is None
        
        result = storage.retrieve_lineage("nonexistent/storage/id")
        assert result is None
    
    def test_metadata_storage(self, storage, sample_attributes):
        """Test storing and retrieving metadata."""
        item_id = "test_metadata"
        metadata = {'source': 'test', 'version': '1.0'}
        
        storage_id = storage.store_attributes(item_id, sample_attributes, metadata)
        
        # Note: In a real implementation, we might want to add a method to retrieve metadata
        # For now, we just verify the storage operation succeeds
        assert storage_id is not None
    
    def test_parquet_file_creation(self, temp_dir):
        """Test that Parquet file is created and data is stored."""
        config = {
            'file_path': str(Path(temp_dir) / 'test.parquet'),
            'create_dirs': True
        }
        storage = ParquetStorage(config)
        
        item_id = "test_parquet"
        sample_attributes = Attributes(
            data={'test': 'parquet'},
            confidences={'test': 0.9}
        )
        
        # Store attributes
        storage_id = storage.store_attributes(item_id, sample_attributes)
        assert storage_id is not None
        
        # Check if Parquet file was created
        parquet_file = Path(temp_dir) / 'test.parquet'
        assert parquet_file.exists()
        
        # Verify data can be retrieved
        retrieved_attributes = storage.retrieve_attributes(storage_id)
        assert retrieved_attributes is not None
        assert retrieved_attributes.data['test'] == 'parquet'
    
    def test_parquet_data_retrieval(self, temp_dir):
        """Test that data can be retrieved from Parquet storage."""
        config = {
            'file_path': str(Path(temp_dir) / 'retrieval_test.parquet'),
            'create_dirs': True
        }
        storage = ParquetStorage(config)
        
        # Store some data
        sample_attributes = Attributes(
            data={'test': 'retrieval'},
            confidences={'test': 0.9}
        )
        storage_id = storage.store_attributes("test_retrieval", sample_attributes)
        
        # Verify data can be retrieved
        retrieved_attributes = storage.retrieve_attributes(storage_id)
        assert retrieved_attributes is not None
        assert retrieved_attributes.data['test'] == 'retrieval'
        assert retrieved_attributes.confidences['test'] == 0.9
        
        # Test listing items
        items = storage.list_items()
        assert len(items) == 1
        assert items[0]['item_id'] == 'test_retrieval'
        assert items[0]['has_attributes'] == True
