"""Lightweight Parquet-based storage backend for attributes and lineage data."""

import pandas as pd
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime
import json

from .base import StorageBackend, StorageError
from ..core.schemas import Attributes, VLMRaw
from ..core.config import ConfigWrapper


class ParquetStorage(StorageBackend):
    """Lightweight Parquet-based storage backend.
    
    Stores all data in a single Parquet file with columns:
    - item_id: str
    - data_type: str (attributes, raw_response, lineage)
    - timestamp: datetime
    - data: str (JSON serialized data)
    - metadata: str (JSON serialized metadata)
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize Parquet storage backend.
        
        Args:
            config: Configuration dictionary with keys:
                - file_path: Path to Parquet file (default: ./storage.parquet)
                - create_dirs: Whether to create directories if they don't exist (default: True)
        """
        super().__init__(config)
        config_wrapper = ConfigWrapper(self.config)
        self.file_path = Path(config_wrapper.get('file_path', './storage.parquet'))
        self.create_dirs = config_wrapper.get_bool('create_dirs', True)
        
        if self.create_dirs:
            self.file_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Initialize empty DataFrame if file doesn't exist
        if not self.file_path.exists():
            self._init_empty_storage()
    
    def _init_empty_storage(self):
        """Initialize empty Parquet storage file."""
        empty_df = pd.DataFrame(columns=[
            'item_id', 'data_type', 'timestamp', 'data', 'metadata'
        ])
        empty_df.to_parquet(self.file_path, index=False)
    
    def _load_dataframe(self) -> pd.DataFrame:
        """Load data from Parquet file."""
        try:
            return pd.read_parquet(self.file_path)
        except Exception as e:
            raise StorageError(f"Failed to load Parquet file: {str(e)}")
    
    def _save_dataframe(self, df: pd.DataFrame):
        """Save DataFrame to Parquet file."""
        try:
            df.to_parquet(self.file_path, index=False)
        except Exception as e:
            raise StorageError(f"Failed to save Parquet file: {str(e)}")
    
    def store_attributes(self, item_id: str, attributes: Attributes, 
                        metadata: Optional[Dict[str, Any]] = None) -> str:
        """Store structured attributes for an item."""
        self._validate_item_id(item_id)
        
        try:
            df = self._load_dataframe()
            
            # Prepare data for storage
            data = {
                'data': attributes.data,
                'confidences': attributes.confidences,
                'tags': list(attributes.tags) if attributes.tags else [],
                'notes': attributes.notes,
                'lineage': attributes.lineage or {}
            }
            
            # Create new row
            new_row = pd.DataFrame([{
                'item_id': item_id,
                'data_type': 'attributes',
                'timestamp': datetime.now().isoformat(),
                'data': json.dumps(data),
                'metadata': json.dumps(metadata or {})
            }])
            
            # Append and save
            df = pd.concat([df, new_row], ignore_index=True)
            self._save_dataframe(df)
            
            return f"{item_id}/attributes/{datetime.now().isoformat()}"
            
        except Exception as e:
            raise StorageError(
                f"Failed to store attributes for item {item_id}: {str(e)}",
                context={"item_id": item_id, "operation": "store_attributes"}
            ) from e
    
    def store_raw_response(self, item_id: str, raw_response: VLMRaw,
                          metadata: Optional[Dict[str, Any]] = None) -> str:
        """Store raw VLM response for an item."""
        self._validate_item_id(item_id)
        
        try:
            df = self._load_dataframe()
            
            # Prepare data for storage
            data = {
                'content': raw_response.content,
                'usage': raw_response.usage,
                'latency_ms': raw_response.latency_ms,
                'provider': raw_response.provider,
                'model': raw_response.model,
                'timestamp': raw_response.timestamp.isoformat() if raw_response.timestamp else None
            }
            
            # Create new row
            new_row = pd.DataFrame([{
                'item_id': item_id,
                'data_type': 'raw_response',
                'timestamp': datetime.now().isoformat(),
                'data': json.dumps(data),
                'metadata': json.dumps(metadata or {})
            }])
            
            # Append and save
            df = pd.concat([df, new_row], ignore_index=True)
            self._save_dataframe(df)
            
            return f"{item_id}/raw_response/{datetime.now().isoformat()}"
            
        except Exception as e:
            raise StorageError(
                f"Failed to store raw response for item {item_id}: {str(e)}",
                context={"item_id": item_id, "operation": "store_raw_response"}
            ) from e
    
    def store_lineage(self, item_id: str, lineage: Dict[str, Any],
                     metadata: Optional[Dict[str, Any]] = None) -> str:
        """Store processing lineage for an item."""
        self._validate_item_id(item_id)
        
        try:
            df = self._load_dataframe()
            
            # Create new row
            new_row = pd.DataFrame([{
                'item_id': item_id,
                'data_type': 'lineage',
                'timestamp': datetime.now().isoformat(),
                'data': json.dumps(lineage),
                'metadata': json.dumps(metadata or {})
            }])
            
            # Append and save
            df = pd.concat([df, new_row], ignore_index=True)
            self._save_dataframe(df)
            
            return f"{item_id}/lineage/{datetime.now().isoformat()}"
            
        except Exception as e:
            raise StorageError(
                f"Failed to store lineage for item {item_id}: {str(e)}",
                context={"item_id": item_id, "operation": "store_lineage"}
            ) from e
    
    def retrieve_attributes(self, storage_id: str) -> Optional[Attributes]:
        """Retrieve stored attributes by storage ID."""
        try:
            df = self._load_dataframe()
            
            # Parse storage ID to get item_id
            parts = storage_id.split('/')
            if len(parts) < 2:
                return None
            
            item_id = parts[0]
            
            # Find most recent attributes for this item
            attr_rows = df[(df['item_id'] == item_id) & (df['data_type'] == 'attributes')]
            if attr_rows.empty:
                return None
            
            # Get the most recent one
            latest_row = attr_rows.sort_values('timestamp').iloc[-1]
            data = json.loads(latest_row['data'])
            
            return Attributes(
                data=data['data'],
                confidences=data['confidences'],
                tags=set(data.get('tags', [])),
                notes=data.get('notes', ''),
                lineage=data.get('lineage', {})
            )
            
        except Exception as e:
            raise StorageError(f"Failed to retrieve attributes for storage ID {storage_id}: {str(e)}")
    
    def retrieve_raw_response(self, storage_id: str) -> Optional[VLMRaw]:
        """Retrieve stored raw response by storage ID."""
        try:
            df = self._load_dataframe()
            
            # Parse storage ID to get item_id
            parts = storage_id.split('/')
            if len(parts) < 2:
                return None
            
            item_id = parts[0]
            
            # Find most recent raw response for this item
            resp_rows = df[(df['item_id'] == item_id) & (df['data_type'] == 'raw_response')]
            if resp_rows.empty:
                return None
            
            # Get the most recent one
            latest_row = resp_rows.sort_values('timestamp').iloc[-1]
            data = json.loads(latest_row['data'])
            
            return VLMRaw(
                content=data['content'],
                usage=data['usage'],
                latency_ms=data['latency_ms'],
                provider=data['provider'],
                model=data['model'],
                timestamp=datetime.fromisoformat(data['timestamp']) if data['timestamp'] else None
            )
            
        except Exception as e:
            raise StorageError(f"Failed to retrieve raw response for storage ID {storage_id}: {str(e)}")
    
    def retrieve_lineage(self, storage_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve stored lineage by storage ID."""
        try:
            df = self._load_dataframe()
            
            # Parse storage ID to get item_id
            parts = storage_id.split('/')
            if len(parts) < 2:
                return None
            
            item_id = parts[0]
            
            # Find most recent lineage for this item
            lineage_rows = df[(df['item_id'] == item_id) & (df['data_type'] == 'lineage')]
            if lineage_rows.empty:
                return None
            
            # Get the most recent one
            latest_row = lineage_rows.sort_values('timestamp').iloc[-1]
            return json.loads(latest_row['data'])
            
        except Exception as e:
            raise StorageError(f"Failed to retrieve lineage for storage ID {storage_id}: {str(e)}")
    
    def list_items(self, limit: Optional[int] = None, 
                  offset: Optional[int] = None) -> List[Dict[str, Any]]:
        """List stored items with metadata."""
        try:
            df = self._load_dataframe()
            
            if df.empty:
                return []
            
            # Get unique items with their metadata
            items = []
            for item_id in df['item_id'].unique():
                item_rows = df[df['item_id'] == item_id]
                
                # Get creation time (earliest timestamp)
                created_at = item_rows['timestamp'].min()
                
                # Check what data types exist
                data_types = set(item_rows['data_type'].unique())
                
                item_metadata = {
                    'item_id': item_id,
                    'created_at': created_at,
                    'has_attributes': 'attributes' in data_types,
                    'has_raw_response': 'raw_response' in data_types,
                    'has_lineage': 'lineage' in data_types,
                    'record_count': len(item_rows)
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
        """Delete all data for an item."""
        self._validate_item_id(item_id)
        
        try:
            df = self._load_dataframe()
            
            # Check if item exists
            if item_id not in df['item_id'].values:
                return False
            
            # Remove all rows for this item
            df = df[df['item_id'] != item_id]
            self._save_dataframe(df)
            
            return True
            
        except Exception as e:
            raise StorageError(f"Failed to delete item {item_id}: {str(e)}")
    
    def get_all_data(self) -> pd.DataFrame:
        """Get all stored data as a DataFrame for analysis.
        
        Returns:
            pd.DataFrame: All stored data
        """
        return self._load_dataframe()
    
    def query_by_item_id(self, item_id: str) -> pd.DataFrame:
        """Query all data for a specific item.
        
        Args:
            item_id: Item identifier
            
        Returns:
            pd.DataFrame: All data for the item
        """
        df = self._load_dataframe()
        return df[df['item_id'] == item_id]
    
    def query_by_data_type(self, data_type: str) -> pd.DataFrame:
        """Query all data of a specific type.
        
        Args:
            data_type: Type of data (attributes, raw_response, lineage)
            
        Returns:
            pd.DataFrame: All data of the specified type
        """
        df = self._load_dataframe()
        return df[df['data_type'] == data_type]
