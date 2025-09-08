"""Unit tests for PipelineService."""

import pytest
import tempfile
import yaml
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from vis2attr.core.config import Config
from vis2attr.core.schemas import Item, VLMRequest, VLMRaw, Attributes, Decision
from vis2attr.pipeline.service import PipelineService, PipelineError, PipelineResult


@pytest.fixture
def sample_config():
    """Create a sample configuration for testing."""
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
def sample_item():
    """Create a sample Item for testing."""
    return Item(
        item_id="test_item_123",
        images=[b"fake_image_data_1", b"fake_image_data_2"],
        meta={
            "source_path": "/test/images",
            "image_count": 2,
            "file_size": 1024
        }
    )


@pytest.fixture
def sample_schema():
    """Create a sample schema for testing."""
    return {
        "brand": {"value": None, "confidence": 0.0},
        "model_or_type": {"value": None, "confidence": 0.0},
        "primary_colors": [
            {"name": "", "confidence": 0.0}
        ],
        "materials": [
            {"name": "", "confidence": 0.0}
        ],
        "condition": {"value": None, "confidence": 0.0},
        "notes": ""
    }


@pytest.fixture
def sample_vlm_request():
    """Create a sample VLMRequest for testing."""
    return VLMRequest(
        model="pixtral-12b-latest",
        messages=[{"role": "user", "content": "test prompt"}],
        images=[b"fake_image_data"],
        max_tokens=1000,
        temperature=0.1
    )


@pytest.fixture
def sample_vlm_raw():
    """Create a sample VLMRaw for testing."""
    return VLMRaw(
        content='{"brand": {"value": "Nike", "confidence": 0.85}}',
        usage={"prompt_tokens": 100, "completion_tokens": 50},
        latency_ms=1500.0,
        provider="mistral",
        model="pixtral-12b-latest"
    )


@pytest.fixture
def sample_attributes():
    """Create sample Attributes for testing."""
    return Attributes(
        data={
            "brand": {"value": "Nike", "confidence": 0.85},
            "model_or_type": {"value": "Air Max", "confidence": 0.78},
            "primary_colors": [
                {"name": "White", "confidence": 0.90},
                {"name": "Black", "confidence": 0.85}
            ],
            "materials": [
                {"name": "Leather", "confidence": 0.80},
                {"name": "Rubber", "confidence": 0.75}
            ],
            "condition": {"value": "Good", "confidence": 0.82},
            "notes": "Slight wear on sole"
        },
        confidences={
            "brand": 0.85,
            "model_or_type": 0.78,
            "primary_colors": 0.875,  # Average of colors
            "materials": 0.775,  # Average of materials
            "condition": 0.82
        },
        tags={"sneakers", "athletic", "white"},
        notes="Slight wear on sole",
        lineage={"provider": "mistral", "model": "pixtral-12b-latest"}
    )


class TestPipelineServiceInit:
    """Test PipelineService initialization."""
    
    @patch('vis2attr.pipeline.service.FileSystemIngestor')
    @patch('vis2attr.pipeline.service.JinjaPromptBuilder')
    @patch('vis2attr.pipeline.service.create_provider')
    @patch('vis2attr.pipeline.service.ParseService')
    @patch('vis2attr.pipeline.service.create_storage_backend')
    def test_initialization_success(self, mock_storage, mock_parser, mock_provider, 
                                   mock_prompt, mock_ingestor, sample_config):
        """Test successful pipeline initialization."""
        # Mock the components
        mock_ingestor.return_value = Mock()
        mock_prompt.return_value = Mock()
        mock_provider.return_value = Mock()
        mock_parser.return_value = Mock()
        mock_storage.return_value = Mock()
        
        # Initialize pipeline
        pipeline = PipelineService(sample_config)
        
        # Verify all components were initialized
        mock_ingestor.assert_called_once()
        mock_prompt.assert_called_once()
        mock_provider.assert_called_once()
        mock_parser.assert_called_once()
        mock_storage.assert_called_once()
        
        assert pipeline.config == sample_config
    
    @patch('vis2attr.pipeline.service.FileSystemIngestor')
    def test_initialization_ingestor_failure(self, mock_ingestor, sample_config):
        """Test initialization failure when ingestor setup fails."""
        mock_ingestor.side_effect = Exception("Ingestor setup failed")
        
        with pytest.raises(PipelineError, match="Failed to initialize ingestor"):
            PipelineService(sample_config)
    
    @patch('vis2attr.pipeline.service.FileSystemIngestor')
    @patch('vis2attr.pipeline.service.JinjaPromptBuilder')
    def test_initialization_prompt_failure(self, mock_prompt, mock_ingestor, sample_config):
        """Test initialization failure when prompt builder setup fails."""
        mock_ingestor.return_value = Mock()
        mock_prompt.side_effect = Exception("Prompt builder setup failed")
        
        with pytest.raises(PipelineError, match="Failed to initialize prompt builder"):
            PipelineService(sample_config)


