"""Tests for the core exception handling system."""

import pytest
from vis2attr.core.exceptions import (
    VLMError, ConfigurationError, PipelineError, IngestError,
    ProcessingError, ValidationError, ResourceError, ErrorFactory,
    wrap_exception, create_pipeline_error, create_ingest_error
)


class TestVLMError:
    """Test the base VLMError class."""
    
    def test_basic_error_creation(self):
        """Test basic error creation with message only."""
        error = VLMError("Test error message")
        assert str(error) == "Test error message"
        assert error.message == "Test error message"
        assert error.context == {}
        assert error.recovery_hint is None
    
    def test_error_with_context(self):
        """Test error creation with context."""
        context = {"key1": "value1", "key2": 42}
        error = VLMError("Test error", context=context)
        assert error.context == context
        assert "key1=value1" in str(error)
        assert "key2=42" in str(error)
    
    def test_error_with_recovery_hint(self):
        """Test error creation with recovery hint."""
        error = VLMError("Test error", recovery_hint="Try again")
        assert error.recovery_hint == "Try again"
    
    def test_error_with_all_parameters(self):
        """Test error creation with all parameters."""
        context = {"stage": "initialization", "item_id": "test_123"}
        error = VLMError(
            "Complete error",
            context=context,
            recovery_hint="Check configuration"
        )
        assert error.message == "Complete error"
        assert error.context == context
        assert error.recovery_hint == "Check configuration"
        assert "stage=initialization" in str(error)
        assert "item_id=test_123" in str(error)


class TestDomainExceptions:
    """Test domain-specific exception classes."""
    
    def test_configuration_error_inheritance(self):
        """Test that ConfigurationError inherits from VLMError."""
        error = ConfigurationError("Config error")
        assert isinstance(error, VLMError)
        assert isinstance(error, ConfigurationError)
    
    def test_pipeline_error_inheritance(self):
        """Test that PipelineError inherits from VLMError."""
        error = PipelineError("Pipeline error")
        assert isinstance(error, VLMError)
        assert isinstance(error, PipelineError)
    
    def test_ingest_error_inheritance(self):
        """Test that IngestError inherits from VLMError."""
        error = IngestError("Ingest error")
        assert isinstance(error, VLMError)
        assert isinstance(error, IngestError)
    
    def test_processing_error_inheritance(self):
        """Test that ProcessingError inherits from VLMError."""
        error = ProcessingError("Processing error")
        assert isinstance(error, VLMError)
        assert isinstance(error, ProcessingError)
    
    def test_validation_error_inheritance(self):
        """Test that ValidationError inherits from VLMError."""
        error = ValidationError("Validation error")
        assert isinstance(error, VLMError)
        assert isinstance(error, ValidationError)
    
    def test_resource_error_inheritance(self):
        """Test that ResourceError inherits from VLMError."""
        error = ResourceError("Resource error")
        assert isinstance(error, VLMError)
        assert isinstance(error, ResourceError)


class TestErrorFactory:
    """Test the ErrorFactory convenience methods."""
    
    def test_configuration_error_factory(self):
        """Test configuration error factory method."""
        error = ErrorFactory.configuration_error(
            "Missing API key",
            config_key="MISTRAL_API_KEY",
            expected_type="string"
        )
        assert isinstance(error, ConfigurationError)
        assert "Missing API key" in str(error)
        assert error.context["config_key"] == "MISTRAL_API_KEY"
        assert error.context["expected_type"] == "string"
        assert "Check configuration file" in error.recovery_hint
    
    def test_resource_error_factory(self):
        """Test resource error factory method."""
        error = ErrorFactory.resource_error(
            "File not found",
            resource_path="/path/to/file.jpg",
            operation="read"
        )
        assert isinstance(error, ResourceError)
        assert "File not found" in str(error)
        assert error.context["resource_path"] == "/path/to/file.jpg"
        assert error.context["operation"] == "read"
        assert "accessible" in error.recovery_hint
    
    def test_processing_error_factory(self):
        """Test processing error factory method."""
        error = ErrorFactory.processing_error(
            "Failed to parse",
            item_id="item_123",
            stage="attribute_extraction"
        )
        assert isinstance(error, ProcessingError)
        assert "Failed to parse" in str(error)
        assert error.context["item_id"] == "item_123"
        assert error.context["stage"] == "attribute_extraction"
        assert "input data" in error.recovery_hint
    
    def test_validation_error_factory(self):
        """Test validation error factory method."""
        error = ErrorFactory.validation_error(
            "Invalid value",
            field="confidence",
            value=1.5
        )
        assert isinstance(error, ValidationError)
        assert "Invalid value" in str(error)
        assert error.context["field"] == "confidence"
        assert error.context["value"] == "1.5"  # Truncated string
        assert "data format" in error.recovery_hint


