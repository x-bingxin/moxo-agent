from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    llm_api_key: str
    llm_base_url: str = "https://api.deepseek.com"
    llm_model: str = "deepseek-chat"
    session_timeout_minutes: int = 60

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


def get_settings() -> Settings:
    return Settings()
