"""Parsing service for integrating with the main vis2attr pipeline."""

from typing import Dict, Any, Optional
from .factory import ParserFactory, create_parser_factory
from .base import ParseError
from ..core.schemas import VLMRaw, Attributes


class ParseService:
    """Service for parsing VLM responses into structured attributes."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize the parsing service.
        
        Args:
            config: Configuration dictionary for parsers
        """
        self.config = config or {}
        self.factory = create_parser_factory(self.config)
    
    def parse_response(self, raw_response: VLMRaw, schema: Dict[str, Any]) -> Attributes:
        """Parse a VLM response into structured attributes.
        
        Args:
            raw_response: Raw response from VLM provider
            schema: Schema definition for attribute extraction
            
        Returns:
            Attributes: Structured attributes with data, confidences, and metadata
            
        Raises:
            ParseError: If parsing fails
        """
        try:
            return self.factory.parse_response(raw_response, schema)
        except Exception as e:
            raise ParseError(
                f"Failed to parse response: {e}",
                context={
                    "provider": raw_response.provider,
                    "model": raw_response.model,
                    "content_length": len(raw_response.content) if raw_response.content else 0
                },
                recovery_hint="Check response format and schema compatibility"
            ) from e
    
    def parse_with_specific_parser(self, raw_response: VLMRaw, schema: Dict[str, Any], parser_name: str) -> Attributes:
        """Parse response using a specific parser.
        
        Args:
            raw_response: Raw response from VLM provider
            schema: Schema definition for attribute extraction
            parser_name: Name of the parser to use ('json')
            
        Returns:
            Attributes: Structured attributes
            
        Raises:
            ParseError: If parsing fails or parser not found
        """
        parser = self.factory.get_parser_by_name(parser_name)
        if not parser:
            raise ParseError(f"Parser '{parser_name}' not found")
        
        # Check if parser can handle the response
        if not parser.can_parse(raw_response):
            raise ParseError(f"Parser '{parser_name}' cannot parse this response")
        
        return parser.parse(raw_response, schema)
    
    def get_available_parsers(self) -> list[str]:
        """Get list of available parsers.
        
        Returns:
            List of parser names
        """
        return self.factory.list_available_parsers()
    
    def validate_schema(self, schema: Dict[str, Any]) -> bool:
        """Validate that a schema is compatible with the parsing system.
        
        Args:
            schema: Schema to validate
            
        Returns:
            bool: True if schema is valid
        """
        try:
            # Check that schema has the expected structure
            if not isinstance(schema, dict):
                return False
            
            for field_name, field_def in schema.items():
                if not isinstance(field_name, str):
                    return False
                
                # Field definition should be either a dict with 'value' key or a list
                if isinstance(field_def, dict):
                    if 'value' not in field_def:
                        return False
                elif isinstance(field_def, list):
                    # Array field - should be list of field definitions
                    if field_def and not isinstance(field_def[0], dict):
                        return False
                else:
                    return False
            
            return True
            
        except Exception:
            return False
    
    def get_parser_info(self, raw_response: VLMRaw) -> Dict[str, Any]:
        """Get information about which parsers can handle a response.
        
        Args:
            raw_response: Raw response to analyze
            
        Returns:
            Dictionary with parser information
        """
        info = {
            'can_parse': [],
            'recommended_parser': None,
            'response_preview': raw_response.content[:200] + '...' if len(raw_response.content) > 200 else raw_response.content
        }
        
        for parser_name in self.get_available_parsers():
            parser = self.factory.get_parser_by_name(parser_name)
            if parser and parser.can_parse(raw_response):
                info['can_parse'].append(parser_name)
        
        # Recommend the first available parser
        if info['can_parse']:
            info['recommended_parser'] = info['can_parse'][0]
        
        return info
