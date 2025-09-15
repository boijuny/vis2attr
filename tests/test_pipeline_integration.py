"""Integration tests for the complete vis2attr pipeline."""

import pytest
import tempfile
import yaml
from pathlib import Path
from unittest.mock import Mock, patch
from PIL import Image
import io

from vis2attr.core.config import Config
from vis2attr.pipeline.service import PipelineService, PipelineError


@pytest.fixture
def integration_config():
    """Create a configuration for integration testing."""
    config_data = {
        "ingestor": "ingest.fs",
        "provider": "providers.mistral",
        "storage": "storage.files",
        "schema_path": "config/schemas/default.yaml",
        "prompt_template": "config/prompts/default.jinja",
        "thresholds": {
            "default": 0.75,
            "brand": 0.80,
            "model_or_type": 0.70,
            "primary_colors": 0.65,
            "materials": 0.70,
            "condition": 0.75
        },
        "io": {
            "max_images_per_item": 3,
            "max_resolution": 768,
            "supported_formats": [".jpg", ".jpeg", ".png", ".webp"]
        },
        "providers": {
            "mistral": {
                "model": "pixtral-12b-latest",
                "max_tokens": 1000,
                "temperature": 0.1
            }
        },
        "metrics": {
            "enable_metrics": True,
            "log_level": "INFO",
            "structured_logging": True
        },
        "security": {
            "strip_exif": True,
            "avoid_pii": True,
            "temp_file_cleanup": True
        },
        "storage_config": {
            "storage_root": "./test_storage",
            "create_dirs": True,
            "backup_enabled": False
        }
    }
    return Config(**config_data)


@pytest.fixture
def test_images_dir():
    """Create a directory with test images for integration testing."""
    temp_dir = tempfile.mkdtemp()
    images_dir = Path(temp_dir) / "test_images"
    images_dir.mkdir()
    
    # Create multiple test images with different colors
    colors = ['red', 'green', 'blue', 'yellow', 'purple']
    for i, color in enumerate(colors):
        img = Image.new('RGB', (100, 100), color=color)
        img_path = images_dir / f"test_{i}.jpg"
        img.save(img_path, format='JPEG', quality=85)
    
    # Create a PNG image
    img = Image.new('RGB', (75, 75), color='orange')
    img_path = images_dir / "test_png.png"
    img.save(img_path, format='PNG')
    
    return images_dir


@pytest.fixture
def mock_vlm_response():
    """Create a mock VLM response for testing."""
    return {
        "content": '''{
            "brand": {"value": "Nike", "confidence": 0.85},
            "model_or_type": {"value": "Air Max 90", "confidence": 0.78},
            "primary_colors": [
                {"name": "White", "confidence": 0.90},
                {"name": "Black", "confidence": 0.85}
            ],
            "materials": [
                {"name": "Leather", "confidence": 0.80},
                {"name": "Rubber", "confidence": 0.75}
            ],
            "condition": {"value": "Good", "confidence": 0.82},
            "notes": "Classic sneaker in good condition with slight wear on sole"
        }''',
        "usage": {"prompt_tokens": 150, "completion_tokens": 75},
        "latency_ms": 1800.0,
        "provider": "mistral",
        "model": "pixtral-12b-latest"
    }


