import os
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """
    Global settings configuration for the FastAPI backend.
    Enables environment variable overrides.
    """
    API_V1_PREFIX: str = "/api/v1"
    PROJECT_NAME: str = "Agentic Decision Intelligence Platform"

    # CORS settings - default to allow all in development
    CORS_ORIGINS: list = ["*"]

    # Database & Memory Configuration
    DATABASE_URL: str = "sqlite:///./data/platform.db"
    CHROMA_PATH: str = "./data/chroma"
    MEMORY_COLLECTION_PREFIX: str = "domain_"

    # Environment settings
    OPENROUTER_API_KEY: str = os.getenv("OPENROUTER_API_KEY", "")
    LANGSMITH_API_KEY: str = os.getenv("LANGSMITH_API_KEY", "")
    LANGCHAIN_TRACING_V2: str = os.getenv("LANGCHAIN_TRACING_V2", "false")
    LANGCHAIN_PROJECT: str = os.getenv("LANGCHAIN_PROJECT", "agentic-decision-platform")

    class Config:
        env_file = ".env"
        extra = "allow"


# Global settings instance
settings = Settings()
