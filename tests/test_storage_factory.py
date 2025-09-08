"""Tests for storage factory."""

import pytest
from vis2attr.storage import StorageFactory, FileStorage, StorageBackend


class TestStorageFactory:
    """Test cases for StorageFactory."""
    
    def test_create_file_storage(self):
        """Test creating a file storage backend."""
        config = {'storage_root': '/tmp/test'}
        storage = StorageFactory.create_backend('files', config)
        
        assert isinstance(storage, FileStorage)
        assert storage.config['storage_root'] == '/tmp/test'
    
    def test_create_file_storage_aliases(self):
        """Test creating file storage with aliases."""
        config = {'storage_root': '/tmp/test'}
        
        # Test 'file' alias
        storage1 = StorageFactory.create_backend('file', config)
        assert isinstance(storage1, FileStorage)
        
        # Test 'local' alias
        storage2 = StorageFactory.create_backend('local', config)
        assert isinstance(storage2, FileStorage)
    
    def test_create_storage_without_config(self):
        """Test creating storage backend without configuration."""
        storage = StorageFactory.create_backend('files')
        assert isinstance(storage, FileStorage)
        assert storage.config == {}
    
    def test_unsupported_backend(self):
        """Test creating an unsupported backend."""
        with pytest.raises(ValueError, match="Unsupported storage backend"):
            StorageFactory.create_backend('unsupported')
    
    def test_list_backends(self):
        """Test listing available backends."""
        backends = StorageFactory.list_backends()
        
        assert 'files' in backends
        assert 'file' in backends
        assert 'local' in backends
        assert len(backends) >= 3
    
    def test_get_backend_info(self):
        """Test getting backend information."""
        info = StorageFactory.get_backend_info('files')
        
        assert info['name'] == 'files'
        assert info['class'] == 'FileStorage'
        assert 'vis2attr.storage.files' in info['module']
        assert info['docstring'] is not None
    
    def test_get_unsupported_backend_info(self):
        """Test getting info for unsupported backend."""
        with pytest.raises(ValueError, match="Unsupported storage backend"):
            StorageFactory.get_backend_info('unsupported')
    
    def test_register_custom_backend(self):
        """Test registering a custom backend."""
        class CustomStorage(StorageBackend):
            def store_attributes(self, item_id, attributes, metadata=None):
                return "custom_id"
            
            def store_raw_response(self, item_id, raw_response, metadata=None):
                return "custom_id"
            
            def store_lineage(self, item_id, lineage, metadata=None):
                return "custom_id"
            
            def retrieve_attributes(self, storage_id):
                return None
            
            def retrieve_raw_response(self, storage_id):
                return None
            
            def retrieve_lineage(self, storage_id):
                return None
            
            def list_items(self, limit=None, offset=None):
                return []
            
            def delete_item(self, item_id):
                return False
        
        # Register custom backend
        StorageFactory.register_backend('custom', CustomStorage)
        
        # Verify it's available
        backends = StorageFactory.list_backends()
        assert 'custom' in backends
        
        # Test creating it
        storage = StorageFactory.create_backend('custom')
        assert isinstance(storage, CustomStorage)
        
        # Test getting info
        info = StorageFactory.get_backend_info('custom')
        assert info['name'] == 'custom'
        assert info['class'] == 'CustomStorage'