class TestPipelineIntegration:
    """Test the complete pipeline integration."""
    
    @patch('vis2attr.pipeline.service.create_storage_backend')
    @patch('vis2attr.pipeline.service.ParseService')
    @patch('vis2attr.pipeline.service.create_provider')
    @patch('vis2attr.pipeline.service.JinjaPromptBuilder')
    @patch('vis2attr.pipeline.service.FileSystemIngestor')
    def test_pipeline_initialization(self, mock_ingestor, mock_prompt, mock_provider, 
                                   mock_parser, mock_storage, integration_config):
        """Test that the pipeline initializes correctly with all components."""
        # Setup mocks
        mock_ingestor.return_value = Mock()
        mock_prompt.return_value = Mock()
        mock_provider.return_value = Mock()
        mock_parser.return_value = Mock()
        mock_storage.return_value = Mock()
        
        # Initialize pipeline
        pipeline = PipelineService(integration_config)
        
        # Verify all components were initialized
        mock_ingestor.assert_called_once()
        mock_prompt.assert_called_once()
        mock_provider.assert_called_once()
        mock_parser.assert_called_once()
        mock_storage.assert_called_once()
        
        # Verify pipeline status
        status = pipeline.get_pipeline_status()
        assert status["pipeline_version"] == "1.0.0"
        assert status["components"]["ingestor"] == "ingest.fs"
        assert status["components"]["provider"] == "providers.mistral"
        assert status["components"]["storage"] == "storage.files"
    
    @patch('vis2attr.pipeline.service.create_storage_backend')
    @patch('vis2attr.pipeline.service.ParseService')
    @patch('vis2attr.pipeline.service.create_provider')
    @patch('vis2attr.pipeline.service.JinjaPromptBuilder')
    @patch('vis2attr.pipeline.service.FileSystemIngestor')
    def test_pipeline_analyze_single_item(self, mock_ingestor, mock_prompt, mock_provider, 
                                        mock_parser, mock_storage, integration_config, 
                                        test_images_dir, mock_vlm_response):
        """Test analyzing a single item through the complete pipeline."""
        from vis2attr.core.schemas import Item, VLMRequest, VLMRaw, Attributes, Decision
        
        # Create mock item
        mock_item = Item(
            item_id="test_item_001",
            images=[b"fake_image_data_1", b"fake_image_data_2"],
            meta={
                "source_path": str(test_images_dir),
                "image_count": 2,
                "file_size": 2048
            }
        )
        
        # Create mock VLM request
        mock_vlm_request = VLMRequest(
            model="pixtral-12b-latest",
            messages=[{"role": "user", "content": "test prompt"}],
            images=[b"fake_image_data_1", b"fake_image_data_2"],
            max_tokens=1000,
            temperature=0.1
        )
        
        # Create mock VLM raw response
        mock_vlm_raw = VLMRaw(
            content=mock_vlm_response["content"],
            usage=mock_vlm_response["usage"],
            latency_ms=mock_vlm_response["latency_ms"],
            provider=mock_vlm_response["provider"],
            model=mock_vlm_response["model"]
        )
        
        # Create mock attributes
        mock_attributes = Attributes(
            data={
                "brand": {"value": "Nike", "confidence": 0.85},
                "model_or_type": {"value": "Air Max 90", "confidence": 0.78},
                "primary_colors": [
                    {"name": "White", "confidence": 0.90},
                    {"name": "Black", "confidence": 0.85}
                ],
                "materials": [
                    {"name": "Leather", "confidence": 0.80},
                    {"name": "Rubber", "confidence": 0.75}
                ],
                "condition": {"value": "Good", "confidence": 0.82},
                "notes": "Classic sneaker in good condition with slight wear on sole"
            },
            confidences={
                "brand": 0.85,
                "model_or_type": 0.78,
                "primary_colors": 0.875,
                "materials": 0.775,
                "condition": 0.82
            },
            tags={"sneakers", "athletic", "white", "black"},
            notes="Classic sneaker in good condition with slight wear on sole",
            lineage={"provider": "mistral", "model": "pixtral-12b-latest"}
        )
        
        # Setup mocks
        mock_ingestor_instance = Mock()
        mock_ingestor_instance.load.return_value = mock_item
        mock_ingestor.return_value = mock_ingestor_instance
        
        mock_prompt_instance = Mock()
        mock_prompt_instance.load_schema.return_value = {
            "brand": {"value": None, "confidence": 0.0},
            "model_or_type": {"value": None, "confidence": 0.0},
            "primary_colors": [{"name": "", "confidence": 0.0}],
            "materials": [{"name": "", "confidence": 0.0}],
            "condition": {"value": None, "confidence": 0.0},
            "notes": ""
        }
        mock_prompt_instance.build_request.return_value = mock_vlm_request
        mock_prompt.return_value = mock_prompt_instance
        
        mock_provider_instance = Mock()
        mock_provider_instance.predict.return_value = mock_vlm_raw
        mock_provider.return_value = mock_provider_instance
        
        mock_parser_instance = Mock()
        mock_parser_instance.parse_response.return_value = mock_attributes
        mock_parser.return_value = mock_parser_instance
        
        mock_storage_instance = Mock()
        mock_storage_instance.store_attributes.return_value = "attr_001"
        mock_storage_instance.store_raw_response.return_value = "raw_001"
        mock_storage_instance.store_lineage.return_value = "lineage_001"
        mock_storage.return_value = mock_storage_instance
        
        # Initialize pipeline
        pipeline = PipelineService(integration_config)
        
        # Run analysis
        result = pipeline.analyze_item(test_images_dir)
        
        # Verify result
        assert result.success is True
        assert result.item_id == "test_item_001"
        assert result.attributes == mock_attributes
        assert result.raw_response == mock_vlm_raw
        assert result.decision is not None
        assert result.decision.accepted is True
        assert result.processing_time_ms > 0
        assert "attributes" in result.storage_ids
        assert "raw_response" in result.storage_ids
        assert "lineage" in result.storage_ids
        
        # Verify all components were called
        mock_ingestor_instance.load.assert_called_once_with(test_images_dir)
        mock_prompt_instance.load_schema.assert_called_once()
        mock_prompt_instance.build_request.assert_called_once()
        mock_provider_instance.predict.assert_called_once_with(mock_vlm_request)
        mock_parser_instance.parse_response.assert_called_once()
        mock_storage_instance.store_attributes.assert_called_once()
        mock_storage_instance.store_raw_response.assert_called_once()
        mock_storage_instance.store_lineage.assert_called_once()
    
    @patch('vis2attr.pipeline.service.create_storage_backend')
    @patch('vis2attr.pipeline.service.ParseService')
    @patch('vis2attr.pipeline.service.create_provider')
    @patch('vis2attr.pipeline.service.JinjaPromptBuilder')
    @patch('vis2attr.pipeline.service.FileSystemIngestor')
    def test_pipeline_analyze_batch(self, mock_ingestor, mock_prompt, mock_provider, 
                                   mock_parser, mock_storage, integration_config, 
                                   test_images_dir, mock_vlm_response):
        """Test analyzing multiple items in batch."""
        from vis2attr.core.schemas import Item, VLMRequest, VLMRaw, Attributes
        
        # Create mock items
        mock_items = [
            Item(
                item_id="test_item_001",
                images=[b"fake_image_data_1"],
                meta={"source_path": str(test_images_dir / "item1"), "image_count": 1}
            ),
            Item(
                item_id="test_item_002", 
                images=[b"fake_image_data_2"],
                meta={"source_path": str(test_images_dir / "item2"), "image_count": 1}
            )
        ]
        
        # Create mock attributes
        mock_attributes = Attributes(
            data={
                "brand": {"value": "Nike", "confidence": 0.85},
                "model_or_type": {"value": "Air Max 90", "confidence": 0.78},
                "condition": {"value": "Good", "confidence": 0.82}
            },
            confidences={
                "brand": 0.85,
                "model_or_type": 0.78,
                "condition": 0.82
            },
            tags={"sneakers"},
            notes="Test item",
            lineage={}
        )
        
        # Setup mocks
        mock_ingestor_instance = Mock()
        mock_ingestor_instance.load.side_effect = mock_items
        mock_ingestor.return_value = mock_ingestor_instance
        
        mock_prompt_instance = Mock()
        mock_prompt_instance.load_schema.return_value = {
            "brand": {"value": None, "confidence": 0.0},
            "model_or_type": {"value": None, "confidence": 0.0},
            "condition": {"value": None, "confidence": 0.0}
        }
        mock_prompt_instance.build_request.return_value = Mock()
        mock_prompt.return_value = mock_prompt_instance
        
        mock_provider_instance = Mock()
        mock_provider_instance.predict.return_value = VLMRaw(
            content=mock_vlm_response["content"],
            usage=mock_vlm_response["usage"],
            latency_ms=mock_vlm_response["latency_ms"],
            provider=mock_vlm_response["provider"],
            model=mock_vlm_response["model"]
        )
        mock_provider.return_value = mock_provider_instance
        
        mock_parser_instance = Mock()
        mock_parser_instance.parse_response.return_value = mock_attributes
        mock_parser.return_value = mock_parser_instance
        
        mock_storage_instance = Mock()
        mock_storage_instance.store_attributes.return_value = "attr_001"
        mock_storage_instance.store_raw_response.return_value = "raw_001"
        mock_storage_instance.store_lineage.return_value = "lineage_001"
        mock_storage.return_value = mock_storage_instance
        
        # Initialize pipeline
        pipeline = PipelineService(integration_config)
        
        # Run batch analysis
        input_paths = [test_images_dir / "item1", test_images_dir / "item2"]
        results = pipeline.analyze_batch(input_paths)
        
        # Verify results
        assert len(results) == 2
        assert all(result.success for result in results)
        assert all(result.item_id.startswith("test_item_") for result in results)
        
        # Verify all items were processed
        assert mock_ingestor_instance.load.call_count == 2
    
    @patch('vis2attr.pipeline.service.create_storage_backend')
    @patch('vis2attr.pipeline.service.ParseService')
    @patch('vis2attr.pipeline.service.create_provider')
    @patch('vis2attr.pipeline.service.JinjaPromptBuilder')
    @patch('vis2attr.pipeline.service.FileSystemIngestor')
    def test_pipeline_error_handling(self, mock_ingestor, mock_prompt, mock_provider, 
                                   mock_parser, mock_storage, integration_config, 
                                   test_images_dir):
        """Test pipeline error handling."""
        # Setup mocks to simulate failure
        mock_ingestor_instance = Mock()
        mock_ingestor_instance.load.side_effect = Exception("Ingestion failed")
        mock_ingestor.return_value = mock_ingestor_instance
        
        mock_prompt.return_value = Mock()
        mock_provider.return_value = Mock()
        mock_parser.return_value = Mock()
        mock_storage.return_value = Mock()
        
        # Initialize pipeline
        pipeline = PipelineService(integration_config)
        
        # Run analysis
        result = pipeline.analyze_item(test_images_dir)
        
        # Verify error handling
        assert result.success is False
        assert "Pipeline analysis failed" in result.error
        assert "Ingestion failed" in result.error
        assert "original_error=Ingestion failed" in result.error
        assert result.processing_time_ms > 0
        assert result.attributes is None
        assert result.decision is None
    
    def test_pipeline_config_validation(self, integration_config):
        """Test that the configuration is valid."""
        # Test configuration properties
        assert integration_config.ingestor == "ingest.fs"
        assert integration_config.provider == "providers.mistral"
        assert integration_config.storage == "storage.files"
        assert integration_config.schema_path == "config/schemas/default.yaml"
        assert integration_config.prompt_template == "config/prompts/default.jinja"
        
        # Test thresholds
        assert integration_config.get_threshold("default") == 0.75
        assert integration_config.get_threshold("brand") == 0.80
        assert integration_config.get_threshold("model_or_type") == 0.70
        assert integration_config.get_threshold("nonexistent") == 0.75  # Default fallback
        
        # Test provider config
        provider_config = integration_config.get_provider_config("mistral")
        assert provider_config["model"] == "pixtral-12b-latest"
        assert provider_config["max_tokens"] == 1000
        assert provider_config["temperature"] == 0.1
        
        # Test storage config
        storage_config = integration_config.get_storage_config()
        assert storage_config["storage_root"] == "./test_storage"
        assert storage_config["create_dirs"] is True
        assert storage_config["backup_enabled"] is False
