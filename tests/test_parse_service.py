"""Tests for parse service functionality."""

import pytest
from datetime import datetime, timezone
from src.vis2attr.parse.service import ParseService
from src.vis2attr.parse.base import ParseError
from src.vis2attr.core.schemas import VLMRaw


@pytest.fixture
def sample_schema():
    """Sample schema for testing."""
    return {
        "brand": {"value": None, "confidence": 0.0},
        "model_or_type": {"value": None, "confidence": 0.0},
        "primary_colors": [{"name": "", "confidence": 0.0}],
        "condition": {"value": None, "confidence": 0.0}
    }


@pytest.fixture
def parse_service():
    """Parse service fixture."""
    return ParseService()


@pytest.fixture
def json_response():
    """Sample JSON response."""
    return VLMRaw(
        content='{"brand": {"value": "Nike", "confidence": 0.9}, "model_or_type": {"value": "Air Max 90", "confidence": 0.8}}',
        usage={"prompt_tokens": 100, "completion_tokens": 50},
        latency_ms=1200.0,
        provider="mistral",
        model="mistral-large-latest",
        timestamp=datetime.now(timezone.utc)
    )




class TestParseService:
    """Test cases for ParseService."""
    
    def test_parse_response_json(self, parse_service, json_response, sample_schema):
        """Test parsing JSON response."""
        attributes = parse_service.parse_response(json_response, sample_schema)
        
        assert attributes.data["brand"] == "Nike"
        assert attributes.data["model_or_type"] == "Air Max 90"
        assert attributes.confidences["brand"] == 0.9
        assert attributes.confidences["model_or_type"] == 0.8
        assert attributes.lineage["parser"] == "json"
        assert attributes.lineage["provider"] == "mistral"
    
    
    def test_parse_with_specific_parser_json(self, parse_service, json_response, sample_schema):
        """Test parsing with specific JSON parser."""
        attributes = parse_service.parse_with_specific_parser(json_response, sample_schema, "json")
        
        assert attributes.data["brand"] == "Nike"
        assert attributes.lineage["parser"] == "json"
    
    
    def test_parse_with_invalid_parser_name(self, parse_service, json_response, sample_schema):
        """Test parsing with invalid parser name raises error."""
        with pytest.raises(ParseError, match="Parser 'invalid' not found"):
            parse_service.parse_with_specific_parser(json_response, sample_schema, "invalid")
    
    def test_parse_with_parser_cannot_handle_response(self, parse_service, sample_schema):
        """Test parsing with parser that cannot handle response."""
        # Create a response that JSON parser cannot handle
        invalid_response = VLMRaw(
            content="This is not valid JSON content",
            usage={},
            latency_ms=0.0,
            provider="test",
            model="test"
        )
        
        # This should raise an error since JSON parser cannot handle non-JSON content
        with pytest.raises(ParseError, match="Parser 'json' cannot parse this response"):
            parse_service.parse_with_specific_parser(invalid_response, sample_schema, "json")
    
    def test_get_available_parsers(self, parse_service):
        """Test getting available parsers."""
        parsers = parse_service.get_available_parsers()
        assert "json" in parsers
        assert len(parsers) == 1
    
    def test_validate_schema_valid(self, parse_service, sample_schema):
        """Test validating valid schema."""
        assert parse_service.validate_schema(sample_schema)
    
    def test_validate_schema_invalid_not_dict(self, parse_service):
        """Test validating invalid schema (not a dict)."""
        assert not parse_service.validate_schema("not a dict")
    
    def test_validate_schema_invalid_field_structure(self, parse_service):
        """Test validating invalid schema (wrong field structure)."""
        invalid_schema = {
            "brand": "just a string",  # Should be dict with 'value' key
            "colors": "not a list"    # Should be list
        }
        assert not parse_service.validate_schema(invalid_schema)
    
    def test_validate_schema_valid_array_field(self, parse_service):
        """Test validating schema with valid array field."""
        valid_schema = {
            "brand": {"value": None, "confidence": 0.0},
            "colors": [{"name": "", "confidence": 0.0}]
        }
        assert parse_service.validate_schema(valid_schema)
    
    def test_get_parser_info_json(self, parse_service, json_response):
        """Test getting parser info for JSON response."""
        info = parse_service.get_parser_info(json_response)
        
        assert "can_parse" in info
        assert "recommended_parser" in info
        assert "response_preview" in info
        assert "json" in info["can_parse"]
        assert info["recommended_parser"] == "json"
        assert "Nike" in info["response_preview"]
    
    
    def test_parse_response_error_handling(self, parse_service, sample_schema):
        """Test error handling in parse_response."""
        # Create a response that will cause parsing to fail
        invalid_response = VLMRaw(
            content="",  # Empty content
            usage={},
            latency_ms=0.0,
            provider="test",
            model="test"
        )
        
        # Should raise error since no parser can handle empty content
        with pytest.raises(ParseError, match="Failed to parse response"):
            parse_service.parse_response(invalid_response, sample_schema)
    
    def test_service_with_custom_config(self):
        """Test service with custom configuration."""
        config = {
            "json_parser": {"strict_json": True}
        }
        service = ParseService(config)
        
        assert service.config == config
        assert service.factory.config == config
    
    def test_parse_complex_schema(self, parse_service, json_response):
        """Test parsing with complex schema including arrays."""
        complex_schema = {
            "brand": {"value": None, "confidence": 0.0},
            "model_or_type": {"value": None, "confidence": 0.0},
            "primary_colors": [{"name": "", "confidence": 0.0}],
            "materials": [{"name": "", "confidence": 0.0}],
            "condition": {"value": None, "confidence": 0.0},
            "notes": ""
        }
        
        complex_response = VLMRaw(
            content='''
            {
                "brand": {"value": "Nike", "confidence": 0.9},
                "primary_colors": [
                    {"name": "white", "confidence": 0.8},
                    {"name": "black", "confidence": 0.9}
                ],
                "materials": [
                    {"name": "leather", "confidence": 0.7}
                ],
                "notes": "Classic sneaker design"
            }
            ''',
            usage={},
            latency_ms=0.0,
            provider="test",
            model="test"
        )
        
        attributes = parse_service.parse_response(complex_response, complex_schema)
        
        assert attributes.data["brand"] == "Nike"
        assert len(attributes.data["primary_colors"]) == 2
        assert attributes.data["primary_colors"][0]["name"] == "white"
        assert len(attributes.data["materials"]) == 1
        assert attributes.data["materials"][0]["name"] == "leather"
        assert "Classic sneaker design" in attributes.notes
