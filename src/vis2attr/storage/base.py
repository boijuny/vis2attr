"""Base storage interface for persisting attributes and lineage data."""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List, Union
from pathlib import Path
from datetime import datetime
from ..core.schemas import Attributes, VLMRaw, Item


class StorageError(Exception):
    """Raised when storage operations fail."""
    pass


class StorageBackend(ABC):
    """Abstract base class for storage backends.
    
    Storage backends handle persisting and retrieving structured attributes,
    raw VLM responses, and processing lineage data.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize the storage backend with configuration.
        
        Args:
            config: Backend-specific configuration dictionary
        """
        self.config = config or {}
    
    @abstractmethod
    def store_attributes(self, item_id: str, attributes: Attributes, 
                        metadata: Optional[Dict[str, Any]] = None) -> str:
        """Store structured attributes for an item.
        
        Args:
            item_id: Unique identifier for the item
            attributes: Structured attributes to store
            metadata: Optional metadata about the storage operation
            
        Returns:
            str: Storage identifier/path for the stored data
            
        Raises:
            StorageError: If storage fails
        """
        pass
    
    @abstractmethod
    def store_raw_response(self, item_id: str, raw_response: VLMRaw,
                          metadata: Optional[Dict[str, Any]] = None) -> str:
        """Store raw VLM response for an item.
        
        Args:
            item_id: Unique identifier for the item
            raw_response: Raw VLM response to store
            metadata: Optional metadata about the storage operation
            
        Returns:
            str: Storage identifier/path for the stored data
            
        Raises:
            StorageError: If storage fails
        """
        pass
    
    @abstractmethod
    def store_lineage(self, item_id: str, lineage: Dict[str, Any],
                     metadata: Optional[Dict[str, Any]] = None) -> str:
        """Store processing lineage for an item.
        
        Args:
            item_id: Unique identifier for the item
            lineage: Processing lineage data
            metadata: Optional metadata about the storage operation
            
        Returns:
            str: Storage identifier/path for the stored data
            
        Raises:
            StorageError: If storage fails
        """
        pass
    
    @abstractmethod
    def retrieve_attributes(self, storage_id: str) -> Optional[Attributes]:
        """Retrieve stored attributes by storage ID.
        
        Args:
            storage_id: Storage identifier/path
            
        Returns:
            Attributes: Retrieved attributes or None if not found
            
        Raises:
            StorageError: If retrieval fails
        """
        pass
    
    @abstractmethod
    def retrieve_raw_response(self, storage_id: str) -> Optional[VLMRaw]:
        """Retrieve stored raw response by storage ID.
        
        Args:
            storage_id: Storage identifier/path
            
        Returns:
            VLMRaw: Retrieved raw response or None if not found
            
        Raises:
            StorageError: If retrieval fails
        """
        pass
    
    @abstractmethod
    def retrieve_lineage(self, storage_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve stored lineage by storage ID.
        
        Args:
            storage_id: Storage identifier/path
            
        Returns:
            Dict[str, Any]: Retrieved lineage data or None if not found
            
        Raises:
            StorageError: If retrieval fails
        """
        pass
    
    @abstractmethod
    def list_items(self, limit: Optional[int] = None, 
                  offset: Optional[int] = None) -> List[Dict[str, Any]]:
        """List stored items with metadata.
        
        Args:
            limit: Maximum number of items to return
            offset: Number of items to skip
            
        Returns:
            List[Dict[str, Any]]: List of item metadata dictionaries
            
        Raises:
            StorageError: If listing fails
        """
        pass
    
    @abstractmethod
    def delete_item(self, item_id: str) -> bool:
        """Delete all data for an item.
        
        Args:
            item_id: Unique identifier for the item
            
        Returns:
            bool: True if deletion was successful, False if item not found
            
        Raises:
            StorageError: If deletion fails
        """
        pass
    
    def _generate_storage_id(self, item_id: str, data_type: str, 
                           timestamp: Optional[datetime] = None) -> str:
        """Generate a unique storage identifier.
        
        Args:
            item_id: Item identifier
            data_type: Type of data (attributes, raw_response, lineage)
            timestamp: Optional timestamp for the ID
            
        Returns:
            str: Unique storage identifier
        """
        if timestamp is None:
            timestamp = datetime.now()
        
        # Format: {item_id}/{data_type}/{timestamp}
        return f"{item_id}/{data_type}/{timestamp.isoformat()}"
    
    def _validate_item_id(self, item_id: str) -> None:
        """Validate item ID format.
        
        Args:
            item_id: Item identifier to validate
            
        Raises:
            StorageError: If item ID is invalid
        """
        if not item_id or not isinstance(item_id, str):
            raise StorageError("Item ID must be a non-empty string")
        
        # Check for invalid characters that might cause filesystem issues
        invalid_chars = ['/', '\\', ':', '*', '?', '"', '<', '>', '|']
        if any(char in item_id for char in invalid_chars):
            raise StorageError(f"Item ID contains invalid characters: {invalid_chars}")
