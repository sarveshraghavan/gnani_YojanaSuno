"""Validated environment settings. Secrets are never written back to disk."""
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[1]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BACKEND_DIR / ".env", env_file_encoding="utf-8", extra="ignore"
    )

    use_mock_voice: bool = True
    use_mock_llm: bool = True
    gnani_api_key: str = ""
    gnani_stt_url: str = "https://api.vachana.ai/stt/v3"
    gnani_tts_url: str = "https://api.vachana.ai/api/v1/tts/inference"
    gnani_tts_voice: str = ""
    prisma_model: str = "prisma-v3.0"
    timbre_model: str = "timbre-v2.5"
    evon_base_url: str = ""
    evon_model: str = "model"
    evon_api_key: str = ""


settings = Settings()
