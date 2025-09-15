"""Core exception hierarchy for vis2attr.

This module provides a lightweight, minimal exception hierarchy that replaces
generic Exception handling with domain-specific exception types.
"""

from typing import Optional, Dict, Any, List


class VLMError(Exception):
    """Base exception for all vis2attr errors.
    
    This is the root of the exception hierarchy and provides common
    functionality for all domain-specific exceptions.
    """
    
    def __init__(self, message: str, context: Optional[Dict[str, Any]] = None, 
                 recovery_hint: Optional[str] = None):
        """Initialize the exception with message and optional context.
        
        Args:
            message: Human-readable error message
            context: Optional context dictionary with additional error details
            recovery_hint: Optional hint for error recovery
        """
        super().__init__(message)
        self.message = message
        self.context = context or {}
        self.recovery_hint = recovery_hint
    
    def __str__(self) -> str:
        """Return formatted error message with context if available."""
        if self.context:
            context_str = ", ".join(f"{k}={v}" for k, v in self.context.items())
            return f"{self.message} (context: {context_str})"
        return self.message


class ConfigurationError(VLMError):
    """Raised when configuration is invalid or missing."""
    pass


class PipelineError(VLMError):
    """Base exception for pipeline-related errors."""
    pass


class IngestError(VLMError):
    """Base exception for data ingestion errors."""
    pass


class ProcessingError(VLMError):
    """Base exception for data processing errors."""
    pass


class ValidationError(VLMError):
    """Raised when data validation fails."""
    pass


class ResourceError(VLMError):
    """Raised when resource access fails (files, network, etc.)."""
    pass


# Domain-specific exception factories for common patterns
class ErrorFactory:
    """Factory for creating domain-specific exceptions with consistent patterns."""
    
    @staticmethod
    def configuration_error(message: str, config_key: Optional[str] = None, 
                          expected_type: Optional[str] = None) -> ConfigurationError:
        """Create a configuration error with context."""
        context = {}
        if config_key:
            context['config_key'] = config_key
        if expected_type:
            context['expected_type'] = expected_type
        
        return ConfigurationError(
            message=message,
            context=context,
            recovery_hint="Check configuration file and environment variables"
        )
    
    @staticmethod
    def resource_error(message: str, resource_path: Optional[str] = None,
                     operation: Optional[str] = None) -> ResourceError:
        """Create a resource error with context."""
        context = {}
        if resource_path:
            context['resource_path'] = resource_path
        if operation:
            context['operation'] = operation
        
        return ResourceError(
            message=message,
            context=context,
            recovery_hint="Verify resource exists and is accessible"
        )
    
    @staticmethod
    def processing_error(message: str, item_id: Optional[str] = None,
                       stage: Optional[str] = None) -> ProcessingError:
        """Create a processing error with context."""
        context = {}
        if item_id:
            context['item_id'] = item_id
        if stage:
            context['stage'] = stage
        
        return ProcessingError(
            message=message,
            context=context,
            recovery_hint="Check input data and processing configuration"
        )
    
    @staticmethod
    def validation_error(message: str, field: Optional[str] = None,
                        value: Optional[Any] = None) -> ValidationError:
        """Create a validation error with context."""
        context = {}
        if field:
            context['field'] = field
        if value is not None:
            context['value'] = str(value)[:100]  # Truncate long values
        
        return ValidationError(
            message=message,
            context=context,
            recovery_hint="Verify data format and required fields"
        )


# Convenience functions for common error patterns
def wrap_exception(original_exception: Exception, message: str, 
                  context: Optional[Dict[str, Any]] = None) -> VLMError:
    """Wrap a generic exception with domain-specific context.
    
    Args:
        original_exception: The original exception to wrap
        message: Human-readable message describing what went wrong
        context: Optional context dictionary
        
    Returns:
        VLMError: Wrapped exception with context
    """
    if context is None:
        context = {}
    
    # Get the original error message without quotes
    original_msg = str(original_exception)
    if original_msg.startswith("'") and original_msg.endswith("'"):
        original_msg = original_msg[1:-1]
    context['original_error'] = original_msg
    context['original_type'] = type(original_exception).__name__
    
    error = VLMError(
        message=message,
        context=context,
        recovery_hint="Check logs for detailed error information"
    )
    error.__cause__ = original_exception
    error.__suppress_context__ = False
    return error


def create_pipeline_error(message: str, item_id: Optional[str] = None,
                         stage: Optional[str] = None) -> PipelineError:
    """Create a pipeline error with standard context."""
    context = {}
    if item_id:
        context['item_id'] = item_id
    if stage:
        context['stage'] = stage
    
    return PipelineError(
        message=message,
        context=context,
        recovery_hint="Check pipeline configuration and input data"
    )


def create_ingest_error(message: str, file_path: Optional[str] = None,
                       file_type: Optional[str] = None) -> IngestError:
    """Create an ingest error with standard context."""
    context = {}
    if file_path:
        context['file_path'] = file_path
    if file_type:
        context['file_type'] = file_type
    
    return IngestError(
        message=message,
        context=context,
        recovery_hint="Verify file exists and is in supported format"
    )