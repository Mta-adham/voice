"""
Configuration module for restaurant booking system.

Loads environment variables and provides configuration settings including
API keys for LLM providers and email notification settings.
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
        sendgrid_api_key: Optional SendGrid API key for email notifications
        restaurant_name: Restaurant name for branding
        restaurant_phone: Restaurant phone number
        restaurant_address: Restaurant physical address
        from_email: Email address to send from
        reply_to_email: Email address for replies
        directions_info: Directions and parking information
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
    
    # Email Configuration (SendGrid)
    sendgrid_api_key: Optional[str] = Field(
        default=None,
        alias="SENDGRID_API_KEY",
        description="SendGrid API key for email notifications"
    )
    
    from_email: str = Field(
        default="noreply@restaurant.com",
        alias="FROM_EMAIL",
        description="Email address to send notifications from"
    )
    
    reply_to_email: str = Field(
        default="info@restaurant.com",
        alias="REPLY_TO_EMAIL",
        description="Email address for customer replies"
    )
    
    # Restaurant Information
    restaurant_name: str = Field(
        default="The Grand Restaurant",
        alias="RESTAURANT_NAME",
        description="Restaurant name for branding"
    )
    
    restaurant_phone: str = Field(
        default="+1 (555) 123-4567",
        alias="RESTAURANT_PHONE",
        description="Restaurant phone number"
    )
    
    restaurant_address: str = Field(
        default="123 Main Street, City, State 12345",
        alias="RESTAURANT_ADDRESS",
        description="Restaurant physical address"
    )
    
    directions_info: str = Field(
        default="Street parking available. Valet service offered during dinner hours.",
        alias="DIRECTIONS_INFO",
        description="Directions and parking information"
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
