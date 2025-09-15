"""Parser factory for creating appropriate parsers based on response content."""

from typing import Dict, Any, List, Optional, Type
from .base import Parser, ParseError
from .json_parser import JSONParser
from ..core.schemas import VLMRaw
from ..core.config import ConfigWrapper


class ParserFactory:
    """Factory for creating parsers based on response content."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize parser factory.
        
        Args:
            config: Configuration dictionary with parser settings
        """
        self.config = config or {}
        self._parsers: List[Parser] = []
        self._register_default_parsers()
    
    def _register_default_parsers(self) -> None:
        """Register default parsers in order of preference."""
        # JSON parser (only parser for structured output)
        config_wrapper = ConfigWrapper(self.config)
        json_config = config_wrapper.get('json_parser', {})
        self._parsers.append(JSONParser(json_config))
    
    def register_parser(self, parser: Parser, priority: int = 0) -> None:
        """Register a custom parser.
        
        Args:
            parser: Parser instance to register
            priority: Priority for parser selection (higher = more preferred)
        """
        # Insert at the appropriate position based on priority
        insert_index = 0
        for i, existing_parser in enumerate(self._parsers):
            # Simple priority system - custom parsers with priority > 0 go first
            if priority > 0:
                insert_index = i
                break
            insert_index = i + 1
        
        self._parsers.insert(insert_index, parser)
    
    def get_parser(self, raw_response: VLMRaw) -> Parser:
        """Get the best parser for the given response.
        
        Args:
            raw_response: Raw response to parse
            
        Returns:
            Parser: The most appropriate parser for the response
            
        Raises:
            ParseError: If no suitable parser is found
        """
        for parser in self._parsers:
            if parser.can_parse(raw_response):
                return parser
        
        raise ParseError("No suitable parser found for the response")
    
    def get_parser_by_name(self, name: str) -> Optional[Parser]:
        """Get a parser by name.
        
        Args:
            name: Name of the parser ('json')
            
        Returns:
            Parser: The requested parser, or None if not found
        """
        parser_map = {
            'json': JSONParser
        }
        
        parser_class = parser_map.get(name.lower())
        if parser_class:
            config_key = f"{name.lower()}_parser"
            config_wrapper = ConfigWrapper(self.config)
            config = config_wrapper.get(config_key, {})
            return parser_class(config)
        
        return None
    
    def list_available_parsers(self) -> List[str]:
        """List all available parser names.
        
        Returns:
            List of parser names
        """
        return ['json']
    
    def parse_response(self, raw_response: VLMRaw, schema: Dict[str, Any]) -> Any:
        """Parse a response using the most appropriate parser.
        
        Args:
            raw_response: Raw response to parse
            schema: Schema definition for attribute extraction
            
        Returns:
            Parsed attributes
            
        Raises:
            ParseError: If parsing fails
        """
        parser = self.get_parser(raw_response)
        return parser.parse(raw_response, schema)


# Convenience function for easy access
def create_parser_factory(config: Optional[Dict[str, Any]] = None) -> ParserFactory:
    """Create a parser factory with the given configuration.
    
    Args:
        config: Configuration dictionary
        
    Returns:
        ParserFactory: Configured parser factory
    """
    return ParserFactory(config)
