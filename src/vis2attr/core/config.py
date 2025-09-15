"""Configuration management for the vis2attr pipeline."""

import os
import yaml
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass
from dotenv import load_dotenv

from .constants import DEFAULT_CONFIDENCE_THRESHOLD


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
