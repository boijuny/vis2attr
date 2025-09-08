"""Factory for creating storage backends."""

from typing import Dict, Any, Optional, Type
from .base import StorageBackend
from .files import FileStorage


class StorageFactory:
    """Factory for creating storage backends based on configuration."""
    
    _backends: Dict[str, Type[StorageBackend]] = {
        'files': FileStorage,
        'file': FileStorage,  # Alias
        'local': FileStorage,  # Alias
    }
    
    @classmethod
    def create_backend(cls, backend_type: str, config: Optional[Dict[str, Any]] = None) -> StorageBackend:
        """Create a storage backend instance.
        
        Args:
            backend_type: Type of storage backend ('files', 'file', 'local')
            config: Backend-specific configuration
            
        Returns:
            StorageBackend: Configured storage backend instance
            
        Raises:
            ValueError: If backend type is not supported
        """
        if backend_type not in cls._backends:
            available = ', '.join(cls._backends.keys())
            raise ValueError(f"Unsupported storage backend: {backend_type}. Available: {available}")
        
        backend_class = cls._backends[backend_type]
        return backend_class(config or {})
    
    @classmethod
    def register_backend(cls, name: str, backend_class: Type[StorageBackend]) -> None:
        """Register a new storage backend.
        
        Args:
            name: Name to register the backend under
            backend_class: Backend class to register
        """
        cls._backends[name] = backend_class
    
    @classmethod
    def list_backends(cls) -> list[str]:
        """List available storage backends.
        
        Returns:
            list[str]: List of available backend names
        """
        return list(cls._backends.keys())
    
    @classmethod
    def get_backend_info(cls, backend_type: str) -> Dict[str, Any]:
        """Get information about a storage backend.
        
        Args:
            backend_type: Type of storage backend
            
        Returns:
            Dict[str, Any]: Backend information including class and docstring
            
        Raises:
            ValueError: If backend type is not supported
        """
        if backend_type not in cls._backends:
            available = ', '.join(cls._backends.keys())
            raise ValueError(f"Unsupported storage backend: {backend_type}. Available: {available}")
        
        backend_class = cls._backends[backend_type]
        return {
            'name': backend_type,
            'class': backend_class.__name__,
            'module': backend_class.__module__,
            'docstring': backend_class.__doc__,
            'config_schema': getattr(backend_class, 'config_schema', None)
        }
