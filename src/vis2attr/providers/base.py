"""Base provider interface for VLM providers."""

import os
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from ..core.schemas import VLMRequest, VLMRaw
from ..core.exceptions import VLMError, ConfigurationError, ResourceError


class ProviderError(VLMError):
    """Base exception for provider-related errors."""
    pass


class ProviderConfigError(ConfigurationError):
    """Raised when provider configuration is invalid."""
    pass


class ProviderAPIError(ResourceError):
    """Raised when provider API call fails."""
    pass


class ProviderRateLimitError(ProviderAPIError):
    """Raised when provider rate limit is exceeded."""
    pass


class ProviderTimeoutError(ProviderAPIError):
    """Raised when provider request times out."""
    pass


class Provider(ABC):
    """Abstract base class for VLM providers.
    
    This defines the contract that all VLM providers must implement.
    The interface follows the ports & adapters pattern for easy swapping.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize the provider with configuration.
        
        Args:
            config: Provider-specific configuration dictionary
        """
        self.config = config
        self._validate_config()
    
    def get_api_key(self, key_name: str, required: bool = True) -> str:
        """Get API key from environment variables.
        
        Args:
            key_name: Name of the environment variable containing the API key
            required: Whether the key is required (raises error if missing)
            
        Returns:
            API key value
            
        Raises:
            ProviderConfigError: If required key is not found
        """
        api_key = os.getenv(key_name)
        if required and not api_key:
            raise ProviderConfigError(f"Required API key not found: {key_name}")
        return api_key or ""
    
    @abstractmethod
    def _validate_config(self) -> None:
        """Validate provider configuration.
        
        Raises:
            ProviderConfigError: If configuration is invalid
        """
        pass
    
    @abstractmethod
    def predict(self, request: VLMRequest) -> VLMRaw:
        """Make a prediction request to the VLM provider.
        
        Args:
            request: The VLM request containing model, messages, images, etc.
            
        Returns:
            VLMRaw: Raw response from the provider with content, usage, and metadata
            
        Raises:
            ProviderAPIError: If the API call fails
            ProviderRateLimitError: If rate limit is exceeded
            ProviderTimeoutError: If request times out
        """
        pass
    
    @abstractmethod
    def get_available_models(self) -> list[str]:
        """Get list of available models for this provider.
        
        Returns:
            List of model names available for this provider
        """
        pass
    
    @abstractmethod
    def estimate_cost(self, request: VLMRequest) -> float:
        """Estimate the cost of a request in USD.
        
        Args:
            request: The VLM request to estimate cost for
            
        Returns:
            Estimated cost in USD
        """
        pass
    
    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Get the name of this provider.
        
        Returns:
            Provider name (e.g., 'openai', 'google', 'anthropic')
        """
        pass
    
    @property
    @abstractmethod
    def max_images_per_request(self) -> int:
        """Get the maximum number of images per request.
        
        Returns:
            Maximum number of images supported per request
        """
        pass
    
    @property
    @abstractmethod
    def max_tokens_per_request(self) -> int:
        """Get the maximum number of tokens per request.
        
        Returns:
            Maximum number of tokens supported per request
        """
        pass