class TestPipelineServiceAnalyzeItem:
    """Test the analyze_item method."""
    
    @patch('vis2attr.pipeline.service.create_storage_backend')
    @patch('vis2attr.pipeline.service.ParseService')
    @patch('vis2attr.pipeline.service.create_provider')
    @patch('vis2attr.pipeline.service.JinjaPromptBuilder')
    @patch('vis2attr.pipeline.service.FileSystemIngestor')
    def test_analyze_item_success(self, mock_ingestor, mock_prompt, mock_provider, 
                                 mock_parser, mock_storage, sample_config, sample_item, 
                                 sample_schema, sample_vlm_request, sample_vlm_raw, 
                                 sample_attributes):
        """Test successful item analysis."""
        # Setup mocks
        mock_ingestor_instance = Mock()
        mock_ingestor_instance.load.return_value = sample_item
        mock_ingestor.return_value = mock_ingestor_instance
        
        mock_prompt_instance = Mock()
        mock_prompt_instance.load_schema.return_value = sample_schema
        mock_prompt_instance.build_request.return_value = sample_vlm_request
        mock_prompt.return_value = mock_prompt_instance
        
        mock_provider_instance = Mock()
        mock_provider_instance.predict.return_value = sample_vlm_raw
        mock_provider.return_value = mock_provider_instance
        
        mock_parser_instance = Mock()
        mock_parser_instance.parse_response.return_value = sample_attributes
        mock_parser.return_value = mock_parser_instance
        
        mock_storage_instance = Mock()
        mock_storage_instance.store_attributes.return_value = "attr_123"
        mock_storage_instance.store_raw_response.return_value = "raw_123"
        mock_storage_instance.store_lineage.return_value = "lineage_123"
        mock_storage.return_value = mock_storage_instance
        
        # Initialize pipeline
        pipeline = PipelineService(sample_config)
        
        # Run analysis
        result = pipeline.analyze_item("/test/images")
        
        # Verify result
        assert isinstance(result, PipelineResult)
        assert result.success is True
        assert result.item_id == "test_item_123"
        assert result.attributes == sample_attributes
        assert result.raw_response == sample_vlm_raw
        assert result.decision is not None
        assert result.decision.accepted is True
        assert result.processing_time_ms > 0
        assert "attributes" in result.storage_ids
        assert "raw_response" in result.storage_ids
        assert "lineage" in result.storage_ids
        
        # Verify all components were called
        mock_ingestor_instance.load.assert_called_once_with("/test/images")
        mock_prompt_instance.load_schema.assert_called_once()
        mock_prompt_instance.build_request.assert_called_once()
        mock_provider_instance.predict.assert_called_once_with(sample_vlm_request)
        mock_parser_instance.parse_response.assert_called_once_with(sample_vlm_raw, sample_schema)
    
    @patch('vis2attr.pipeline.service.create_storage_backend')
    @patch('vis2attr.pipeline.service.ParseService')
    @patch('vis2attr.pipeline.service.create_provider')
    @patch('vis2attr.pipeline.service.JinjaPromptBuilder')
    @patch('vis2attr.pipeline.service.FileSystemIngestor')
    def test_analyze_item_ingestion_failure(self, mock_ingestor, mock_prompt, mock_provider, 
                                           mock_parser, mock_storage, sample_config):
        """Test item analysis when ingestion fails."""
        # Setup mocks
        mock_ingestor_instance = Mock()
        mock_ingestor_instance.load.side_effect = Exception("Ingestion failed")
        mock_ingestor.return_value = mock_ingestor_instance
        
        mock_prompt.return_value = Mock()
        mock_provider.return_value = Mock()
        mock_parser.return_value = Mock()
        mock_storage.return_value = Mock()
        
        # Initialize pipeline
        pipeline = PipelineService(sample_config)
        
        # Run analysis
        result = pipeline.analyze_item("/test/images")
        
        # Verify result
        assert isinstance(result, PipelineResult)
        assert result.success is False
        assert result.error == "Pipeline failed: Ingestion failed"
        assert result.processing_time_ms > 0
    
    @patch('vis2attr.pipeline.service.create_storage_backend')
    @patch('vis2attr.pipeline.service.ParseService')
    @patch('vis2attr.pipeline.service.create_provider')
    @patch('vis2attr.pipeline.service.JinjaPromptBuilder')
    @patch('vis2attr.pipeline.service.FileSystemIngestor')
    def test_analyze_item_provider_failure(self, mock_ingestor, mock_prompt, mock_provider, 
                                          mock_parser, mock_storage, sample_config, 
                                          sample_item, sample_schema, sample_vlm_request):
        """Test item analysis when provider fails."""
        # Setup mocks
        mock_ingestor_instance = Mock()
        mock_ingestor_instance.load.return_value = sample_item
        mock_ingestor.return_value = mock_ingestor_instance
        
        mock_prompt_instance = Mock()
        mock_prompt_instance.load_schema.return_value = sample_schema
        mock_prompt_instance.build_request.return_value = sample_vlm_request
        mock_prompt.return_value = mock_prompt_instance
        
        mock_provider_instance = Mock()
        mock_provider_instance.predict.side_effect = Exception("Provider failed")
        mock_provider.return_value = mock_provider_instance
        
        mock_parser.return_value = Mock()
        mock_storage.return_value = Mock()
        
        # Initialize pipeline
        pipeline = PipelineService(sample_config)
        
        # Run analysis
        result = pipeline.analyze_item("/test/images")
        
        # Verify result
        assert isinstance(result, PipelineResult)
        assert result.success is False
        assert result.error == "Pipeline failed: Provider failed"
        assert result.item_id == "test_item_123"


