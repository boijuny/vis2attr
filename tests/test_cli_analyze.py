"""Unit tests for CLI analyze command."""

import pytest
import tempfile
import pandas as pd
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from click.testing import CliRunner

from vis2attr.cli.analyze import analyze_command, _save_results_to_parquet, _show_summary_stats
from vis2attr.pipeline.service import PipelineResult, PipelineError
from vis2attr.core.schemas import Attributes, Decision, VLMRaw
from datetime import datetime


@pytest.fixture
def sample_pipeline_results():
    """Create sample pipeline results for testing."""
    attributes1 = Attributes(
        data={
            "brand": {"value": "Nike", "confidence": 0.85},
            "model_or_type": {"value": "Air Max", "confidence": 0.78},
            "condition": {"value": "Good", "confidence": 0.82}
        },
        confidences={
            "brand": 0.85,
            "model_or_type": 0.78,
            "condition": 0.82
        },
        tags={"sneakers", "athletic"},
        notes="Slight wear on sole",
        lineage={"provider": "mistral"}
    )
    
    decision1 = Decision(
        accepted=True,
        field_flags={"brand": "accepted", "model_or_type": "accepted", "condition": "accepted"},
        reasons=[],
        confidence_score=0.82
    )
    
    raw_response1 = VLMRaw(
        content='{"brand": {"value": "Nike", "confidence": 0.85}}',
        usage={"prompt_tokens": 100, "completion_tokens": 50},
        latency_ms=1500.0,
        provider="mistral",
        model="pixtral-12b-latest"
    )
    
    result1 = PipelineResult(
        item_id="item_001",
        success=True,
        attributes=attributes1,
        raw_response=raw_response1,
        decision=decision1,
        processing_time_ms=2000.0,
        storage_ids={"attributes": "attr_001", "raw_response": "raw_001"}
    )
    
    # Second result with lower confidence
    attributes2 = Attributes(
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
        lineage={"provider": "mistral"}
    )
    
    decision2 = Decision(
        accepted=False,
        field_flags={"brand": "low_confidence", "model_or_type": "low_confidence", "condition": "low_confidence"},
        reasons=["brand confidence 0.300 below threshold 0.800", "model_or_type confidence 0.250 below threshold 0.700"],
        confidence_score=0.32
    )
    
    raw_response2 = VLMRaw(
        content='{"brand": {"value": "Unknown", "confidence": 0.30}}',
        usage={"prompt_tokens": 100, "completion_tokens": 30},
        latency_ms=1200.0,
        provider="mistral",
        model="pixtral-12b-latest"
    )
    
    result2 = PipelineResult(
        item_id="item_002",
        success=True,
        attributes=attributes2,
        raw_response=raw_response2,
        decision=decision2,
        processing_time_ms=1500.0,
        storage_ids={"attributes": "attr_002", "raw_response": "raw_002"}
    )
    
    return [result1, result2]


@pytest.fixture
def temp_config_file():
    """Create a temporary config file for testing."""
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
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        import yaml
        yaml.dump(config_data, f)
        return f.name


@pytest.fixture
def temp_images_dir():
    """Create a temporary directory with test images."""
    temp_dir = tempfile.mkdtemp()
    images_dir = Path(temp_dir) / "images"
    images_dir.mkdir()
    
    # Create a simple test image
    from PIL import Image
    img = Image.new('RGB', (100, 100), color='red')
    img_path = images_dir / "test.jpg"
    img.save(img_path, format='JPEG', quality=85)
    
    return images_dir


