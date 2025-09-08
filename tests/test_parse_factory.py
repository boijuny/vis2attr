"""Tests for parser factory functionality."""

import pytest
from datetime import datetime, timezone
from src.vis2attr.parse.factory import ParserFactory, create_parser_factory
from src.vis2attr.parse.base import ParseError
from src.vis2attr.core.schemas import VLMRaw


@pytest.fixture
def sample_schema():
    """Sample schema for testing."""
    return {
        "brand": {"value": None, "confidence": 0.0},
        "model_or_type": {"value": None, "confidence": 0.0}
    }


@pytest.fixture
def json_response():
    """Sample JSON response."""
    return VLMRaw(
        content='{"brand": {"value": "Nike", "confidence": 0.9}}',
        usage={},
        latency_ms=0.0,
        provider="test",
        model="test"
    )




class TestParserFactory:
    """Test cases for ParserFactory."""
    
    def test_create_factory(self):
        """Test factory creation."""
        factory = ParserFactory()
        assert isinstance(factory, ParserFactory)
        assert len(factory._parsers) == 1  # Only JSON parser
    
    def test_create_factory_with_config(self):
        """Test factory creation with configuration."""
        config = {
            "json_parser": {"strict_json": True}
        }
        factory = ParserFactory(config)
        assert factory.config == config
    
    def test_get_parser_json_response(self, factory, json_response):
        """Test getting parser for JSON response."""
        parser = factory.get_parser(json_response)
        assert parser.__class__.__name__ == "JSONParser"
    
    
    def test_get_parser_by_name(self, factory):
        """Test getting parser by name."""
        json_parser = factory.get_parser_by_name("json")
        assert json_parser.__class__.__name__ == "JSONParser"
        
        unknown_parser = factory.get_parser_by_name("unknown")
        assert unknown_parser is None
    
    def test_list_available_parsers(self, factory):
        """Test listing available parsers."""
        parsers = factory.list_available_parsers()
        assert "json" in parsers
        assert len(parsers) == 1
    
    def test_parse_response_json(self, factory, json_response, sample_schema):
        """Test parsing JSON response through factory."""
        attributes = factory.parse_response(json_response, sample_schema)
        
        assert attributes.data["brand"] == "Nike"
        assert attributes.confidences["brand"] == 0.9
        assert attributes.lineage["parser"] == "json"
    
    
    def test_register_custom_parser(self, factory):
        """Test registering a custom parser."""
        from src.vis2attr.parse.json_parser import JSONParser
        
        custom_parser = JSONParser({"strict_json": True})
        factory.register_parser(custom_parser, priority=10)
        
        # Should be added to the parsers list
        assert len(factory._parsers) == 2
        assert custom_parser in factory._parsers
    
    def test_parse_response_failure(self, factory, sample_schema):
        """Test parsing failure handling."""
        # Create a response that no parser can handle
        invalid_response = VLMRaw(
            content="",  # Empty content
            usage={},
            latency_ms=0.0,
            provider="test",
            model="test"
        )
        
        # This should raise an error since no parser can handle empty content
        with pytest.raises(ParseError, match="No suitable parser found for the response"):
            factory.parse_response(invalid_response, sample_schema)


class TestCreateParserFactory:
    """Test cases for create_parser_factory function."""
    
    def test_create_without_config(self):
        """Test creating factory without configuration."""
        factory = create_parser_factory()
        assert isinstance(factory, ParserFactory)
    
    def test_create_with_config(self):
        """Test creating factory with configuration."""
        config = {"json_parser": {"strict_json": True}}
        factory = create_parser_factory(config)
        assert factory.config == config


@pytest.fixture
def factory():
    """Parser factory fixture."""
    return ParserFactory()
