"""Application configuration placeholders."""

from pydantic import BaseModel


class Settings(BaseModel):
    """Minimal local-first settings."""

    env: str = "local"
    database_url: str = "sqlite:///./edgelab.db"


settings = Settings()