class TestPipelineServiceAnalyzeBatch:
    """Test the analyze_batch method."""
    
    @patch('vis2attr.pipeline.service.create_storage_backend')
    @patch('vis2attr.pipeline.service.ParseService')
    @patch('vis2attr.pipeline.service.create_provider')
    @patch('vis2attr.pipeline.service.JinjaPromptBuilder')
    @patch('vis2attr.pipeline.service.FileSystemIngestor')
    def test_analyze_batch_success(self, mock_ingestor, mock_prompt, mock_provider, 
                                  mock_parser, mock_storage, sample_config, sample_item, 
                                  sample_schema, sample_vlm_request, sample_vlm_raw, 
                                  sample_attributes):
        """Test successful batch analysis."""
        # Setup mocks
        mock_ingestor_instance = Mock()
        mock_ingestor_instance.load.return_value = sample_item
        mock_ingestor.return_value = mock_ingestor_instance
        
        mock_prompt_instance = Mock()
        mock_prompt_instance.load_schema.return_value = sample_schema
        mock_prompt_instance.build_request.return_value = sample_vlm_request
        mock_prompt.return_value = mock_prompt_instance
        
        mock_provider_instance = Mock()
        mock_provider_instance.predict.return_value = sample_vlm_raw
        mock_provider.return_value = mock_provider_instance
        
        mock_parser_instance = Mock()
        mock_parser_instance.parse_response.return_value = sample_attributes
        mock_parser.return_value = mock_parser_instance
        
        mock_storage_instance = Mock()
        mock_storage_instance.store_attributes.return_value = "attr_123"
        mock_storage_instance.store_raw_response.return_value = "raw_123"
        mock_storage_instance.store_lineage.return_value = "lineage_123"
        mock_storage.return_value = mock_storage_instance
        
        # Initialize pipeline
        pipeline = PipelineService(sample_config)
        
        # Run batch analysis
        input_paths = ["/test/images1", "/test/images2", "/test/images3"]
        results = pipeline.analyze_batch(input_paths)
        
        # Verify results
        assert len(results) == 3
        assert all(isinstance(r, PipelineResult) for r in results)
        assert all(r.success for r in results)
        assert all(r.item_id == "test_item_123" for r in results)
        
        # Verify all items were processed
        assert mock_ingestor_instance.load.call_count == 3
    
    @patch('vis2attr.pipeline.service.create_storage_backend')
    @patch('vis2attr.pipeline.service.ParseService')
    @patch('vis2attr.pipeline.service.create_provider')
    @patch('vis2attr.pipeline.service.JinjaPromptBuilder')
    @patch('vis2attr.pipeline.service.FileSystemIngestor')
    def test_analyze_batch_mixed_results(self, mock_ingestor, mock_prompt, mock_provider, 
                                        mock_parser, mock_storage, sample_config, 
                                        sample_item, sample_schema, sample_vlm_request, 
                                        sample_vlm_raw, sample_attributes):
        """Test batch analysis with mixed success/failure results."""
        # Setup mocks with alternating success/failure
        mock_ingestor_instance = Mock()
        mock_ingestor_instance.load.side_effect = [
            sample_item,  # Success
            Exception("Ingestion failed"),  # Failure
            sample_item   # Success
        ]
        mock_ingestor.return_value = mock_ingestor_instance
        
        mock_prompt_instance = Mock()
        mock_prompt_instance.load_schema.return_value = sample_schema
        mock_prompt_instance.build_request.return_value = sample_vlm_request
        mock_prompt.return_value = mock_prompt_instance
        
        mock_provider_instance = Mock()
        mock_provider_instance.predict.return_value = sample_vlm_raw
        mock_provider.return_value = mock_provider_instance
        
        mock_parser_instance = Mock()
        mock_parser_instance.parse_response.return_value = sample_attributes
        mock_parser.return_value = mock_parser_instance
        
        mock_storage_instance = Mock()
        mock_storage_instance.store_attributes.return_value = "attr_123"
        mock_storage_instance.store_raw_response.return_value = "raw_123"
        mock_storage_instance.store_lineage.return_value = "lineage_123"
        mock_storage.return_value = mock_storage_instance
        
        # Initialize pipeline
        pipeline = PipelineService(sample_config)
        
        # Run batch analysis
        input_paths = ["/test/images1", "/test/images2", "/test/images3"]
        results = pipeline.analyze_batch(input_paths)
        
        # Verify results
        assert len(results) == 3
        successful = [r for r in results if r.success]
        failed = [r for r in results if not r.success]
        
        assert len(successful) == 2
        assert len(failed) == 1
        assert failed[0].error == "Pipeline failed: Ingestion failed"


