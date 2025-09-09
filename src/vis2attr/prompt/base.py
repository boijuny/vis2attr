"""Base prompt building interface."""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Union
from ..core.schemas import Item, VLMRequest
from ..core.constants import DEFAULT_MAX_TOKENS, DEFAULT_TEMPERATURE


class PromptBuilder(ABC):
    """Abstract base class for prompt builders.
    
    Converts Items and schemas into VLMRequests using templates.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize the prompt builder with configuration.
        
        Args:
            config: Configuration dictionary containing template paths, etc.
        """
        self.config = config
    
    @abstractmethod
    def build_request(
        self, 
        item: Item, 
        schema: Dict[str, Any], 
        model: str,
        max_tokens: int = DEFAULT_MAX_TOKENS,
        temperature: float = DEFAULT_TEMPERATURE
    ) -> VLMRequest:
        """Build a VLM request from an item and schema.
        
        Args:
            item: Item containing images and metadata
            schema: Schema definition for attribute extraction
            model: VLM model to use
            max_tokens: Maximum tokens for the response
            temperature: Temperature for generation
            
        Returns:
            VLMRequest ready to send to VLM provider
        """
        pass
    
    @abstractmethod
    def load_schema(self, schema_path: str) -> Dict[str, Any]:
        """Load schema from file.
        
        Args:
            schema_path: Path to schema file
            
        Returns:
            Schema dictionary
        """
        pass
    
    @abstractmethod
    def get_schema_fields(self, schema: Dict[str, Any]) -> List[str]:
        """Get list of field names from schema.
        
        Args:
            schema: Schema dictionary
            
        Returns:
            List of field names
        """
        pass
