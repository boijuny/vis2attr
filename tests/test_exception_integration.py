"""Integration tests for exception handling across the vis2attr system."""

import pytest
from unittest.mock import Mock, patch
from pathlib import Path

from vis2attr.core.exceptions import (
    VLMError, ConfigurationError, PipelineError, IngestError,
    ProcessingError, ValidationError, ResourceError, wrap_exception
)
from vis2attr.providers.base import ProviderError, ProviderConfigError, ProviderAPIError
from vis2attr.parse.base import ParseError
from vis2attr.storage.base import StorageError


class TestProviderExceptionIntegration:
    """Test exception handling in provider modules."""
    
    def test_provider_error_inheritance(self):
        """Test that provider errors inherit from VLMError."""
        assert issubclass(ProviderError, VLMError)
        assert issubclass(ProviderConfigError, ConfigurationError)
        assert issubclass(ProviderAPIError, ResourceError)
    
    def test_provider_config_error_with_context(self):
        """Test provider config error with context."""
        error = ProviderConfigError(
            "Invalid API key",
            context={"provider": "mistral", "config_key": "api_key"},
            recovery_hint="Set MISTRAL_API_KEY environment variable"
        )
        assert isinstance(error, VLMError)
        assert isinstance(error, ConfigurationError)
        assert error.context["provider"] == "mistral"
        assert "MISTRAL_API_KEY" in error.recovery_hint
    
    def test_provider_api_error_with_context(self):
        """Test provider API error with context."""
        error = ProviderAPIError(
            "API request failed",
            context={"provider": "mistral", "status_code": 429},
            recovery_hint="Check rate limits and retry"
        )
        assert isinstance(error, VLMError)
        assert isinstance(error, ResourceError)
        assert error.context["status_code"] == 429


class TestParseExceptionIntegration:
    """Test exception handling in parse modules."""
    
    def test_parse_error_inheritance(self):
        """Test that parse errors inherit from VLMError."""
        assert issubclass(ParseError, ProcessingError)
        assert issubclass(ParseError, VLMError)
    
    def test_parse_error_with_context(self):
        """Test parse error with context."""
        error = ParseError(
            "Failed to parse JSON response",
            context={
                "provider": "mistral",
                "model": "pixtral-12b-latest",
                "content_length": 1500
            },
            recovery_hint="Check response format and schema compatibility"
        )
        assert isinstance(error, VLMError)
        assert isinstance(error, ProcessingError)
        assert error.context["provider"] == "mistral"
        assert error.context["content_length"] == 1500


class TestStorageExceptionIntegration:
    """Test exception handling in storage modules."""
    
    def test_storage_error_inheritance(self):
        """Test that storage errors inherit from VLMError."""
        assert issubclass(StorageError, ResourceError)
        assert issubclass(StorageError, VLMError)
    
    def test_storage_error_with_context(self):
        """Test storage error with context."""
        error = StorageError(
            "Failed to write file",
            context={"item_id": "item_123", "operation": "store_attributes"},
            recovery_hint="Check storage permissions and disk space"
        )
        assert isinstance(error, VLMError)
        assert isinstance(error, ResourceError)
        assert error.context["item_id"] == "item_123"
        assert error.context["operation"] == "store_attributes"


class TestPipelineExceptionIntegration:
    """Test exception handling in pipeline service."""
    
    def test_pipeline_error_inheritance(self):
        """Test that pipeline errors inherit from VLMError."""
        assert issubclass(PipelineError, VLMError)
    
    def test_pipeline_error_with_context(self):
        """Test pipeline error with context."""
        error = PipelineError(
            "Pipeline initialization failed",
            context={"stage": "provider_setup", "provider": "mistral"},
            recovery_hint="Check provider configuration and dependencies"
        )
        assert isinstance(error, VLMError)
        assert error.context["stage"] == "provider_setup"
        assert error.context["provider"] == "mistral"


class TestExceptionWrappingIntegration:
    """Test exception wrapping in real scenarios."""
    
    def test_wrap_provider_exception(self):
        """Test wrapping a provider exception."""
        original = ConnectionError("Connection failed")
        wrapped = wrap_exception(
            original,
            "Provider communication failed",
            {"provider": "mistral", "endpoint": "https://api.mistral.ai"}
        )
        
        assert isinstance(wrapped, VLMError)
        assert wrapped.context["provider"] == "mistral"
        assert wrapped.context["original_error"] == "Connection failed"
        assert wrapped.__cause__ is original
    
    def test_wrap_parse_exception(self):
        """Test wrapping a parse exception."""
        original = ValueError("Invalid JSON")
        wrapped = wrap_exception(
            original,
            "Response parsing failed",
            {"parser": "json", "content_type": "application/json"}
        )
        
        assert isinstance(wrapped, VLMError)
        assert wrapped.context["parser"] == "json"
        assert wrapped.context["original_type"] == "ValueError"
    
    def test_wrap_storage_exception(self):
        """Test wrapping a storage exception."""
        original = PermissionError("Permission denied")
        wrapped = wrap_exception(
            original,
            "Storage operation failed",
            {"operation": "write", "path": "/storage/data"}
        )
        
        assert isinstance(wrapped, VLMError)
        assert wrapped.context["operation"] == "write"
        assert wrapped.context["path"] == "/storage/data"


