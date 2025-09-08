"""Local file system storage backend for attributes and lineage data."""

import json
import pickle
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime
import shutil

from .base import StorageBackend, StorageError
from ..core.schemas import Attributes, VLMRaw


class FileStorage(StorageBackend):
    """Local file system storage backend.
    
    Stores data in a structured directory hierarchy:
    storage_root/
    ├── {item_id}/
    │   ├── attributes/
    │   │   └── {timestamp}.json
    │   ├── raw_responses/
    │   │   └── {timestamp}.json
    │   └── lineage/
    │       └── {timestamp}.json
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize file storage backend.
        
        Args:
            config: Configuration dictionary with keys:
                - storage_root: Base directory for storage (default: ./storage)
                - create_dirs: Whether to create directories if they don't exist (default: True)
                - backup_enabled: Whether to create backups (default: False)
        """
        super().__init__(config)
        self.storage_root = Path(self.config.get('storage_root', './storage'))
        self.create_dirs = self.config.get('create_dirs', True)
        self.backup_enabled = self.config.get('backup_enabled', False)
        
        if self.create_dirs:
            self.storage_root.mkdir(parents=True, exist_ok=True)
    
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
        self._validate_item_id(item_id)
        
        try:
            # Create item directory structure
            item_dir = self.storage_root / item_id
            attributes_dir = item_dir / 'attributes'
            attributes_dir.mkdir(parents=True, exist_ok=True)
            
            # Generate storage ID and file path
            storage_id = self._generate_storage_id(item_id, 'attributes')
            file_path = attributes_dir / f"{datetime.now().isoformat()}.json"
            
            # Prepare data for serialization
            data = {
                'item_id': item_id,
                'storage_id': storage_id,
                'timestamp': datetime.now().isoformat(),
                'attributes': {
                    'data': attributes.data,
                    'confidences': attributes.confidences,
                    'tags': list(attributes.tags) if attributes.tags else [],
                    'notes': attributes.notes,
                    'lineage': attributes.lineage
                },
                'metadata': metadata or {}
            }
            
            # Write to file
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            # Create backup if enabled
            if self.backup_enabled:
                self._create_backup(file_path)
            
            return storage_id
            
        except Exception as e:
            raise StorageError(f"Failed to store attributes for item {item_id}: {str(e)}")
    
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
        self._validate_item_id(item_id)
        
        try:
            # Create item directory structure
            item_dir = self.storage_root / item_id
            raw_dir = item_dir / 'raw_responses'
            raw_dir.mkdir(parents=True, exist_ok=True)
            
            # Generate storage ID and file path
            storage_id = self._generate_storage_id(item_id, 'raw_responses')
            file_path = raw_dir / f"{datetime.now().isoformat()}.json"
            
            # Prepare data for serialization
            data = {
                'item_id': item_id,
                'storage_id': storage_id,
                'timestamp': datetime.now().isoformat(),
                'raw_response': {
                    'content': raw_response.content,
                    'usage': raw_response.usage,
                    'latency_ms': raw_response.latency_ms,
                    'provider': raw_response.provider,
                    'model': raw_response.model,
                    'timestamp': raw_response.timestamp.isoformat() if raw_response.timestamp else None
                },
                'metadata': metadata or {}
            }
            
            # Write to file
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            # Create backup if enabled
            if self.backup_enabled:
                self._create_backup(file_path)
            
            return storage_id
            
        except Exception as e:
            raise StorageError(f"Failed to store raw response for item {item_id}: {str(e)}")
    
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
        self._validate_item_id(item_id)
        
        try:
            # Create item directory structure
            item_dir = self.storage_root / item_id
            lineage_dir = item_dir / 'lineage'
            lineage_dir.mkdir(parents=True, exist_ok=True)
            
            # Generate storage ID and file path
            storage_id = self._generate_storage_id(item_id, 'lineage')
            file_path = lineage_dir / f"{datetime.now().isoformat()}.json"
            
            # Prepare data for serialization
            data = {
                'item_id': item_id,
                'storage_id': storage_id,
                'timestamp': datetime.now().isoformat(),
                'lineage': lineage,
                'metadata': metadata or {}
            }
            
            # Write to file
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            # Create backup if enabled
            if self.backup_enabled:
                self._create_backup(file_path)
            
            return storage_id
            
        except Exception as e:
            raise StorageError(f"Failed to store lineage for item {item_id}: {str(e)}")
    
    def retrieve_attributes(self, storage_id: str) -> Optional[Attributes]:
        """Retrieve stored attributes by storage ID.
        
        Args:
            storage_id: Storage identifier/path
            
        Returns:
            Attributes: Retrieved attributes or None if not found
            
        Raises:
            StorageError: If retrieval fails
        """
        try:
            file_path = self._find_storage_file(storage_id, 'attributes')
            if not file_path or not file_path.exists():
                return None
            
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            attr_data = data['attributes']
            return Attributes(
                data=attr_data['data'],
                confidences=attr_data['confidences'],
                tags=set(attr_data.get('tags', [])),
                notes=attr_data.get('notes', ''),
                lineage=attr_data.get('lineage', {})
            )
            
        except Exception as e:
            raise StorageError(f"Failed to retrieve attributes for storage ID {storage_id}: {str(e)}")
    
    def retrieve_raw_response(self, storage_id: str) -> Optional[VLMRaw]:
        """Retrieve stored raw response by storage ID.
        
        Args:
            storage_id: Storage identifier/path
            
        Returns:
            VLMRaw: Retrieved raw response or None if not found
            
        Raises:
            StorageError: If retrieval fails
        """
        try:
            file_path = self._find_storage_file(storage_id, 'raw_responses')
            if not file_path or not file_path.exists():
                return None
            
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            resp_data = data['raw_response']
            return VLMRaw(
                content=resp_data['content'],
                usage=resp_data['usage'],
                latency_ms=resp_data['latency_ms'],
                provider=resp_data['provider'],
                model=resp_data['model'],
                timestamp=datetime.fromisoformat(resp_data['timestamp']) if resp_data['timestamp'] else None
            )
            
        except Exception as e:
            raise StorageError(f"Failed to retrieve raw response for storage ID {storage_id}: {str(e)}")
    
    def retrieve_lineage(self, storage_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve stored lineage by storage ID.
        
        Args:
            storage_id: Storage identifier/path
            
        Returns:
            Dict[str, Any]: Retrieved lineage data or None if not found
            
        Raises:
            StorageError: If retrieval fails
        """
        try:
            file_path = self._find_storage_file(storage_id, 'lineage')
            if not file_path or not file_path.exists():
                return None
            
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            return data['lineage']
            
        except Exception as e:
            raise StorageError(f"Failed to retrieve lineage for storage ID {storage_id}: {str(e)}")
    
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
        try:
            if not self.storage_root.exists():
                return []
            
            items = []
            for item_dir in self.storage_root.iterdir():
                if not item_dir.is_dir():
                    continue
                
                item_metadata = {
                    'item_id': item_dir.name,
                    'created_at': self._get_dir_creation_time(item_dir),
                    'has_attributes': (item_dir / 'attributes').exists(),
                    'has_raw_response': (item_dir / 'raw_responses').exists(),
                    'has_lineage': (item_dir / 'lineage').exists(),
                    'file_count': self._count_files_in_dir(item_dir)
                }
                items.append(item_metadata)
            
            # Sort by creation time (newest first)
            items.sort(key=lambda x: x['created_at'], reverse=True)
            
            # Apply offset and limit
            if offset:
                items = items[offset:]
            if limit:
                items = items[:limit]
            
            return items
            
        except Exception as e:
            raise StorageError(f"Failed to list items: {str(e)}")
    
    def delete_item(self, item_id: str) -> bool:
        """Delete all data for an item.
        
        Args:
            item_id: Unique identifier for the item
            
        Returns:
            bool: True if deletion was successful, False if item not found
            
        Raises:
            StorageError: If deletion fails
        """
        self._validate_item_id(item_id)
        
        try:
            item_dir = self.storage_root / item_id
            if not item_dir.exists():
                return False
            
            # Create backup if enabled
            if self.backup_enabled:
                self._create_backup(item_dir)
            
            # Remove the entire item directory
            shutil.rmtree(item_dir)
            return True
            
        except Exception as e:
            raise StorageError(f"Failed to delete item {item_id}: {str(e)}")
    
    def _find_storage_file(self, storage_id: str, data_type: str) -> Optional[Path]:
        """Find the file path for a given storage ID and data type.
        
        Args:
            storage_id: Storage identifier
            data_type: Type of data (attributes, raw_responses, lineage)
            
        Returns:
            Path: File path if found, None otherwise
        """
        try:
            # Parse storage ID to extract item_id
            parts = storage_id.split('/')
            if len(parts) < 2:
                return None
            
            item_id = parts[0]
            data_type_from_id = parts[1]
            
            # Verify data type matches
            if data_type_from_id != data_type:
                return None
            
            # Look for the most recent file in the data type directory
            data_dir = self.storage_root / item_id / data_type
            if not data_dir.exists():
                return None
            
            # Find the most recent file
            files = list(data_dir.glob('*.json'))
            if not files:
                return None
            
            # Sort by modification time and return the most recent
            files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
            return files[0]
            
        except Exception:
            return None
    
    def _get_dir_creation_time(self, dir_path: Path) -> datetime:
        """Get the creation time of a directory.
        
        Args:
            dir_path: Path to the directory
            
        Returns:
            datetime: Creation time
        """
        try:
            stat = dir_path.stat()
            return datetime.fromtimestamp(stat.st_ctime)
        except Exception:
            return datetime.now()
    
    def _count_files_in_dir(self, dir_path: Path) -> int:
        """Count the number of files in a directory recursively.
        
        Args:
            dir_path: Path to the directory
            
        Returns:
            int: Number of files
        """
        try:
            return sum(1 for f in dir_path.rglob('*') if f.is_file())
        except Exception:
            return 0
    
    def _create_backup(self, path: Path) -> None:
        """Create a backup of a file or directory.
        
        Args:
            path: Path to backup
        """
        try:
            backup_dir = self.storage_root / 'backups'
            backup_dir.mkdir(exist_ok=True)
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_path = backup_dir / f"{path.name}_{timestamp}"
            
            if path.is_file():
                shutil.copy2(path, backup_path)
            elif path.is_dir():
                shutil.copytree(path, backup_path)
                
        except Exception:
            # Backup creation is optional, don't raise errors
            pass
