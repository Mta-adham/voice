"""
Unit tests for LLM service abstraction layer.

Tests:
- Mock API calls for OpenAI, Gemini, and Claude
- llm_chat() returns standardized format for each provider
- Error handling (rate limits, timeouts, invalid credentials)
- Retry logic with tenacity
- Token usage tracking
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
import openai
import anthropic

from services.llm_service import (
    llm_chat,
    LLMError,
    _call_openai,
    _call_gemini,
    _call_claude
)


class TestLLMChatValidation:
    """Test input validation for llm_chat function."""
    
    def test_llm_chat_invalid_provider(self):
        """Test that invalid provider raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            llm_chat(
                provider="invalid_provider",
                messages=[{"role": "user", "content": "Hello"}]
            )
        
        assert "invalid provider" in str(exc_info.value).lower()
    
    def test_llm_chat_empty_messages(self):
        """Test that empty messages list raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            llm_chat(
                provider="openai",
                messages=[]
            )
        
        assert "cannot be empty" in str(exc_info.value).lower()
    
    def test_llm_chat_invalid_message_format(self):
        """Test that invalid message format raises ValueError."""
        with pytest.raises(ValueError):
            llm_chat(
                provider="openai",
                messages=[{"invalid_key": "value"}]
            )
    
    def test_llm_chat_invalid_role(self):
        """Test that invalid role raises ValueError."""
        with pytest.raises(ValueError):
            llm_chat(
                provider="openai",
                messages=[{"role": "invalid_role", "content": "Hello"}]
            )


class TestOpenAIProvider:
    """Test OpenAI provider integration."""
    
    @patch('services.llm_service.openai.OpenAI')
    @patch('services.llm_service.get_api_key')
    def test_call_openai_success(self, mock_get_api_key, mock_openai_class):
        """Test successful OpenAI API call."""
        # Setup mocks
        mock_get_api_key.return_value = "test_api_key"
        
        mock_client = Mock()
        mock_openai_class.return_value = mock_client
        
        # Mock response
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "Hello! How can I help?"
        mock_response.usage.total_tokens = 25
        
        mock_client.chat.completions.create.return_value = mock_response
        
        # Call function
        result = llm_chat(
            provider="openai",
            messages=[{"role": "user", "content": "Hello"}]
        )
        
        # Verify response format
        assert result["content"] == "Hello! How can I help?"
        assert result["provider"] == "openai"
        assert result["tokens_used"] == 25
        assert isinstance(result["tokens_used"], int)
    
    @patch('services.llm_service.openai.OpenAI')
    @patch('services.llm_service.get_api_key')
    def test_call_openai_with_system_prompt(self, mock_get_api_key, mock_openai_class):
        """Test OpenAI call with system prompt."""
        mock_get_api_key.return_value = "test_api_key"
        
        mock_client = Mock()
        mock_openai_class.return_value = mock_client
        
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "Response"
        mock_response.usage.total_tokens = 20
        
        mock_client.chat.completions.create.return_value = mock_response
        
        result = llm_chat(
            provider="openai",
            messages=[{"role": "user", "content": "Hello"}],
            system_prompt="You are a helpful assistant."
        )
        
        # Verify system prompt was included in API call
        call_args = mock_client.chat.completions.create.call_args
        messages = call_args.kwargs["messages"]
        
        assert messages[0]["role"] == "system"
        assert messages[0]["content"] == "You are a helpful assistant."
    
    @patch('services.llm_service.openai.OpenAI')
    @patch('services.llm_service.get_api_key')
    def test_call_openai_authentication_error(self, mock_get_api_key, mock_openai_class):
        """Test OpenAI authentication error handling."""
        mock_get_api_key.return_value = "invalid_key"
        
        mock_client = Mock()
        mock_openai_class.return_value = mock_client
        
        # Mock authentication error
        mock_client.chat.completions.create.side_effect = openai.AuthenticationError(
            "Invalid API key",
            response=Mock(),
            body=None
        )
        
        with pytest.raises(LLMError) as exc_info:
            llm_chat(
                provider="openai",
                messages=[{"role": "user", "content": "Hello"}]
            )
        
        assert "authentication" in str(exc_info.value).lower()
        assert exc_info.value.provider == "openai"
    
    @patch('services.llm_service.openai.OpenAI')
    @patch('services.llm_service.get_api_key')
    def test_call_openai_rate_limit_retry(self, mock_get_api_key, mock_openai_class):
        """Test OpenAI rate limit error triggers retry."""
        mock_get_api_key.return_value = "test_api_key"
        
        mock_client = Mock()
        mock_openai_class.return_value = mock_client
        
        # Mock rate limit error
        mock_client.chat.completions.create.side_effect = openai.RateLimitError(
            "Rate limit exceeded",
            response=Mock(),
            body=None
        )
        
        with pytest.raises(openai.RateLimitError):
            llm_chat(
                provider="openai",
                messages=[{"role": "user", "content": "Hello"}]
            )
        
        # Verify retry was attempted (should be called 3 times due to tenacity)
        assert mock_client.chat.completions.create.call_count == 3


class TestGeminiProvider:
    """Test Google Gemini provider integration."""
    
    @patch('services.llm_service.genai.GenerativeModel')
    @patch('services.llm_service.genai.configure')
    @patch('services.llm_service.get_api_key')
    def test_call_gemini_success(self, mock_get_api_key, mock_configure, mock_model_class):
        """Test successful Gemini API call."""
        mock_get_api_key.return_value = "test_gemini_key"
        
        mock_model = Mock()
        mock_model_class.return_value = mock_model
        
        # Mock response
        mock_response = Mock()
        mock_response.text = "Hello! I'm here to help."
        
        mock_model.generate_content.return_value = mock_response
        
        result = llm_chat(
            provider="gemini",
            messages=[{"role": "user", "content": "Hello"}]
        )
        
        assert result["content"] == "Hello! I'm here to help."
        assert result["provider"] == "gemini"
        assert result["tokens_used"] > 0
    
    @patch('services.llm_service.genai.GenerativeModel')
    @patch('services.llm_service.genai.configure')
    @patch('services.llm_service.get_api_key')
    def test_call_gemini_with_system_prompt(self, mock_get_api_key, mock_configure, mock_model_class):
        """Test Gemini call with system prompt."""
        mock_get_api_key.return_value = "test_gemini_key"
        
        mock_model = Mock()
        mock_model_class.return_value = mock_model
        
        mock_response = Mock()
        mock_response.text = "Response"
        
        mock_model.generate_content.return_value = mock_response
        
        result = llm_chat(
            provider="gemini",
            messages=[{"role": "user", "content": "Hello"}],
            system_prompt="You are a helpful assistant."
        )
        
        # Verify system prompt was included
        call_args = mock_model.generate_content.call_args
        conversation_text = call_args[0][0]
        
        assert "System: You are a helpful assistant." in conversation_text
    
    @patch('services.llm_service.genai.GenerativeModel')
    @patch('services.llm_service.genai.configure')
    @patch('services.llm_service.get_api_key')
    def test_call_gemini_error_handling(self, mock_get_api_key, mock_configure, mock_model_class):
        """Test Gemini error handling."""
        mock_get_api_key.return_value = "test_gemini_key"
        
        mock_model = Mock()
        mock_model_class.return_value = mock_model
        
        # Mock API error
        mock_model.generate_content.side_effect = Exception("API Error")
        
        with pytest.raises(LLMError) as exc_info:
            llm_chat(
                provider="gemini",
                messages=[{"role": "user", "content": "Hello"}]
            )
        
        assert exc_info.value.provider == "gemini"


class TestClaudeProvider:
    """Test Anthropic Claude provider integration."""
    
    @patch('services.llm_service.anthropic.Anthropic')
    @patch('services.llm_service.get_api_key')
    def test_call_claude_success(self, mock_get_api_key, mock_anthropic_class):
        """Test successful Claude API call."""
        mock_get_api_key.return_value = "test_claude_key"
        
        mock_client = Mock()
        mock_anthropic_class.return_value = mock_client
        
        # Mock response
        mock_response = Mock()
        mock_response.content = [Mock()]
        mock_response.content[0].text = "Hello! How may I assist you?"
        mock_response.usage = Mock()
        mock_response.usage.input_tokens = 10
        mock_response.usage.output_tokens = 15
        
        mock_client.messages.create.return_value = mock_response
        
        result = llm_chat(
            provider="claude",
            messages=[{"role": "user", "content": "Hello"}]
        )
        
        assert result["content"] == "Hello! How may I assist you?"
        assert result["provider"] == "claude"
        assert result["tokens_used"] == 25  # 10 + 15
    
    @patch('services.llm_service.anthropic.Anthropic')
    @patch('services.llm_service.get_api_key')
    def test_call_claude_with_system_prompt(self, mock_get_api_key, mock_anthropic_class):
        """Test Claude call with system prompt."""
        mock_get_api_key.return_value = "test_claude_key"
        
        mock_client = Mock()
        mock_anthropic_class.return_value = mock_client
        
        mock_response = Mock()
        mock_response.content = [Mock()]
        mock_response.content[0].text = "Response"
        mock_response.usage = Mock()
        mock_response.usage.input_tokens = 10
        mock_response.usage.output_tokens = 10
        
        mock_client.messages.create.return_value = mock_response
        
        result = llm_chat(
            provider="claude",
            messages=[{"role": "user", "content": "Hello"}],
            system_prompt="You are a helpful assistant."
        )
        
        # Verify system prompt was passed
        call_args = mock_client.messages.create.call_args
        
        assert "system" in call_args.kwargs
        assert call_args.kwargs["system"] == "You are a helpful assistant."
    
    @patch('services.llm_service.anthropic.Anthropic')
    @patch('services.llm_service.get_api_key')
    def test_call_claude_authentication_error(self, mock_get_api_key, mock_anthropic_class):
        """Test Claude authentication error handling."""
        mock_get_api_key.return_value = "invalid_key"
        
        mock_client = Mock()
        mock_anthropic_class.return_value = mock_client
        
        # Mock authentication error
        mock_client.messages.create.side_effect = anthropic.AuthenticationError(
            "Invalid API key",
            response=Mock(),
            body=None
        )
        
        with pytest.raises(LLMError) as exc_info:
            llm_chat(
                provider="claude",
                messages=[{"role": "user", "content": "Hello"}]
            )
        
        assert "authentication" in str(exc_info.value).lower()
        assert exc_info.value.provider == "claude"
    
    @patch('services.llm_service.anthropic.Anthropic')
    @patch('services.llm_service.get_api_key')
    def test_call_claude_rate_limit_retry(self, mock_get_api_key, mock_anthropic_class):
        """Test Claude rate limit error triggers retry."""
        mock_get_api_key.return_value = "test_claude_key"
        
        mock_client = Mock()
        mock_anthropic_class.return_value = mock_client
        
        # Mock rate limit error
        mock_client.messages.create.side_effect = anthropic.RateLimitError(
            "Rate limit exceeded",
            response=Mock(),
            body=None
        )
        
        with pytest.raises(anthropic.RateLimitError):
            llm_chat(
                provider="claude",
                messages=[{"role": "user", "content": "Hello"}]
            )
        
        # Verify retry was attempted
        assert mock_client.messages.create.call_count == 3


class TestLLMChatIntegration:
    """Test llm_chat function integration with all providers."""
    
    @patch('services.llm_service._call_openai')
    def test_llm_chat_routes_to_openai(self, mock_call_openai):
        """Test that llm_chat routes to OpenAI provider."""
        mock_call_openai.return_value = {
            "content": "Response",
            "provider": "openai",
            "tokens_used": 20
        }
        
        result = llm_chat(
            provider="openai",
            messages=[{"role": "user", "content": "Hello"}]
        )
        
        assert result["provider"] == "openai"
        mock_call_openai.assert_called_once()
    
    @patch('services.llm_service._call_gemini')
    def test_llm_chat_routes_to_gemini(self, mock_call_gemini):
        """Test that llm_chat routes to Gemini provider."""
        mock_call_gemini.return_value = {
            "content": "Response",
            "provider": "gemini",
            "tokens_used": 20
        }
        
        result = llm_chat(
            provider="gemini",
            messages=[{"role": "user", "content": "Hello"}]
        )
        
        assert result["provider"] == "gemini"
        mock_call_gemini.assert_called_once()
    
    @patch('services.llm_service._call_claude')
    def test_llm_chat_routes_to_claude(self, mock_call_claude):
        """Test that llm_chat routes to Claude provider."""
        mock_call_claude.return_value = {
            "content": "Response",
            "provider": "claude",
            "tokens_used": 20
        }
        
        result = llm_chat(
            provider="claude",
            messages=[{"role": "user", "content": "Hello"}]
        )
        
        assert result["provider"] == "claude"
        mock_call_claude.assert_called_once()
    
    @patch('services.llm_service._call_openai')
    def test_llm_chat_temperature_parameter(self, mock_call_openai):
        """Test that temperature parameter is passed correctly."""
        mock_call_openai.return_value = {
            "content": "Response",
            "provider": "openai",
            "tokens_used": 20
        }
        
        llm_chat(
            provider="openai",
            messages=[{"role": "user", "content": "Hello"}],
            temperature=0.9
        )
        
        call_args = mock_call_openai.call_args
        assert call_args[0][2] == 0.9  # temperature is 3rd positional arg
    
    @patch('services.llm_service._call_openai')
    def test_llm_chat_max_tokens_parameter(self, mock_call_openai):
        """Test that max_tokens parameter is passed correctly."""
        mock_call_openai.return_value = {
            "content": "Response",
            "provider": "openai",
            "tokens_used": 20
        }
        
        llm_chat(
            provider="openai",
            messages=[{"role": "user", "content": "Hello"}],
            max_tokens=1000
        )
        
        call_args = mock_call_openai.call_args
        assert call_args[0][3] == 1000  # max_tokens is 4th positional arg
