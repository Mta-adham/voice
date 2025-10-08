"""
Configuration module for restaurant booking system.

Loads environment variables and provides configuration settings including
API keys for LLM providers.
"""
import os
from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    
    Attributes:
        database_url: PostgreSQL connection string
        openai_api_key: Optional OpenAI API key
        gemini_api_key: Optional Google Gemini API key
        anthropic_api_key: Optional Anthropic Claude API key
    """
    
    # Database configuration
    database_url: str = Field(
        alias="DATABASE_URL",
        description="PostgreSQL connection string"
    )
    
    # LLM Provider API Keys
    openai_api_key: Optional[str] = Field(
        default=None,
        alias="OPENAI_API_KEY",
        description="OpenAI API key for GPT models"
    )
    
    gemini_api_key: Optional[str] = Field(
        default=None,
        alias="GEMINI_API_KEY",
        description="Google Gemini API key"
    )
    
    anthropic_api_key: Optional[str] = Field(
        default=None,
        alias="ANTHROPIC_API_KEY",
        description="Anthropic Claude API key"
    )
    
    # Twilio SMS Configuration
    twilio_account_sid: Optional[str] = Field(
        default=None,
        alias="TWILIO_ACCOUNT_SID",
        description="Twilio Account SID"
    )
    
    twilio_auth_token: Optional[str] = Field(
        default=None,
        alias="TWILIO_AUTH_TOKEN",
        description="Twilio Auth Token"
    )
    
    twilio_phone_number: Optional[str] = Field(
        default=None,
        alias="TWILIO_PHONE_NUMBER",
        description="Twilio phone number (sender)"
    )
    
    # Restaurant Configuration
    restaurant_name: str = Field(
        default="Our Restaurant",
        alias="RESTAURANT_NAME",
        description="Restaurant name for confirmations"
    )
    
    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"


# Global settings instance
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """
    Get or create the global settings instance.
    
    Returns:
        Settings instance with loaded configuration
    
    Raises:
        ValueError: If DATABASE_URL is not set
    """
    global _settings
    
    if _settings is None:
        _settings = Settings()
    
    return _settings


def get_api_key(provider: str) -> str:
    """
    Get API key for a specific LLM provider.
    
    Args:
        provider: Provider name ("openai", "gemini", or "claude")
    
    Returns:
        API key string
    
    Raises:
        ValueError: If API key is not configured for the provider
    """
    settings = get_settings()
    
    if provider == "openai":
        if not settings.openai_api_key:
            raise ValueError(
                "OpenAI API key not configured. "
                "Please set OPENAI_API_KEY environment variable."
            )
        return settings.openai_api_key
    
    elif provider == "gemini":
        if not settings.gemini_api_key:
            raise ValueError(
                "Gemini API key not configured. "
                "Please set GEMINI_API_KEY environment variable."
            )
        return settings.gemini_api_key
    
    elif provider == "claude":
        if not settings.anthropic_api_key:
            raise ValueError(
                "Anthropic API key not configured. "
                "Please set ANTHROPIC_API_KEY environment variable."
            )
        return settings.anthropic_api_key
    
    else:
        raise ValueError(
            f"Unknown provider: {provider}. "
            "Must be one of: openai, gemini, claude"
        )
