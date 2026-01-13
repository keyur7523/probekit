from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # Database
    database_url: str = "postgresql+asyncpg://postgres:probekit@localhost:5432/probekit"

    # LLM API Keys
    anthropic_api_key: str = ""
    openai_api_key: str = ""

    # Ollama (optional, for local models)
    ollama_base_url: str = "http://localhost:11434"

    # App settings
    debug: bool = False

    # Model pricing (USD per 1M tokens) - as of Jan 2025
    # Claude pricing
    claude_sonnet_input_price: float = 3.0
    claude_sonnet_output_price: float = 15.0
    claude_opus_input_price: float = 15.0
    claude_opus_output_price: float = 75.0
    claude_haiku_input_price: float = 0.25
    claude_haiku_output_price: float = 1.25

    # OpenAI pricing
    gpt4_turbo_input_price: float = 10.0
    gpt4_turbo_output_price: float = 30.0
    gpt4o_input_price: float = 2.5
    gpt4o_output_price: float = 10.0
    gpt4o_mini_input_price: float = 0.15
    gpt4o_mini_output_price: float = 0.6

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache
def get_settings() -> Settings:
    return Settings()
