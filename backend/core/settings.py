import os
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import model_validator


class Settings(BaseSettings):
    """
    Global settings configuration for the FastAPI backend.
    Enables environment variable overrides.
    """
    API_V1_PREFIX: str = "/api/v1"
    PROJECT_NAME: str = "Agentic Decision Intelligence Platform"

    # CORS settings - default to allow all in development
    CORS_ORIGINS: list = ["*"]

    # Base directory of the project (project root)
    BASE_DIR: Path = Path(__file__).resolve().parent.parent.parent

    # Database & Memory Configuration (resolved to absolute paths on validation)
    DATABASE_URL: str = ""
    CHROMA_PATH: str = ""
    MEMORY_COLLECTION_PREFIX: str = "domain_"

    # Environment settings
    OPENROUTER_API_KEY: str = ""
    LANGSMITH_API_KEY: str = ""
    LANGCHAIN_TRACING_V2: str = "false"
    LANGCHAIN_PROJECT: str = "agentic-decision-platform"

    # Infrastructure settings
    LOG_LEVEL: str = "INFO"
    ENVIRONMENT: str = "development"

    # Hardening & Guardrail parameters
    ENABLE_PII_REDACTION: bool = True
    ENABLE_PROMPT_GUARD: bool = True
    ENABLE_HEURISTIC_FALLBACK: bool = True
    ENABLE_LEARNING_FILTER: bool = True
    LLM_TIMEOUT_SECONDS: int = 20
    MAX_LLM_RETRIES: int = 2
    MAX_LLM_CALLS_PER_REQUEST: int = 5
    USE_SYNTHESIS_ONLY_IF_NEEDED: bool = True

    model_config = SettingsConfigDict(
        env_file=str(Path(__file__).resolve().parent.parent.parent / ".env"),
        env_file_encoding="utf-8",
        extra="allow"
    )

    @model_validator(mode="before")
    @classmethod
    def resolve_paths(cls, values: dict) -> dict:
        base_dir = Path(__file__).resolve().parent.parent.parent
        
        # 1. Resolve DATABASE_URL
        db_url = values.get("DATABASE_URL")
        if not db_url:
            # Fallback to standard absolute SQLite path
            db_path = base_dir / "backend" / "data" / "platform.db"
            db_url = f"sqlite:///{db_path}"
            values["DATABASE_URL"] = db_url
        elif db_url.startswith("sqlite:///./"):
            rel_path = db_url.replace("sqlite:///./", "")
            abs_path = base_dir / "backend" / rel_path
            values["DATABASE_URL"] = f"sqlite:///{abs_path}"
        elif db_url.startswith("sqlite:///"):
            rel_path = db_url.replace("sqlite:///", "")
            if not Path(rel_path).is_absolute():
                abs_path = base_dir / "backend" / rel_path
                values["DATABASE_URL"] = f"sqlite:///{abs_path}"

        # 2. Resolve CHROMA_PATH
        chroma_path = values.get("CHROMA_PATH")
        if not chroma_path:
            chroma_path = str(base_dir / "backend" / "data" / "chroma")
            values["CHROMA_PATH"] = chroma_path
        else:
            p = Path(chroma_path)
            if not p.is_absolute():
                values["CHROMA_PATH"] = str(base_dir / "backend" / chroma_path)

        return values


# Global settings instance
settings = Settings()
