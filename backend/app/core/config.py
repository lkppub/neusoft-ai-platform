from pathlib import Path
from pydantic_settings import BaseSettings
from typing import List
import json

# 项目根目录（backend 的上级目录），确保 .env 文件路径始终正确
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent


class Settings(BaseSettings):
    # App
    APP_NAME: str = "东软智慧商务AI助手平台"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True
    SECRET_KEY: str = "change-me"

    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./data/app.db"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # JWT
    JWT_SECRET_KEY: str = "change-me-jwt"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # AI Provider: "mock" or "deepseek"
    AI_PROVIDER: str = "deepseek"

    # DeepSeek
    DEEPSEEK_API_KEY: str = ""
    DEEPSEEK_BASE_URL: str = "https://api.deepseek.com"
    DEEPSEEK_MODEL: str = "deepseek-v4-pro"
    DEEPSEEK_MAX_TOKENS: int = 4096
    DEEPSEEK_TEMPERATURE: float = 0.7

    # Embedding model (sentence-transformers)
    EMBEDDING_MODEL: str = "paraphrase-multilingual-MiniLM-L12-v2"

    # Chroma
    CHROMA_PERSIST_DIR: str = "./data/chroma"
    CHROMA_COLLECTION_NAME: str = "enterprise_knowledge"

    # Dify
    DIFY_API_URL: str = "http://localhost:5001/v1"
    DIFY_API_KEY: str = ""

    # Voice / STT
    STT_PROVIDER: str = "whisper"       # "whisper" | "mock"
    WHISPER_MODEL: str = "base"         # tiny/base/small/medium/large

    # Voice / TTS
    TTS_PROVIDER: str = "pyttsx3"       # "pyttsx3" (offline, Windows) | "edge_tts" (cloud) | "mock"
    TTS_VOICE: str = "zh-CN-XiaoxiaoNeural"
    TTS_RATE: str = "+0%"               # "+10%" faster, "-20%" slower

    # CORS
    CORS_ORIGINS: str = '["http://localhost:5173","http://localhost:3000"]'

    @property
    def cors_origins_list(self) -> List[str]:
        return json.loads(self.CORS_ORIGINS)

    class Config:
        env_file = str(_PROJECT_ROOT / ".env")
        env_file_encoding = "utf-8"


settings = Settings()