class TestPipelineServiceDecisionMaking:
    """Test the decision making logic."""
    
    @patch('vis2attr.pipeline.service.create_storage_backend')
    @patch('vis2attr.pipeline.service.ParseService')
    @patch('vis2attr.pipeline.service.create_provider')
    @patch('vis2attr.pipeline.service.JinjaPromptBuilder')
    @patch('vis2attr.pipeline.service.FileSystemIngestor')
    def test_make_decision_high_confidence(self, mock_ingestor, mock_prompt, mock_provider, 
                                          mock_parser, mock_storage, sample_config, 
                                          sample_item, sample_schema, sample_vlm_request, 
                                          sample_vlm_raw, sample_attributes):
        """Test decision making with high confidence attributes."""
        # Create high confidence attributes
        high_conf_attributes = Attributes(
            data={
                "brand": {"value": "Nike", "confidence": 0.90},
                "model_or_type": {"value": "Air Max", "confidence": 0.85},
                "condition": {"value": "Excellent", "confidence": 0.88}
            },
            confidences={
                "brand": 0.90,
                "model_or_type": 0.85,
                "condition": 0.88
            },
            tags=set(),
            notes="",
            lineage={}
        )
        
        # Setup mocks
        mock_ingestor_instance = Mock()
        mock_ingestor_instance.load.return_value = sample_item
        mock_ingestor.return_value = mock_ingestor_instance
        
        mock_prompt_instance = Mock()
        mock_prompt_instance.load_schema.return_value = sample_schema
        mock_prompt_instance.build_request.return_value = sample_vlm_request
        mock_prompt.return_value = mock_prompt_instance
        
        mock_provider_instance = Mock()
        mock_provider_instance.predict.return_value = sample_vlm_raw
        mock_provider.return_value = mock_provider_instance
        
        mock_parser_instance = Mock()
        mock_parser_instance.parse_response.return_value = high_conf_attributes
        mock_parser.return_value = mock_parser_instance
        
        mock_storage_instance = Mock()
        mock_storage_instance.store_attributes.return_value = "attr_123"
        mock_storage_instance.store_raw_response.return_value = "raw_123"
        mock_storage_instance.store_lineage.return_value = "lineage_123"
        mock_storage.return_value = mock_storage_instance
        
        # Initialize pipeline
        pipeline = PipelineService(sample_config)
        
        # Run analysis
        result = pipeline.analyze_item("/test/images")
        
        # Verify decision
        assert result.success is True
        assert result.decision is not None
        assert result.decision.accepted is True
        assert result.decision.confidence_score > 0.75
        assert len(result.decision.reasons) == 0  # No rejection reasons
    
    @patch('vis2attr.pipeline.service.create_storage_backend')
    @patch('vis2attr.pipeline.service.ParseService')
    @patch('vis2attr.pipeline.service.create_provider')
    @patch('vis2attr.pipeline.service.JinjaPromptBuilder')
    @patch('vis2attr.pipeline.service.FileSystemIngestor')
    def test_make_decision_low_confidence(self, mock_ingestor, mock_prompt, mock_provider, 
                                         mock_parser, mock_storage, sample_config, 
                                         sample_item, sample_schema, sample_vlm_request, 
                                         sample_vlm_raw):
        """Test decision making with low confidence attributes."""
        # Create low confidence attributes
        low_conf_attributes = Attributes(
            data={
                "brand": {"value": "Unknown", "confidence": 0.30},
                "model_or_type": {"value": "Unknown", "confidence": 0.25},
                "condition": {"value": "Unknown", "confidence": 0.40}
            },
            confidences={
                "brand": 0.30,
                "model_or_type": 0.25,
                "condition": 0.40
            },
            tags=set(),
            notes="",
            lineage={}
        )
        
        # Setup mocks
        mock_ingestor_instance = Mock()
        mock_ingestor_instance.load.return_value = sample_item
        mock_ingestor.return_value = mock_ingestor_instance
        
        mock_prompt_instance = Mock()
        mock_prompt_instance.load_schema.return_value = sample_schema
        mock_prompt_instance.build_request.return_value = sample_vlm_request
        mock_prompt.return_value = mock_prompt_instance
        
        mock_provider_instance = Mock()
        mock_provider_instance.predict.return_value = sample_vlm_raw
        mock_provider.return_value = mock_provider_instance
        
        mock_parser_instance = Mock()
        mock_parser_instance.parse_response.return_value = low_conf_attributes
        mock_parser.return_value = mock_parser_instance
        
        mock_storage_instance = Mock()
        mock_storage_instance.store_attributes.return_value = "attr_123"
        mock_storage_instance.store_raw_response.return_value = "raw_123"
        mock_storage_instance.store_lineage.return_value = "lineage_123"
        mock_storage.return_value = mock_storage_instance
        
        # Initialize pipeline
        pipeline = PipelineService(sample_config)
        
        # Run analysis
        result = pipeline.analyze_item("/test/images")
        
        # Verify decision
        assert result.success is True
        assert result.decision is not None
        assert result.decision.accepted is False
        assert result.decision.confidence_score < 0.75
        assert len(result.decision.reasons) > 0  # Should have rejection reasons