class TestAnalyzeCommand:
    """Test the analyze command functionality."""
    
    @patch('vis2attr.cli.analyze.PipelineService')
    @patch('vis2attr.cli.analyze.Config')
    def test_analyze_command_success(self, mock_config_class, mock_pipeline_class, 
                                   temp_config_file, temp_images_dir, sample_pipeline_results):
        """Test successful analyze command execution."""
        # Setup mocks
        mock_config = Mock()
        mock_config_class.from_file.return_value = mock_config
        
        mock_pipeline = Mock()
        mock_pipeline.analyze_batch.return_value = sample_pipeline_results
        mock_pipeline_class.return_value = mock_pipeline
        
        # Run command
        runner = CliRunner()
        result = runner.invoke(analyze_command, [
            "--input", str(temp_images_dir),
            "--config", temp_config_file,
            "--output", "test_output.parquet"
        ])
        
        # Verify success
        assert result.exit_code == 0
        assert "Analysis completed" in result.output
        assert "✅ Successful: 2" in result.output
        assert "❌ Failed: 0" in result.output
        assert "Results saved successfully!" in result.output
        
        # Verify pipeline was called correctly
        mock_config_class.from_file.assert_called_once_with(temp_config_file)
        mock_pipeline_class.assert_called_once_with(mock_config)
        mock_pipeline.analyze_batch.assert_called_once()
    
    @patch('vis2attr.cli.analyze.PipelineService')
    @patch('vis2attr.cli.analyze.Config')
    def test_analyze_command_with_overrides(self, mock_config_class, mock_pipeline_class, 
                                          temp_config_file, temp_images_dir, sample_pipeline_results):
        """Test analyze command with schema and provider overrides."""
        # Setup mocks
        mock_config = Mock()
        mock_config_class.from_file.return_value = mock_config
        
        mock_pipeline = Mock()
        mock_pipeline.analyze_batch.return_value = sample_pipeline_results
        mock_pipeline_class.return_value = mock_pipeline
        
        # Run command with overrides
        runner = CliRunner()
        result = runner.invoke(analyze_command, [
            "--input", str(temp_images_dir),
            "--config", temp_config_file,
            "--schema", "custom_schema.yaml",
            "--provider", "openai",
            "--verbose"
        ])
        
        # Verify success
        assert result.exit_code == 0
        
        # Verify overrides were applied
        assert mock_config.schema_path == "custom_schema.yaml"
        assert mock_config.provider == "providers.openai"
    
    @patch('vis2attr.cli.analyze.PipelineService')
    @patch('vis2attr.cli.analyze.Config')
    def test_analyze_command_batch_mode(self, mock_config_class, mock_pipeline_class, 
                                      temp_config_file, temp_images_dir, sample_pipeline_results):
        """Test analyze command in batch mode."""
        # Create subdirectories for batch processing
        subdir1 = temp_images_dir / "item1"
        subdir1.mkdir()
        subdir2 = temp_images_dir / "item2"
        subdir2.mkdir()
        
        # Setup mocks
        mock_config = Mock()
        mock_config_class.from_file.return_value = mock_config
        
        mock_pipeline = Mock()
        mock_pipeline.analyze_batch.return_value = sample_pipeline_results
        mock_pipeline_class.return_value = mock_pipeline
        
        # Run command in batch mode
        runner = CliRunner()
        result = runner.invoke(analyze_command, [
            "--input", str(temp_images_dir),
            "--config", temp_config_file,
            "--batch"
        ])
        
        # Verify success
        assert result.exit_code == 0
        assert "Batch processing 2 directories" in result.output
    
    @patch('vis2attr.cli.analyze.PipelineService')
    @patch('vis2attr.cli.analyze.Config')
    def test_analyze_command_pipeline_error(self, mock_config_class, mock_pipeline_class, 
                                           temp_config_file, temp_images_dir):
        """Test analyze command when pipeline fails."""
        # Setup mocks
        mock_config = Mock()
        mock_config_class.from_file.return_value = mock_config
        
        mock_pipeline = Mock()
        mock_pipeline.analyze_batch.side_effect = PipelineError("Pipeline failed")
        mock_pipeline_class.return_value = mock_pipeline
        
        # Run command
        runner = CliRunner()
        result = runner.invoke(analyze_command, [
            "--input", str(temp_images_dir),
            "--config", temp_config_file
        ])
        
        # Verify failure
        assert result.exit_code == 1
        assert "❌ Pipeline error: Pipeline failed" in result.output
    
    @patch('vis2attr.cli.analyze.PipelineService')
    @patch('vis2attr.cli.analyze.Config')
    def test_analyze_command_mixed_results(self, mock_config_class, mock_pipeline_class, 
                                         temp_config_file, temp_images_dir, sample_pipeline_results):
        """Test analyze command with mixed success/failure results."""
        # Create mixed results
        failed_result = PipelineResult(
            item_id="item_003",
            success=False,
            error="Processing failed",
            processing_time_ms=500.0
        )
        mixed_results = sample_pipeline_results + [failed_result]
        
        # Setup mocks
        mock_config = Mock()
        mock_config_class.from_file.return_value = mock_config
        
        mock_pipeline = Mock()
        mock_pipeline.analyze_batch.return_value = mixed_results
        mock_pipeline_class.return_value = mock_pipeline
        
        # Run command
        runner = CliRunner()
        result = runner.invoke(analyze_command, [
            "--input", str(temp_images_dir),
            "--config", temp_config_file
        ])
        
        # Verify mixed results
        assert result.exit_code == 0
        assert "✅ Successful: 2" in result.output
        assert "❌ Failed: 1" in result.output
        assert "Failed items:" in result.output
        assert "item_003: Processing failed" in result.output


