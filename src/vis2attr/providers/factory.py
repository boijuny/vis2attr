"""Factory for creating VLM provider instances."""

from typing import Dict, Any, Type, Optional
from .base import Provider, ProviderError, ProviderConfigError


class ProviderFactory:
    """Factory for creating provider instances based on configuration.
    
    This factory follows the factory pattern to create provider instances
    dynamically based on configuration, enabling easy provider swapping.
    """
    
    _providers: Dict[str, Type[Provider]] = {}
    
    @classmethod
    def register_provider(cls, name: str, provider_class: Type[Provider]) -> None:
        """Register a provider class with the factory.
        
        Args:
            name: Provider name (e.g., 'openai', 'google', 'anthropic')
            provider_class: Provider class that implements the Provider interface
        """
        if not issubclass(provider_class, Provider):
            raise ValueError(f"Provider class must inherit from Provider: {provider_class}")
        
        cls._providers[name] = provider_class
    
    @classmethod
    def create_provider(cls, name: str, config: Dict[str, Any]) -> Provider:
        """Create a provider instance.
        
        Args:
            name: Provider name (e.g., 'openai', 'google', 'anthropic')
            config: Provider-specific configuration
            
        Returns:
            Provider instance
            
        Raises:
            ProviderConfigError: If provider is not registered or config is invalid
        """
        if name not in cls._providers:
            available = list(cls._providers.keys())
            raise ProviderConfigError(
                f"Provider '{name}' is not registered. Available providers: {available}"
            )
        
        provider_class = cls._providers[name]
        
        try:
            return provider_class(config)
        except Exception as e:
            raise ProviderConfigError(
                f"Failed to create provider '{name}': {e}",
                context={"provider": name, "config_keys": list(config.keys())},
                recovery_hint="Check provider configuration and dependencies"
            ) from e
    
    @classmethod
    def get_available_providers(cls) -> list[str]:
        """Get list of available provider names.
        
        Returns:
            List of registered provider names
        """
        return list(cls._providers.keys())
    
    @classmethod
    def is_provider_registered(cls, name: str) -> bool:
        """Check if a provider is registered.
        
        Args:
            name: Provider name to check
            
        Returns:
            True if provider is registered, False otherwise
        """
        return name in cls._providers
    
    @classmethod
    def unregister_provider(cls, name: str) -> None:
        """Unregister a provider.
        
        Args:
            name: Provider name to unregister
        """
        cls._providers.pop(name, None)


# Convenience function for creating providers
def create_provider(name: str, config: Dict[str, Any]) -> Provider:
    """Create a provider instance using the factory.
    
    Args:
        name: Provider name
        config: Provider configuration
        
    Returns:
        Provider instance
    """
    return ProviderFactory.create_provider(name, config)
