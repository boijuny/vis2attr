"""Tests for JSON parser functionality."""

import pytest
from datetime import datetime, timezone
from src.vis2attr.parse.json_parser import JSONParser
from src.vis2attr.parse.base import ParseError
from src.vis2attr.core.schemas import VLMRaw


@pytest.fixture
def sample_schema():
    """Sample schema for testing."""
    return {
        "brand": {"value": None, "confidence": 0.0},
        "model_or_type": {"value": None, "confidence": 0.0},
        "primary_colors": [{"name": "", "confidence": 0.0}],
        "materials": [{"name": "", "confidence": 0.0}],
        "condition": {"value": None, "confidence": 0.0},
        "notes": ""
    }


@pytest.fixture
def sample_vlm_raw():
    """Sample VLM raw response."""
    return VLMRaw(
        content='{"brand": {"value": "Nike", "confidence": 0.9}, "model_or_type": {"value": "Air Max 90", "confidence": 0.8}}',
        usage={"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150},
        latency_ms=1200.0,
        provider="mistral",
        model="mistral-large-latest",
        timestamp=datetime.now(timezone.utc)
    )


@pytest.fixture
def json_parser():
    """JSON parser instance."""
    return JSONParser()


class TestJSONParser:
    """Test cases for JSONParser."""
    
    def test_can_parse_pure_json(self, json_parser, sample_vlm_raw):
        """Test that parser can handle pure JSON responses."""
        assert json_parser.can_parse(sample_vlm_raw)
    
    def test_can_parse_json_in_markdown(self, json_parser):
        """Test that parser can handle JSON in markdown code blocks."""
        vlm_raw = VLMRaw(
            content='```json\n{"brand": "Nike"}\n```',
            usage={},
            latency_ms=0.0,
            provider="test",
            model="test"
        )
        assert json_parser.can_parse(vlm_raw)
    
    def test_cannot_parse_plain_text(self, json_parser):
        """Test that parser cannot handle plain text responses."""
        vlm_raw = VLMRaw(
            content='This is just plain text without any JSON',
            usage={},
            latency_ms=0.0,
            provider="test",
            model="test"
        )
        assert not json_parser.can_parse(vlm_raw)
    
    def test_parse_simple_json(self, json_parser, sample_vlm_raw, sample_schema):
        """Test parsing simple JSON response."""
        attributes = json_parser.parse(sample_vlm_raw, sample_schema)
        
        assert attributes.data["brand"] == "Nike"
        assert attributes.data["model_or_type"] == "Air Max 90"
        assert attributes.confidences["brand"] == 0.9
        assert attributes.confidences["model_or_type"] == 0.8
        assert "high_confidence" in attributes.tags
    
    def test_parse_json_with_arrays(self, json_parser, sample_schema):
        """Test parsing JSON with array fields."""
        json_content = '''
        {
            "brand": {"value": "Adidas", "confidence": 0.85},
            "primary_colors": [
                {"name": "white", "confidence": 0.9},
                {"name": "black", "confidence": 0.8}
            ],
            "materials": [
                {"name": "leather", "confidence": 0.7},
                {"name": "rubber", "confidence": 0.9}
            ]
        }
        '''
        
        vlm_raw = VLMRaw(
            content=json_content,
            usage={},
            latency_ms=0.0,
            provider="test",
            model="test"
        )
        
        attributes = json_parser.parse(vlm_raw, sample_schema)
        
        assert attributes.data["brand"] == "Adidas"
        assert len(attributes.data["primary_colors"]) == 2
        assert attributes.data["primary_colors"][0]["name"] == "white"
        assert attributes.data["primary_colors"][0]["confidence"] == 0.9
        assert len(attributes.data["materials"]) == 2
    
    def test_parse_json_in_markdown(self, json_parser, sample_schema):
        """Test parsing JSON from markdown code blocks."""
        json_content = '''
        Here's the analysis:
        
        ```json
        {
            "brand": {"value": "Puma", "confidence": 0.75},
            "condition": {"value": "good", "confidence": 0.8}
        }
        ```
        
        This is the result.
        '''
        
        vlm_raw = VLMRaw(
            content=json_content,
            usage={},
            latency_ms=0.0,
            provider="test",
            model="test"
        )
        
        attributes = json_parser.parse(vlm_raw, sample_schema)
        
        assert attributes.data["brand"] == "Puma"
        assert attributes.data["condition"] == "good"
        assert attributes.confidences["brand"] == 0.75
    
    def test_parse_with_notes(self, json_parser, sample_schema):
        """Test parsing JSON with notes field."""
        json_content = '''
        {
            "brand": {"value": "Converse", "confidence": 0.9},
            "notes": "Classic Chuck Taylor design with some wear on the sole"
        }
        '''
        
        vlm_raw = VLMRaw(
            content=json_content,
            usage={},
            latency_ms=0.0,
            provider="test",
            model="test"
        )
        
        attributes = json_parser.parse(vlm_raw, sample_schema)
        
        assert attributes.data["brand"] == "Converse"
        assert "Classic Chuck Taylor design" in attributes.notes
    
    def test_parse_invalid_json_raises_error(self, json_parser, sample_schema):
        """Test that invalid JSON raises ParseError."""
        vlm_raw = VLMRaw(
            content='{"brand": "Nike", "model": }',  # Invalid JSON
            usage={},
            latency_ms=0.0,
            provider="test",
            model="test"
        )
        
        with pytest.raises(ParseError):
            json_parser.parse(vlm_raw, sample_schema)
    
    def test_parse_no_json_found_raises_error(self, json_parser, sample_schema):
        """Test that missing JSON raises ParseError."""
        vlm_raw = VLMRaw(
            content='This is just plain text without any JSON structure',
            usage={},
            latency_ms=0.0,
            provider="test",
            model="test"
        )
        
        with pytest.raises(ParseError):
            json_parser.parse(vlm_raw, sample_schema)
    
    def test_confidence_normalization(self, json_parser, sample_schema):
        """Test that confidence scores are normalized to 0.0-1.0 range."""
        json_content = '''
        {
            "brand": {"value": "Test", "confidence": 1.5},  # > 1.0
            "model_or_type": {"value": "Test", "confidence": -0.5}  # < 0.0
        }
        '''
        
        vlm_raw = VLMRaw(
            content=json_content,
            usage={},
            latency_ms=0.0,
            provider="test",
            model="test"
        )
        
        attributes = json_parser.parse(vlm_raw, sample_schema)
        
        assert attributes.confidences["brand"] == 1.0
        assert attributes.confidences["model_or_type"] == 0.0
    
    def test_lineage_metadata(self, json_parser, sample_vlm_raw, sample_schema):
        """Test that lineage metadata is properly set."""
        attributes = json_parser.parse(sample_vlm_raw, sample_schema)
        
        assert attributes.lineage["parser"] == "json"
        assert attributes.lineage["provider"] == "mistral"
        assert attributes.lineage["model"] == "mistral-large-latest"
        assert "timestamp" in attributes.lineage
        assert attributes.lineage["latency_ms"] == 1200.0