class TestSaveResultsToParquet:
    """Test the _save_results_to_parquet function."""
    
    def test_save_results_to_parquet(self, sample_pipeline_results, temp_dir):
        """Test saving results to Parquet file."""
        output_path = temp_dir / "test_results.parquet"
        
        # Save results
        _save_results_to_parquet(sample_pipeline_results, output_path)
        
        # Verify file was created
        assert output_path.exists()
        
        # Load and verify data
        df = pd.read_parquet(output_path)
        
        # Check basic columns
        assert "item_id" in df.columns
        assert "timestamp" in df.columns
        assert "processing_time_ms" in df.columns
        assert "success" in df.columns
        assert "decision_accepted" in df.columns
        assert "confidence_score" in df.columns
        
        # Check data
        assert len(df) == 2
        assert df["item_id"].tolist() == ["item_001", "item_002"]
        assert df["success"].all()
        assert df["decision_accepted"].tolist() == [True, False]
        assert df["confidence_score"].tolist() == [0.82, 0.32]
        
        # Check attribute columns
        assert "attr_brand" in df.columns
        assert "conf_brand" in df.columns
        assert "attr_model_or_type" in df.columns
        assert "conf_model_or_type" in df.columns
        assert "attr_condition" in df.columns
        assert "conf_condition" in df.columns
    
    def test_save_results_empty_list(self, temp_dir):
        """Test saving empty results list."""
        output_path = temp_dir / "empty_results.parquet"
        
        # Save empty results
        _save_results_to_parquet([], output_path)
        
        # Verify file was created but is empty
        assert output_path.exists()
        df = pd.read_parquet(output_path)
        assert len(df) == 0