class TestWrapException:
    """Test the wrap_exception utility function."""
    
    def test_wrap_basic_exception(self):
        """Test wrapping a basic exception."""
        original = ValueError("Original error")
        wrapped = wrap_exception(original, "Wrapped message")
        
        assert isinstance(wrapped, VLMError)
        assert "Wrapped message" in str(wrapped)
        assert wrapped.context["original_error"] == "Original error"
        assert wrapped.context["original_type"] == "ValueError"
        assert wrapped.__cause__ is original
    
    def test_wrap_with_context(self):
        """Test wrapping with additional context."""
        original = FileNotFoundError("File not found")
        context = {"file_path": "/test/path", "operation": "read"}
        wrapped = wrap_exception(original, "Processing failed", context)
        
        assert wrapped.context["file_path"] == "/test/path"
        assert wrapped.context["operation"] == "read"
        assert wrapped.context["original_error"] == "File not found"
        assert wrapped.context["original_type"] == "FileNotFoundError"
    
    def test_wrap_preserves_cause(self):
        """Test that exception chaining is preserved."""
        original = RuntimeError("Original")
        wrapped = wrap_exception(original, "Wrapped")
        
        assert wrapped.__cause__ is original
        assert wrapped.__suppress_context__ is False


class TestConvenienceFunctions:
    """Test convenience functions for common patterns."""
    
    def test_create_pipeline_error(self):
        """Test create_pipeline_error function."""
        error = create_pipeline_error(
            "Analysis failed",
            item_id="item_456",
            stage="provider_call"
        )
        assert isinstance(error, PipelineError)
        assert "Analysis failed" in str(error)
        assert error.context["item_id"] == "item_456"
        assert error.context["stage"] == "provider_call"
        assert "pipeline configuration" in error.recovery_hint
    
    def test_create_ingest_error(self):
        """Test create_ingest_error function."""
        error = create_ingest_error(
            "Image processing failed",
            file_path="/path/to/image.png",
            file_type=".png"
        )
        assert isinstance(error, IngestError)
        assert "Image processing failed" in str(error)
        assert error.context["file_path"] == "/path/to/image.png"
        assert error.context["file_type"] == ".png"
        assert "supported format" in error.recovery_hint
    
    def test_create_pipeline_error_minimal(self):
        """Test create_pipeline_error with minimal parameters."""
        error = create_pipeline_error("Simple error")
        assert isinstance(error, PipelineError)
        assert "Simple error" in str(error)
        assert error.context == {}


class TestExceptionChaining:
    """Test exception chaining and context preservation."""
    
    def test_exception_chain(self):
        """Test that exceptions can be chained properly."""
        try:
            try:
                raise ValueError("Original error")
            except Exception as e:
                raise wrap_exception(e, "Wrapped error") from e
        except VLMError as e:
            assert e.__cause__ is not None
            assert isinstance(e.__cause__, ValueError)
            assert str(e.__cause__) == "Original error"
    
    def test_context_preservation(self):
        """Test that context is preserved through exception chains."""
        original = KeyError("Missing key")
        wrapped = wrap_exception(original, "Processing failed", {"stage": "parsing"})
        
        assert wrapped.context["stage"] == "parsing"
        assert wrapped.context["original_error"] == "Missing key"
        assert wrapped.context["original_type"] == "KeyError"


class TestErrorStringRepresentation:
    """Test string representation of errors."""
    
    def test_simple_error_string(self):
        """Test string representation without context."""
        error = VLMError("Simple error")
        assert str(error) == "Simple error"
    
    def test_error_with_context_string(self):
        """Test string representation with context."""
        error = VLMError("Error with context", context={"key": "value"})
        assert "Error with context" in str(error)
        assert "key=value" in str(error)
    
    def test_error_with_multiple_context_items(self):
        """Test string representation with multiple context items."""
        error = VLMError(
            "Complex error",
            context={"item_id": "123", "stage": "processing", "count": 42}
        )
        error_str = str(error)
        assert "Complex error" in error_str
        assert "item_id=123" in error_str
        assert "stage=processing" in error_str
        assert "count=42" in error_str


class TestErrorFactoryEdgeCases:
    """Test edge cases for ErrorFactory methods."""
    
    def test_configuration_error_no_optional_params(self):
        """Test configuration error with no optional parameters."""
        error = ErrorFactory.configuration_error("Basic config error")
        assert isinstance(error, ConfigurationError)
        assert error.context == {}
    
    def test_resource_error_no_optional_params(self):
        """Test resource error with no optional parameters."""
        error = ErrorFactory.resource_error("Basic resource error")
        assert isinstance(error, ResourceError)
        assert error.context == {}
    
    def test_processing_error_no_optional_params(self):
        """Test processing error with no optional parameters."""
        error = ErrorFactory.processing_error("Basic processing error")
        assert isinstance(error, ProcessingError)
        assert error.context == {}
    
    def test_validation_error_no_optional_params(self):
        """Test validation error with no optional parameters."""
        error = ErrorFactory.validation_error("Basic validation error")
        assert isinstance(error, ValidationError)
        assert error.context == {}


if __name__ == "__main__":
    pytest.main([__file__])
