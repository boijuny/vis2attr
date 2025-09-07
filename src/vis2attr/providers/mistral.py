"""Mistral AI provider implementation for vision capabilities."""

import base64
import time
from typing import Dict, Any, List, Union
from mistralai import Mistral
from .base import Provider, ProviderAPIError, ProviderConfigError, ProviderRateLimitError, ProviderTimeoutError
from ..core.schemas import VLMRequest, VLMRaw


class MistralProvider(Provider):
    """Mistral AI provider implementation for vision capabilities.
    
    Supports the following Mistral vision models:
    - pixtral-12b-latest
    - pixtral-large-latest  
    - mistral-medium-latest
    - mistral-small-latest
    """
    
    def _validate_config(self) -> None:
        """Validate Mistral provider configuration."""
        required_keys = ["api_key"]
        for key in required_keys:
            if key not in self.config:
                raise ProviderConfigError(f"Missing required config key: {key}")
        
        # Set default model if not provided
        if "model" not in self.config:
            self.config["model"] = "pixtral-12b-latest"
        
        # Validate model is supported
        supported_models = self.get_available_models()
        if self.config["model"] not in supported_models:
            raise ProviderConfigError(
                f"Unsupported model: {self.config['model']}. "
                f"Supported models: {supported_models}"
            )
    
    def predict(self, request: VLMRequest) -> VLMRaw:
        """Make a prediction request to Mistral AI.
        
        Args:
            request: The VLM request containing model, messages, images, etc.
            
        Returns:
            VLMRaw: Raw response from Mistral AI
            
        Raises:
            ProviderAPIError: If the API call fails
            ProviderRateLimitError: If rate limit is exceeded
            ProviderTimeoutError: If request times out
        """
        try:
            # Initialize Mistral client
            client = Mistral(api_key=self.config["api_key"])
            
            # Convert images to Mistral format
            mistral_messages = self._convert_messages(request.messages, request.images)
            
            # Record start time for latency calculation
            start_time = time.time()
            
            # Make the API call
            response = client.chat.complete(
                model=request.model,
                messages=mistral_messages,
                max_tokens=request.max_tokens,
                temperature=request.temperature
            )
            
            # Calculate latency
            latency_ms = (time.time() - start_time) * 1000
            
            # Extract response content
            content = response.choices[0].message.content
            
            # Extract usage information
            usage = {
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens,
                "cost_usd": self._calculate_cost(response.usage, request.model)
            }
            
            return VLMRaw(
                content=content,
                usage=usage,
                latency_ms=latency_ms,
                provider=self.provider_name,
                model=request.model
            )
            
        except Exception as e:
            # Map common exceptions to our provider exceptions
            error_msg = str(e).lower()
            if "rate limit" in error_msg or "quota" in error_msg:
                raise ProviderRateLimitError(f"Mistral rate limit exceeded: {e}") from e
            elif "timeout" in error_msg:
                raise ProviderTimeoutError(f"Mistral request timeout: {e}") from e
            else:
                raise ProviderAPIError(f"Mistral API error: {e}") from e
    
    def get_available_models(self) -> List[str]:
        """Get available Mistral vision models."""
        return [
            "pixtral-12b-latest",
            "pixtral-large-latest",
            "mistral-medium-latest", 
            "mistral-small-latest"
        ]
    
    def estimate_cost(self, request: VLMRequest) -> float:
        """Estimate cost for Mistral API call.
        
        Note: This is a rough estimate. Actual costs may vary.
        """
        # Rough cost estimation based on Mistral pricing
        # These are approximate values - actual pricing may differ
        model_costs = {
            "pixtral-12b-latest": 0.0003,  # per 1K tokens
            "pixtral-large-latest": 0.0006,
            "mistral-medium-latest": 0.0004,
            "mistral-small-latest": 0.0002
        }
        
        cost_per_1k = model_costs.get(request.model, 0.0003)
        estimated_tokens = request.max_tokens + 100  # Add some overhead
        return (estimated_tokens / 1000) * cost_per_1k
    
    @property
    def provider_name(self) -> str:
        """Get provider name."""
        return "mistral"
    
    @property
    def max_images_per_request(self) -> int:
        """Get maximum images per request."""
        return 8  # Mistral supports up to 8 images per request
    
    @property
    def max_tokens_per_request(self) -> int:
        """Get maximum tokens per request."""
        return 32000  # Conservative estimate for Mistral models
    
    def _convert_messages(self, messages: List[Dict[str, Any]], images: List[Union[bytes, str]]) -> List[Dict[str, Any]]:
        """Convert VLMRequest messages to Mistral format.
        
        Args:
            messages: List of message dictionaries
            images: List of image data (bytes or URLs)
            
        Returns:
            List of messages in Mistral format
        """
        mistral_messages = []
        
        for message in messages:
            mistral_message = {"role": message["role"]}
            
            if "content" in message:
                # If content is a string, wrap it in the Mistral format
                if isinstance(message["content"], str):
                    content_parts = [{"type": "text", "text": message["content"]}]
                else:
                    content_parts = message["content"]
                
                # Add images to the content
                for image in images:
                    if isinstance(image, bytes):
                        # Convert bytes to base64
                        base64_image = base64.b64encode(image).decode('utf-8')
                        content_parts.append({
                            "type": "image_url",
                            "image_url": f"data:image/jpeg;base64,{base64_image}"
                        })
                    elif isinstance(image, str):
                        # Assume it's a URL
                        content_parts.append({
                            "type": "image_url", 
                            "image_url": image
                        })
                
                mistral_message["content"] = content_parts
            
            mistral_messages.append(mistral_message)
        
        return mistral_messages
    
    def _calculate_cost(self, usage: Any, model: str) -> float:
        """Calculate actual cost based on usage.
        
        Args:
            usage: Mistral usage object
            model: Model name used
            
        Returns:
            Estimated cost in USD
        """
        # Rough cost estimation - actual pricing may vary
        model_costs = {
            "pixtral-12b-latest": 0.0003,
            "pixtral-large-latest": 0.0006, 
            "mistral-medium-latest": 0.0004,
            "mistral-small-latest": 0.0002
        }
        
        cost_per_1k = model_costs.get(model, 0.0003)
        total_tokens = usage.total_tokens
        return (total_tokens / 1000) * cost_per_1k
