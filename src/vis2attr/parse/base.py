"""Base parsing interface for extracting structured data from VLM responses."""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from ..core.schemas import VLMRaw, Attributes
from ..core.exceptions import ProcessingError


class ParseError(ProcessingError):
    """Raised when parsing fails."""
    pass


class Parser(ABC):
    """Abstract base class for response parsers.
    
    Parsers convert raw VLM responses into structured Attributes objects.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize the parser with optional configuration.
        
        Args:
            config: Parser-specific configuration dictionary
        """
        self.config = config or {}
    
    @abstractmethod
    def parse(self, raw_response: VLMRaw, schema: Dict[str, Any]) -> Attributes:
        """Parse a raw VLM response into structured attributes.
        
        Args:
            raw_response: Raw response from VLM provider
            schema: Schema definition for attribute extraction
            
        Returns:
            Attributes: Structured attributes with data, confidences, and metadata
            
        Raises:
            ParseError: If parsing fails
        """
        pass
    
    @abstractmethod
    def can_parse(self, raw_response: VLMRaw) -> bool:
        """Check if this parser can handle the given response.
        
        Args:
            raw_response: Raw response to check
            
        Returns:
            bool: True if this parser can handle the response
        """
        pass
    
    def _extract_confidence(self, field_data: Any, default: float = 0.0) -> float:
        """Extract confidence score from field data.
        
        Args:
            field_data: Field data that may contain confidence
            default: Default confidence if not found
            
        Returns:
            float: Raw confidence score (will be normalized by caller)
        """
        if isinstance(field_data, dict) and 'confidence' in field_data:
            conf = field_data['confidence']
            if isinstance(conf, (int, float)):
                return float(conf)
        return default
    
    def _extract_value(self, field_data: Any) -> Any:
        """Extract value from field data.
        clear
        Args:
            field_data: Field data that may contain value
            
        Returns:
            Any: The extracted value
        """
        if isinstance(field_data, dict) and 'value' in field_data:
            return field_data['value']
        return field_data
    
    def _normalize_confidence(self, confidence: float) -> float:
        """Normalize confidence score to 0.0-1.0 range.
        
        Args:
            confidence: Raw confidence score
            
        Returns:
            float: Normalized confidence between 0.0 and 1.0
        """
        return max(0.0, min(1.0, float(confidence)))