class TestPipelineServiceStatus:
    """Test pipeline status and utility methods."""
    
    @patch('vis2attr.pipeline.service.create_storage_backend')
    @patch('vis2attr.pipeline.service.ParseService')
    @patch('vis2attr.pipeline.service.create_provider')
    @patch('vis2attr.pipeline.service.JinjaPromptBuilder')
    @patch('vis2attr.pipeline.service.FileSystemIngestor')
    def test_get_pipeline_status(self, mock_ingestor, mock_prompt, mock_provider, 
                                mock_parser, mock_storage, sample_config):
        """Test getting pipeline status."""
        # Setup mocks
        mock_ingestor.return_value = Mock()
        mock_prompt.return_value = Mock()
        mock_provider.return_value = Mock()
        mock_parser.return_value = Mock()
        mock_storage.return_value = Mock()
        
        # Initialize pipeline
        pipeline = PipelineService(sample_config)
        
        # Get status
        status = pipeline.get_pipeline_status()
        
        # Verify status
        assert isinstance(status, dict)
        assert "pipeline_version" in status
        assert "components" in status
        assert "config" in status
        assert "timestamp" in status
        
        assert status["components"]["ingestor"] == "ingest.fs"
        assert status["components"]["provider"] == "providers.mistral"
        assert status["components"]["storage"] == "storage.files"
        assert status["config"]["schema_path"] == "config/schemas/default.yaml"


