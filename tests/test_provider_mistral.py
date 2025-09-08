"""Tests for the Mistral provider implementation."""

import pytest
from unittest.mock import Mock, patch
from src.vis2attr.providers import MistralProvider, ProviderConfigError, ProviderAPIError
from src.vis2attr.core.schemas import VLMRequest, VLMRaw


class TestMistralProvider:
    """Test the Mistral provider implementation."""
    
    def test_mistral_provider_validation(self):
        """Test Mistral provider configuration validation."""
        # Valid config
        config = {"model": "pixtral-12b-latest"}
        provider = MistralProvider(config)
        assert provider.config["model"] == "pixtral-12b-latest"
        
        # Test default model
        provider_default = MistralProvider({})
        assert provider_default.config["model"] == "pixtral-12b-latest"
        
        # Invalid config - unsupported model
        with pytest.raises(ProviderConfigError):
            MistralProvider({"model": "unsupported-model"})
    
    def test_mistral_provider_defaults(self):
        """Test Mistral provider default configuration."""
        config = {}
        provider = MistralProvider(config)
        
        assert provider.provider_name == "mistral"
        assert provider.max_images_per_request == 8
        assert provider.max_tokens_per_request == 32000
        assert provider.config["model"] == "pixtral-12b-latest"  # Default model
    
    def test_mistral_provider_available_models(self):
        """Test getting available models."""
        config = {}
        provider = MistralProvider(config)
        
        models = provider.get_available_models()
        expected_models = [
            "pixtral-12b-latest",
            "pixtral-large-latest",
            "mistral-medium-latest",
            "mistral-small-latest"
        ]
        
        for model in expected_models:
            assert model in models
    
    def test_mistral_provider_estimate_cost(self):
        """Test cost estimation."""
        config = {"model": "pixtral-12b-latest"}
        provider = MistralProvider(config)
        
        request = VLMRequest(
            model="pixtral-12b-latest",
            messages=[{"role": "user", "content": "Test"}],
            images=[],
            max_tokens=1000
        )
        
        cost = provider.estimate_cost(request)
        assert cost > 0
        assert isinstance(cost, float)
    
    @patch('src.vis2attr.providers.mistral.Mistral')
    @patch.dict('os.environ', {'MISTRAL_API_KEY': 'test_api_key'})
    def test_mistral_provider_predict_success(self, mock_mistral_class):
        """Test successful prediction."""
        # Mock the Mistral client and response
        mock_client = Mock()
        mock_mistral_class.return_value = mock_client
        
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = '{"brand": "Test Brand", "confidence": 0.9}'
        mock_response.usage.prompt_tokens = 100
        mock_response.usage.completion_tokens = 50
        mock_response.usage.total_tokens = 150
        
        mock_client.chat.complete.return_value = mock_response
        
        # Create provider and request
        config = {"model": "pixtral-12b-latest"}
        provider = MistralProvider(config)
        
        request = VLMRequest(
            model="pixtral-12b-latest",
            messages=[{"role": "user", "content": "Analyze this image"}],
            images=[b"fake_image_data"],
            max_tokens=1000,
            temperature=0.1
        )
        
        # Make prediction
        response = provider.predict(request)
        
        # Verify response
        assert isinstance(response, VLMRaw)
        assert response.provider == "mistral"
        assert response.model == "pixtral-12b-latest"
        assert response.latency_ms > 0
        assert "brand" in response.content
        assert response.usage["total_tokens"] == 150
        
        # Verify API was called correctly
        mock_client.chat.complete.assert_called_once()
        call_args = mock_client.chat.complete.call_args
        assert call_args[1]["model"] == "pixtral-12b-latest"
        assert call_args[1]["max_tokens"] == 1000
        assert call_args[1]["temperature"] == 0.1
    
    @patch('src.vis2attr.providers.mistral.Mistral')
    def test_mistral_provider_predict_api_error(self, mock_mistral_class):
        """Test API error handling."""
        # Mock the Mistral client to raise an exception
        mock_client = Mock()
        mock_mistral_class.return_value = mock_client
        mock_client.chat.complete.side_effect = Exception("API Error")
        
        config = {"model": "pixtral-12b-latest"}
        provider = MistralProvider(config)
        
        request = VLMRequest(
            model="pixtral-12b-latest",
            messages=[{"role": "user", "content": "Test"}],
            images=[],
            max_tokens=1000
        )
        
        with pytest.raises(ProviderAPIError):
            provider.predict(request)
    
    def test_convert_messages_with_bytes(self):
        """Test message conversion with byte images."""
        config = {}
        provider = MistralProvider(config)
        
        messages = [{"role": "user", "content": "What's in this image?"}]
        images = [b"fake_image_data"]
        
        result = provider._convert_messages(messages, images)
        
        assert len(result) == 1
        assert result[0]["role"] == "user"
        assert len(result[0]["content"]) == 2  # text + image
        assert result[0]["content"][0]["type"] == "text"
        assert result[0]["content"][1]["type"] == "image_url"
        assert "data:image/jpeg;base64," in result[0]["content"][1]["image_url"]
    
    def test_convert_messages_with_urls(self):
        """Test message conversion with URL images."""
        config = {}
        provider = MistralProvider(config)
        
        messages = [{"role": "user", "content": "What's in this image?"}]
        images = ["https://example.com/image.jpg"]
        
        result = provider._convert_messages(messages, images)
        
        assert len(result) == 1
        assert result[0]["role"] == "user"
        assert len(result[0]["content"]) == 2  # text + image
        assert result[0]["content"][0]["type"] == "text"
        assert result[0]["content"][1]["type"] == "image_url"
        assert result[0]["content"][1]["image_url"] == "https://example.com/image.jpg"