class TestExceptionHierarchyConsistency:
    """Test that exception hierarchy is consistent across modules."""
    
    def test_all_domain_exceptions_inherit_from_vlm_error(self):
        """Test that all domain exceptions inherit from VLMError."""
        domain_exceptions = [
            ConfigurationError, PipelineError, IngestError,
            ProcessingError, ValidationError, ResourceError,
            ProviderError, ParseError, StorageError
        ]
        
        for exc_class in domain_exceptions:
            assert issubclass(exc_class, VLMError), f"{exc_class} should inherit from VLMError"
    
    def test_exception_context_consistency(self):
        """Test that exception context is handled consistently."""
        # Test that all exceptions support context parameter
        exceptions = [
            ConfigurationError, PipelineError, IngestError,
            ProcessingError, ValidationError, ResourceError
        ]
        
        for exc_class in exceptions:
            error = exc_class("Test", context={"key": "value"})
            assert error.context == {"key": "value"}
    
    def test_exception_recovery_hint_consistency(self):
        """Test that exception recovery hints are handled consistently."""
        exceptions = [
            ConfigurationError, PipelineError, IngestError,
            ProcessingError, ValidationError, ResourceError
        ]
        
        for exc_class in exceptions:
            error = exc_class("Test", recovery_hint="Try again")
            assert error.recovery_hint == "Try again"


class TestExceptionChainingIntegration:
    """Test exception chaining in integration scenarios."""
    
    def test_provider_to_pipeline_exception_chain(self):
        """Test exception chaining from provider to pipeline."""
        try:
            try:
                raise ProviderAPIError("Rate limit exceeded")
            except ProviderAPIError as e:
                raise wrap_exception(e, "Provider call failed") from e
        except VLMError as e:
            assert isinstance(e, VLMError)
            assert e.__cause__ is not None
            assert isinstance(e.__cause__, ProviderAPIError)
            assert "Rate limit exceeded" in e.context["original_error"]
    
    def test_parse_to_pipeline_exception_chain(self):
        """Test exception chaining from parse to pipeline."""
        try:
            try:
                raise ParseError("Invalid JSON format")
            except ParseError as e:
                raise wrap_exception(e, "Response parsing failed") from e
        except VLMError as e:
            assert isinstance(e, VLMError)
            assert e.__cause__ is not None
            assert isinstance(e.__cause__, ParseError)
            assert "Invalid JSON format" in e.context["original_error"]
    
    def test_storage_to_pipeline_exception_chain(self):
        """Test exception chaining from storage to pipeline."""
        try:
            try:
                raise StorageError("Disk full")
            except StorageError as e:
                raise wrap_exception(e, "Storage operation failed") from e
        except VLMError as e:
            assert isinstance(e, VLMError)
            assert e.__cause__ is not None
            assert isinstance(e.__cause__, StorageError)
            assert "Disk full" in e.context["original_error"]


class TestExceptionContextPreservation:
    """Test that context is preserved through exception chains."""
    
    def test_context_accumulation(self):
        """Test that context accumulates through exception chains."""
        try:
            try:
                original = ValueError("Original error")
                raise original
            except Exception as e:
                wrapped1 = wrap_exception(e, "First wrap", {"stage": "initialization"})
                raise wrapped1
        except VLMError as e:
            try:
                wrapped2 = wrap_exception(e, "Second wrap", {"stage": "processing"})
                raise wrapped2
            except VLMError as final:
                assert final.context["stage"] == "processing"  # Latest context
                # When wrapping a wrapped exception, we get the string representation of the wrapped exception
                # The original error should be preserved in the context of the first wrapped exception
                assert "Original error" in final.context["original_error"]
                # When wrapping a wrapped exception, the immediate original type is VLMError
                # but the original ValueError is preserved in the exception chain
                assert final.context["original_type"] == "VLMError"
                # Check that we have the chain
                assert final.__cause__ is e
                assert e.__cause__ is original


if __name__ == "__main__":
    pytest.main([__file__])
