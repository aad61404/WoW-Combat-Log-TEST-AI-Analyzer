"""
Application configuration via environment variables.

Uses Pydantic Settings to load from .env file or environment.
"""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Warcraft Logs API
    wcl_client_id: str = ""
    wcl_client_secret: str = ""

    # Google Gemini API
    gemini_api_key: str = ""

    # Server
    api_host: str = "0.0.0.0"
    api_port: int = 8000

    # CORS — allowed origins for the frontend dev server
    cors_origins: list[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
    }


# Singleton instance
settings = Settings()
