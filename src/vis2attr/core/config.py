"""Configuration management for the vis2attr pipeline."""

import yaml
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass


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
    
    @classmethod
    def from_file(cls, config_path: str) -> "Config":
        """Load configuration from a YAML file."""
        config_path = Path(config_path)
        
        if not config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_path}")
        
        with open(config_path, 'r') as f:
            config_data = yaml.safe_load(f)
        
        return cls(**config_data)
    
    def get_provider_config(self, provider_name: str) -> Dict[str, Any]:
        """Get configuration for a specific provider."""
        return self.providers.get(provider_name, {})
    
    def get_threshold(self, field_name: str) -> float:
        """Get confidence threshold for a specific field."""
        return self.thresholds.get(field_name, self.thresholds.get('default', 0.75))
