"""Configuration management for the vis2attr pipeline."""

import os
import yaml
from pathlib import Path
from typing import Dict, Any, Optional, TypeVar, Union
from dataclasses import dataclass
from dotenv import load_dotenv

from .constants import DEFAULT_CONFIDENCE_THRESHOLD

T = TypeVar('T')


@dataclass
class Config:
    """Configuration container for the vis2attr pipeline."""
    
    # Pipeline components
    ingestor: str
    provider: str
    storage: str
    
    # Schema and prompts
    schema_path: str
    prompt_template: str
    
    # Thresholds
    thresholds: Dict[str, float]
    
    # I/O settings
    io: Dict[str, Any]
    
    # Provider settings
    providers: Dict[str, Dict[str, Any]]
    
    # Metrics and logging
    metrics: Dict[str, Any]
    
    # Security settings
    security: Dict[str, Any]
    
    # Storage settings
    storage_config: Optional[Dict[str, Any]] = None
    
    @classmethod
    def from_file(cls, config_path: str) -> "Config":
        """Load configuration from a YAML file."""
        config_path = Path(config_path)
        
        if not config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_path}")
        
        with open(config_path, 'r') as f:
            config_data = yaml.safe_load(f)
        
        config = cls(**config_data)
        config._load_environment()
        return config
    
    def _load_environment(self) -> None:
        """Load environment variables from .env file."""
        # Find project root by looking for pyproject.toml
        current = Path(__file__).parent
        while current != current.parent:
            if (current / 'pyproject.toml').exists():
                project_root = current
                break
            current = current.parent
        else:
            # Fallback to relative path
            project_root = Path(__file__).parent.parent.parent
        
        # Load .env file if it exists
        env_file = project_root / ".env"
        if env_file.exists():
            load_dotenv(env_file)
    
    def get_env_key(self, key: str, required: bool = True) -> str:
        """Get environment variable with optional requirement check.
        
        Args:
            key: Environment variable name
            required: Whether the key is required (raises error if missing)
            
        Returns:
            Environment variable value
            
        Raises:
            ValueError: If required key is not found
        """
        value = os.getenv(key)
        if required and not value:
            raise ValueError(f"Required environment variable not set: {key}")
        return value or ""
    
    def get_provider_config(self, provider_name: str) -> Dict[str, Any]:
        """Get configuration for a specific provider."""
        return self.providers.get(provider_name, {})
    
    def get_threshold(self, field_name: str) -> float:
        """Get confidence threshold for a specific field."""
        return self.thresholds.get(field_name, self.thresholds.get('default', DEFAULT_CONFIDENCE_THRESHOLD))
    
    def get_storage_config(self) -> Dict[str, Any]:
        """Get storage configuration."""
        return self.storage_config or {}


class ConfigWrapper:
    """Lightweight configuration wrapper with typed access and defaults."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize with configuration dictionary.
        
        Args:
            config: Configuration dictionary
        """
        self._config = config
    
    def get(self, key: str, default: T = None) -> T:
        """Get configuration value with type-safe default.
        
        Args:
            key: Configuration key (supports dot notation for nested access)
            default: Default value to return if key not found
            
        Returns:
            Configuration value or default
        """
        return self._get_nested_value(key, default)
    
    def get_bool(self, key: str, default: bool = False) -> bool:
        """Get boolean configuration value.
        
        Args:
            key: Configuration key
            default: Default boolean value
            
        Returns:
            Boolean configuration value
        """
        value = self._get_nested_value(key, default)
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.lower() in ('true', '1', 'yes', 'on')
        return bool(value)
    
    def get_int(self, key: str, default: int = 0) -> int:
        """Get integer configuration value.
        
        Args:
            key: Configuration key
            default: Default integer value
            
        Returns:
            Integer configuration value
        """
        value = self._get_nested_value(key, default)
        if isinstance(value, int):
            return value
        if isinstance(value, str) and value.isdigit():
            return int(value)
        return default
    
    def get_list(self, key: str, default: list = None) -> list:
        """Get list configuration value.
        
        Args:
            key: Configuration key
            default: Default list value
            
        Returns:
            List configuration value
        """
        if default is None:
            default = []
        value = self._get_nested_value(key, default)
        if isinstance(value, list):
            return value
        return default
    
    def _get_nested_value(self, key: str, default: T) -> T:
        """Get nested configuration value using dot notation.
        
        Args:
            key: Configuration key (supports dot notation)
            default: Default value
            
        Returns:
            Configuration value or default
        """
        keys = key.split('.')
        value = self._config
        
        try:
            for k in keys:
                value = value[k]
            return value
        except (KeyError, TypeError):
            return default
