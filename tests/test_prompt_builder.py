"""Tests for the prompt builder implementation."""

import pytest
import tempfile
import yaml
from pathlib import Path
from src.vis2attr.prompt import JinjaPromptBuilder
from src.vis2attr.core.schemas import Item, VLMRequest


class TestJinjaPromptBuilder:
    """Test the Jinja prompt builder implementation."""
    
    def test_prompt_builder_initialization(self):
        """Test prompt builder initialization."""
        config = {"template_path": "config/prompts", "template_name": "default.jinja"}
        builder = JinjaPromptBuilder(config)
        
        assert builder.template_path == "config/prompts"
        assert builder.config["template_name"] == "default.jinja"
    
    def test_load_schema_yaml(self):
        """Test loading schema from YAML file."""
        # Create temporary schema file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            schema_data = {
                "brand": {"value": None, "confidence": 0.0},
                "model_or_type": {"value": None, "confidence": 0.0},
                "notes": ""
            }
            yaml.dump(schema_data, f)
            schema_path = f.name
        
        try:
            config = {"template_path": "config/prompts"}
            builder = JinjaPromptBuilder(config)
            schema = builder.load_schema(schema_path)
            
            assert "brand" in schema
            assert "model_or_type" in schema
            assert "notes" in schema
            assert schema["brand"]["confidence"] == 0.0
        finally:
            Path(schema_path).unlink()
    
    def test_load_schema_json(self):
        """Test loading schema from JSON file."""
        import json
        
        # Create temporary schema file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            schema_data = {
                "brand": {"value": None, "confidence": 0.0},
                "model_or_type": {"value": None, "confidence": 0.0}
            }
            json.dump(schema_data, f)
            schema_path = f.name
        
        try:
            config = {"template_path": "config/prompts"}
            builder = JinjaPromptBuilder(config)
            schema = builder.load_schema(schema_path)
            
            assert "brand" in schema
            assert "model_or_type" in schema
        finally:
            Path(schema_path).unlink()
    
    def test_load_schema_file_not_found(self):
        """Test loading schema from non-existent file."""
        config = {"template_path": "config/prompts"}
        builder = JinjaPromptBuilder(config)
        
        with pytest.raises(FileNotFoundError):
            builder.load_schema("nonexistent.yaml")
    
    def test_get_schema_fields(self):
        """Test extracting field names from schema."""
        config = {"template_path": "config/prompts"}
        builder = JinjaPromptBuilder(config)
        
        schema = {
            "brand": {"value": None, "confidence": 0.0},
            "model_or_type": {"value": None, "confidence": 0.0},
            "primary_colors": [{"name": "", "confidence": 0.0}],
            "materials": [{"name": "", "confidence": 0.0}],
            "notes": ""
        }
        
        fields = builder.get_schema_fields(schema)
        expected_fields = ["brand", "model_or_type", "primary_colors", "materials", "notes"]
        
        assert set(fields) == set(expected_fields)
    
    def test_prepare_context(self):
        """Test context preparation for template rendering."""
        config = {"template_path": "config/prompts"}
        builder = JinjaPromptBuilder(config)
        
        item = Item(
            item_id="test_item_001",
            images=[b"fake_image_data"],
            meta={"source": "test"}
        )
        
        schema = {
            "brand": {"value": None, "confidence": 0.0},
            "model_or_type": {"value": None, "confidence": 0.0},
            "notes": ""
        }
        
        context = builder._prepare_context(item, schema)
        
        assert context["item_id"] == "test_item_001"
        assert context["num_images"] == 1
        assert context["item_meta"]["source"] == "test"
        assert "brand" in context["schema_fields"]
        assert "model_or_type" in context["schema_fields"]
        assert "notes" in context["schema_fields"]
        assert "schema_description" in context
        assert "example_output" in context
    
    def test_format_schema_description(self):
        """Test schema description formatting."""
        config = {"template_path": "config/prompts"}
        builder = JinjaPromptBuilder(config)
        
        schema = {
            "brand": {"value": None, "confidence": 0.0},
            "primary_colors": [{"name": "", "confidence": 0.0}],
            "notes": ""
        }
        
        fields = ["brand", "primary_colors", "notes"]
        description = builder._format_schema_description(schema, fields)
        
        assert "- brand: single value" in description
        assert "- primary_colors: list of items" in description
        assert "- notes: text string" in description
    
    def test_create_example_output(self):
        """Test example output creation."""
        config = {"template_path": "config/prompts"}
        builder = JinjaPromptBuilder(config)
        
        schema = {
            "brand": {"value": None, "confidence": 0.0},
            "primary_colors": [{"name": "", "confidence": 0.0}],
            "notes": ""
        }
        
        fields = ["brand", "primary_colors", "notes"]
        example = builder._create_example_output(schema, fields)
        
        # Parse the JSON to verify structure
        import json
        example_data = json.loads(example)
        
        assert "brand" in example_data
        assert "primary_colors" in example_data
        assert "notes" in example_data
        assert example_data["brand"]["value"] == "example_value"
        assert example_data["brand"]["confidence"] == 0.85
        assert isinstance(example_data["primary_colors"], list)
        assert example_data["notes"] == "example text"
    
    def test_create_messages_text_only(self):
        """Test message creation with text only."""
        config = {"template_path": "config/prompts"}
        builder = JinjaPromptBuilder(config)
        
        messages = builder._create_messages("Test prompt", [])
        
        assert len(messages) == 1
        assert messages[0]["role"] == "user"
        assert messages[0]["content"] == "Test prompt"
    
    def test_create_messages_with_images(self):
        """Test message creation with images."""
        config = {"template_path": "config/prompts"}
        builder = JinjaPromptBuilder(config)
        
        messages = builder._create_messages("Test prompt", [b"fake_image_data"])
        
        assert len(messages) == 1
        assert messages[0]["role"] == "user"
        assert isinstance(messages[0]["content"], list)
        assert len(messages[0]["content"]) == 2  # text + image
        assert messages[0]["content"][0]["type"] == "text"
        assert messages[0]["content"][1]["type"] == "image_url"
        assert "data:image/jpeg;base64," in messages[0]["content"][1]["image_url"]
    
    def test_create_messages_with_urls(self):
        """Test message creation with image URLs."""
        config = {"template_path": "config/prompts"}
        builder = JinjaPromptBuilder(config)
        
        messages = builder._create_messages("Test prompt", ["https://example.com/image.jpg"])
        
        assert len(messages) == 1
        assert messages[0]["role"] == "user"
        assert isinstance(messages[0]["content"], list)
        assert len(messages[0]["content"]) == 2  # text + image
        assert messages[0]["content"][0]["type"] == "text"
        assert messages[0]["content"][1]["type"] == "image_url"
        assert messages[0]["content"][1]["image_url"] == "https://example.com/image.jpg"
