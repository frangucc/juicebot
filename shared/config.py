"""Configuration management for the trading assistant."""

import os
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

load_dotenv()


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Supabase
    supabase_url: str = os.getenv("SUPABASE_URL", "")
    supabase_anon_key: str = os.getenv("SUPABASE_ANON_KEY", "")
    supabase_service_role_key: str = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
    database_url: str = os.getenv("DATABASE_URL", "")
    database2_url: str = os.getenv("DATABASE2_URL", "")  # Neon Discord database

    # Databento
    databento_api_key: str = os.getenv("DATABENTO_API_KEY", "")

    # JWT
    jwt_key: str = os.getenv("JWT_KEY", "")

    # Twilio (to be added)
    twilio_account_sid: str = os.getenv("TWILIO_ACCOUNT_SID", "")
    twilio_auth_token: str = os.getenv("TWILIO_AUTH_TOKEN", "")
    twilio_phone_number: str = os.getenv("TWILIO_PHONE_NUMBER", "")

    # AI APIs
    anthropic_api_key: str = os.getenv("ANTHROPIC_API_KEY", "")
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    openai_key: str = os.getenv("OPENAI_KEY", "")  # Alternative key name
    alpha_api_key: str = os.getenv("ALPHA_API_KEY", "")
    elevenlabs_api_key: str = os.getenv("ELEVENLABS_API_KEY", "")

    # Screener settings
    screener_pct_threshold: float = 0.03  # 3% move threshold
    screener_dataset: str = "EQUS.MINI"  # Regular hours only (9:30 AM - 4:00 PM ET)
    screener_schema: str = "mbp-1"
    enable_price_bars: bool = os.getenv("ENABLE_PRICE_BARS", "false").lower() == "true"  # Enable 1-minute bar capture

    # Redis (optional for now)
    redis_url: str = os.getenv("REDIS_URL", "redis://localhost:6379")

    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"  # Ignore extra fields in .env that aren't defined in the model


settings = Settings()
