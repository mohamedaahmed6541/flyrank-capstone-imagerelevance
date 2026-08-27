from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    # Ollama (primary vision model)
    OLLAMA_HOST: str = Field(
        default="http://localhost:11434",
        description="Ollama API base URL"
    )
    OLLAMA_MODEL: str = Field(
        default="llava",
        description="Ollama vision model name"
    )

    # Google AI Studio API Key (optional fallback)
    GEMINI_API_KEY: str | None = Field(
        default=None,
        description="Google AI Studio API key for Gemini Flash (optional)"
    )

    # Pexels API Key (for fetching verified images)
    PEXELS_API_KEY: str | None = Field(
        default=None,
        description="Pexels API key for fetching verified images"
    )

    DATABASE_URL: str = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/flyrank",
        description="PostgreSQL connection URL"
    )
    APP_ENV: str = Field(default="development")
    LOG_LEVEL: str = Field(default="INFO")
    EMBEDDING_DIM: int = Field(default=768)
    SIMILARITY_THRESHOLD: float = Field(default=0.65)
    CONFIDENCE_FLOOR: float = Field(default=0.60)
    DEFAULT_PAGE_SIZE: int = Field(default=20)
    MAX_PAGE_SIZE: int = Field(default=100)
    
    # Ollama Embedding Model
    OLLAMA_EMBEDDING_MODEL: str = Field(
        default="nomic-embed-text",
        description="Ollama embedding model name"
    )

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


settings = Settings()