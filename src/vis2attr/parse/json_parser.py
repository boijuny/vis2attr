"""JSON parser for structured VLM responses."""

import json
import re
from typing import Dict, Any, List, Optional
from .base import Parser, ParseError
from ..core.schemas import VLMRaw, Attributes
from ..core.config import ConfigWrapper


class JSONParser(Parser):
    """Parser for JSON-formatted VLM responses."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize JSON parser.
        
        Args:
            config: Configuration dictionary with options:
                - strict_json: If True, only accept pure JSON (default: False)
                - extract_from_markdown: If True, extract JSON from markdown code blocks (default: True)
                - fallback_to_text: If True, try to extract structured data from text (default: False)
        """
        super().__init__(config)
        config_wrapper = ConfigWrapper(self.config)
        self.strict_json = config_wrapper.get_bool('strict_json', False)
        self.extract_from_markdown = config_wrapper.get_bool('extract_from_markdown', True)
        self.fallback_to_text = config_wrapper.get_bool('fallback_to_text', False)
    
    def can_parse(self, raw_response: VLMRaw) -> bool:
        """Check if response can be parsed as JSON.
        
        Args:
            raw_response: Raw response to check
            
        Returns:
            bool: True if response appears to contain JSON
        """
        content = raw_response.content.strip()
        
        # Check for pure JSON
        if self._is_pure_json(content):
            return True
        
        # Check for JSON in markdown code blocks
        if self.extract_from_markdown and self._has_json_in_markdown(content):
            return True
        
        return False
    
    def parse(self, raw_response: VLMRaw, schema: Dict[str, Any]) -> Attributes:
        """Parse JSON response into structured attributes.
        
        Args:
            raw_response: Raw response from VLM provider
            schema: Schema definition for attribute extraction
            
        Returns:
            Attributes: Structured attributes
            
        Raises:
            ParseError: If parsing fails
        """
        try:
            # Extract JSON from response
            json_data = self._extract_json(raw_response.content)
            
            # Parse the JSON
            parsed_data = json.loads(json_data)
            
            # Convert to Attributes format
            return self._convert_to_attributes(parsed_data, schema, raw_response)
            
        except json.JSONDecodeError as e:
            raise ParseError(f"Failed to parse JSON: {e}")
        except Exception as e:
            raise ParseError(f"Unexpected error during JSON parsing: {e}")
    
    def _is_pure_json(self, content: str) -> bool:
        """Check if content is pure JSON.
        
        Args:
            content: Content to check
            
        Returns:
            bool: True if content is valid JSON
        """
        try:
            json.loads(content)
            return True
        except json.JSONDecodeError:
            return False
    
    def _has_json_in_markdown(self, content: str) -> bool:
        """Check if content contains JSON in markdown code blocks.
        
        Args:
            content: Content to check
            
        Returns:
            bool: True if JSON found in markdown
        """
        # Look for JSON in code blocks
        json_pattern = r'```(?:json)?\s*(\{.*?\})\s*```'
        matches = re.findall(json_pattern, content, re.DOTALL)
        
        for match in matches:
            if self._is_pure_json(match):
                return True
        
        return False
    
    def _extract_json(self, content: str) -> str:
        """Extract JSON from response content.
        
        Args:
            content: Raw response content
            
        Returns:
            str: Extracted JSON string
            
        Raises:
            ParseError: If no valid JSON found
        """
        content = content.strip()
        
        # Try pure JSON first
        if self._is_pure_json(content):
            return content
        
        # Try extracting from markdown code blocks
        if self.extract_from_markdown:
            json_pattern = r'```(?:json)?\s*(\{.*?\})\s*```'
            matches = re.findall(json_pattern, content, re.DOTALL)
            
            for match in matches:
                if self._is_pure_json(match):
                    return match
        
        # Try to find JSON object in text - improved pattern
        json_pattern = r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}'
        matches = re.findall(json_pattern, content, re.DOTALL)
        
        for match in matches:
            if self._is_pure_json(match):
                return match
        
        # Try to clean JSON by removing comments and extra whitespace
        cleaned_json = self._clean_json_content(content)
        if cleaned_json and self._is_pure_json(cleaned_json):
            return cleaned_json
        
        # Last resort: try to extract JSON with a more permissive approach
        # Look for JSON-like structure even with comments
        json_like_pattern = r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}'
        matches = re.findall(json_like_pattern, content, re.DOTALL)
        
        for match in matches:
            # Try to clean this match
            cleaned = self._clean_json_content(match)
            if cleaned and self._is_pure_json(cleaned):
                return cleaned
        
        raise ParseError("No valid JSON found in response")
    
    def _clean_json_content(self, content: str) -> str:
        """Clean JSON content by removing comments and normalizing whitespace.
        
        Args:
            content: Raw content that may contain JSON with comments
            
        Returns:
            str: Cleaned JSON string or empty string if no JSON found
        """
        # Find JSON object boundaries
        start_idx = content.find('{')
        if start_idx == -1:
            return ""
        
        # Find matching closing brace
        brace_count = 0
        end_idx = start_idx
        for i, char in enumerate(content[start_idx:], start_idx):
            if char == '{':
                brace_count += 1
            elif char == '}':
                brace_count -= 1
                if brace_count == 0:
                    end_idx = i + 1
                    break
        
        if brace_count != 0:
            return ""
        
        json_str = content[start_idx:end_idx]
        
        # Simple approach: remove comments using regex
        # Remove single-line comments (// ...)
        json_str = re.sub(r'//.*$', '', json_str, flags=re.MULTILINE)
        
        # Remove multi-line comments (/* ... */)
        json_str = re.sub(r'/\*.*?\*/', '', json_str, flags=re.DOTALL)
        
        # Remove hash comments (# ...)
        json_str = re.sub(r'#.*$', '', json_str, flags=re.MULTILINE)
        
        # Clean up extra whitespace but preserve structure
        json_str = re.sub(r'\s+', ' ', json_str)
        json_str = json_str.strip()
        
        return json_str
    
    def _convert_to_attributes(self, data: Dict[str, Any], schema: Dict[str, Any], raw_response: VLMRaw) -> Attributes:
        """Convert parsed JSON data to Attributes object.
        
        Args:
            data: Parsed JSON data
            schema: Schema definition
            raw_response: Original raw response for metadata
            
        Returns:
            Attributes: Structured attributes
        """
        attributes_data = {}
        confidences = {}
        tags = set()
        notes = ""
        
        # Process each field in the schema
        for field_name, field_schema in schema.items():
            if field_name in data:
                field_data = data[field_name]
                
                # Handle different field types
                if isinstance(field_schema, dict) and 'value' in field_schema:
                    # Simple field with value and confidence
                    value = self._extract_value(field_data)
                    confidence = self._extract_confidence(field_data)
                    
                    attributes_data[field_name] = value
                    confidences[field_name] = self._normalize_confidence(confidence)
                    
                elif isinstance(field_schema, list) and field_schema:
                    # Array field (like primary_colors, materials)
                    if isinstance(field_data, list):
                        processed_items = []
                        for item in field_data:
                            if isinstance(item, dict):
                                processed_item = {
                                    'name': self._extract_value(item.get('name', '')),
                                    'confidence': self._normalize_confidence(
                                        self._extract_confidence(item)
                                    )
                                }
                            else:
                                processed_item = {
                                    'name': str(item),
                                    'confidence': 0.5  # Default confidence for simple values
                                }
                            processed_items.append(processed_item)
                        
                        attributes_data[field_name] = processed_items
                        # Use average confidence for array fields
                        if processed_items:
                            avg_confidence = sum(item['confidence'] for item in processed_items) / len(processed_items)
                            confidences[field_name] = self._normalize_confidence(avg_confidence)
                        else:
                            confidences[field_name] = 0.0
                    else:
                        attributes_data[field_name] = []
                        confidences[field_name] = 0.0
                else:
                    # Direct value field
                    attributes_data[field_name] = field_data
                    confidences[field_name] = 0.5  # Default confidence
        
        # Extract notes if present
        if 'notes' in data:
            notes = str(data['notes'])
        
        # Add quality tags based on confidence scores
        avg_confidence = sum(confidences.values()) / len(confidences) if confidences else 0.0
        if avg_confidence > 0.8:
            tags.add('high_confidence')
        elif avg_confidence > 0.5:
            tags.add('medium_confidence')
        else:
            tags.add('low_confidence')
        
        # Add parsing metadata to lineage
        lineage = {
            'parser': 'json',
            'provider': raw_response.provider,
            'model': raw_response.model,
            'timestamp': raw_response.timestamp.isoformat(),
            'latency_ms': raw_response.latency_ms
        }
        
        return Attributes(
            data=attributes_data,
            confidences=confidences,
            tags=tags,
            notes=notes,
            lineage=lineage
        )
