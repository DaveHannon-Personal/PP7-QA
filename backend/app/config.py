"""
Application configuration via environment variables / .env file.
All values can be overridden at runtime; the Settings UI persists
ProPresenter and Ollama config to the SQLite DB (see models/config.py).
"""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Database
    database_url: str = "sqlite:////data/pp7qa.db"

    # ProPresenter 7 — startup defaults (overridden by DB config)
    propresenter_url: str = "http://localhost"
    propresenter_port: int = 50001

    # Ollama AI — startup defaults
    ollama_url: str = "http://host.docker.internal:11434"
    ollama_model: str = "llama3.2:3b"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
