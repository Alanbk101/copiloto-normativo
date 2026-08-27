from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str
    redis_url: str
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    log_level: str = "info"
    ollama_url: str = "http://ollama:11434"
    ollama_model: str = "qwen2.5:1.5b"


settings = Settings()