class TestPipelineResult:
    """Test PipelineResult class."""
    
    def test_pipeline_result_success(self):
        """Test successful pipeline result creation."""
        attributes = Attributes(
            data={"brand": {"value": "Nike", "confidence": 0.85}},
            confidences={"brand": 0.85},
            tags=set(),
            notes="",
            lineage={}
        )
        
        decision = Decision(
            accepted=True,
            field_flags={"brand": "accepted"},
            reasons=[],
            confidence_score=0.85
        )
        
        result = PipelineResult(
            item_id="test_123",
            success=True,
            attributes=attributes,
            decision=decision,
            processing_time_ms=1500.0,
            storage_ids={"attributes": "attr_123"}
        )
        
        assert result.item_id == "test_123"
        assert result.success is True
        assert result.attributes == attributes
        assert result.decision == decision
        assert result.processing_time_ms == 1500.0
        assert result.storage_ids == {"attributes": "attr_123"}
        assert result.error is None
        assert isinstance(result.timestamp, datetime)
    
    def test_pipeline_result_failure(self):
        """Test failed pipeline result creation."""
        result = PipelineResult(
            item_id="test_123",
            success=False,
            error="Test error message",
            processing_time_ms=500.0
        )
        
        assert result.item_id == "test_123"
        assert result.success is False
        assert result.error == "Test error message"
        assert result.processing_time_ms == 500.0
        assert result.attributes is None
        assert result.decision is None
        assert result.storage_ids == {}


class TestPipelineError:
    """Test PipelineError exception."""
    
    def test_pipeline_error_creation(self):
        """Test PipelineError creation."""
        error = PipelineError("Test error message")
        assert str(error) == "Test error message"
        assert isinstance(error, Exception)
    
    def test_pipeline_error_with_cause(self):
        """Test PipelineError with underlying cause."""
        original_error = ValueError("Original error")
        error = PipelineError("Pipeline failed") 
        error.__cause__ = original_error
        assert str(error) == "Pipeline failed"
        assert error.__cause__ == original_error
