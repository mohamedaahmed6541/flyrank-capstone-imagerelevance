from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    GEMINI_API_KEY: str = Field(..., description="Google AI Studio API key for Gemini Flash")
    DATABASE_URL: str = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/flyrank",
        description="PostgreSQL connection URL"
    )
    APP_ENV: str = Field(default="development")
    LOG_LEVEL: str = Field(default="INFO")
    EMBEDDING_DIM: int = Field(default=768)
    SIMILARITY_THRESHOLD: float = Field(default=0.75)
    CONFIDENCE_FLOOR: float = Field(default=0.60)
    DEFAULT_PAGE_SIZE: int = Field(default=20)
    MAX_PAGE_SIZE: int = Field(default=100)

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


settings = Settings()