class TestShowSummaryStats:
    """Test the _show_summary_stats function."""
    
    def test_show_summary_stats(self, sample_pipeline_results, capsys):
        """Test showing summary statistics."""
        _show_summary_stats(sample_pipeline_results)
        
        captured = capsys.readouterr()
        output = captured.out
        
        # Check that summary statistics are displayed
        assert "📊 Summary Statistics:" in output
        assert "Total items processed: 2" in output
        assert "Items accepted: 1 (50.0%)" in output
        assert "Average processing time:" in output
        assert "Average confidence:" in output
        assert "Confidence range:" in output
        assert "Provider usage:" in output
    
    def test_show_summary_stats_empty_list(self, capsys):
        """Test showing summary statistics for empty list."""
        _show_summary_stats([])
        
        captured = capsys.readouterr()
        output = captured.out
        
        # Should not crash and should show empty stats
        assert "📊 Summary Statistics:" in output
        assert "Total items processed: 0" in output
        assert "Items accepted: 0" in output
    
    def test_show_summary_stats_no_decisions(self, capsys):
        """Test showing summary statistics when no decisions are present."""
        # Create results without decisions
        result = PipelineResult(
            item_id="test_item",
            success=True,
            processing_time_ms=1000.0
        )
        
        _show_summary_stats([result])
        
        captured = capsys.readouterr()
        output = captured.out
        
        # Should handle missing decisions gracefully
        assert "📊 Summary Statistics:" in output
        assert "Total items processed: 1" in output
        assert "Items accepted: 0" in output


class TestAnalyzeCommandIntegration:
    """Integration tests for the analyze command."""
    
    @patch('vis2attr.cli.analyze.PipelineService')
    @patch('vis2attr.cli.analyze.Config')
    def test_full_workflow_simulation(self, mock_config_class, mock_pipeline_class, 
                                    temp_config_file, temp_images_dir):
        """Test the full workflow simulation."""
        # Create realistic pipeline results
        attributes = Attributes(
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
                "notes": "Slight wear on sole, otherwise excellent condition"
            },
            confidences={
                "brand": 0.85,
                "model_or_type": 0.78,
                "primary_colors": 0.875,
                "materials": 0.775,
                "condition": 0.82
            },
            tags={"sneakers", "athletic", "white", "black"},
            notes="Slight wear on sole, otherwise excellent condition",
            lineage={"provider": "mistral", "model": "pixtral-12b-latest"}
        )
        
        decision = Decision(
            accepted=True,
            field_flags={
                "brand": "accepted",
                "model_or_type": "accepted", 
                "primary_colors": "accepted",
                "materials": "accepted",
                "condition": "accepted"
            },
            reasons=[],
            confidence_score=0.82
        )
        
        raw_response = VLMRaw(
            content='{"brand": {"value": "Nike", "confidence": 0.85}}',
            usage={"prompt_tokens": 150, "completion_tokens": 75},
            latency_ms=1800.0,
            provider="mistral",
            model="pixtral-12b-latest"
        )
        
        result = PipelineResult(
            item_id="nike_air_max_001",
            success=True,
            attributes=attributes,
            raw_response=raw_response,
            decision=decision,
            processing_time_ms=2500.0,
            storage_ids={
                "attributes": "attr_nike_001",
                "raw_response": "raw_nike_001",
                "lineage": "lineage_nike_001"
            }
        )
        
        # Setup mocks
        mock_config = Mock()
        mock_config_class.from_file.return_value = mock_config
        
        mock_pipeline = Mock()
        mock_pipeline.analyze_batch.return_value = [result]
        mock_pipeline_class.return_value = mock_pipeline
        
        # Run command
        runner = CliRunner()
        result_cli = runner.invoke(analyze_command, [
            "--input", str(temp_images_dir),
            "--config", temp_config_file,
            "--output", "nike_analysis.parquet",
            "--verbose"
        ])
        
        # Verify success
        assert result_cli.exit_code == 0
        assert "Analysis completed" in result_cli.output
        assert "✅ Successful: 1" in result_cli.output
        assert "❌ Failed: 0" in result_cli.output
        assert "Results saved successfully!" in result_cli.output
        
        # Verify output file was created
        output_file = Path("nike_analysis.parquet")
        assert output_file.exists()
        
        # Load and verify the saved data
        df = pd.read_parquet(output_file)
        assert len(df) == 1
        assert df["item_id"].iloc[0] == "nike_air_max_001"
        assert df["decision_accepted"].iloc[0] == True
        assert df["confidence_score"].iloc[0] == 0.82
        
        # Clean up
        output_file.unlink()
