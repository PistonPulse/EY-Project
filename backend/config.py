"""
config.py
=========

Centralised application configuration using **Pydantic Settings**.

All environment variables are loaded from a ``.env`` file (or the system
environment) and validated at import time.  Modules across the backend should
import the singleton ``settings`` instance rather than reading ``os.environ``
directly.

Sections
--------
- **General** — app name, version, debug toggle.
- **Server** — host, port, allowed CORS origins.
- **External APIs** — CRM, credit-bureau, and LLM provider keys / URLs.
- **Logging** — log level, JSON format toggle.

Example ``.env``::

    APP_NAME=Agentic Lending Platform
    DEBUG=true
    LOG_LEVEL=DEBUG
    OPENAI_API_KEY=sk-...
"""

from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    """Application-wide settings sourced from environment variables."""

    # ── General ──────────────────────────────────────────────────────────
    APP_NAME: str = "Agentic Lending Platform"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = False

    # ── Server ───────────────────────────────────────────────────────────
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    ALLOWED_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:5173"]

    # ── External APIs ────────────────────────────────────────────────────
    CRM_API_BASE_URL: str = ""
    CRM_API_KEY: str = ""
    CREDIT_BUREAU_API_URL: str = ""
    CREDIT_BUREAU_API_KEY: str = ""
    OPENAI_API_KEY: str = ""
    LLM_MODEL_NAME: str = "gpt-4"

    # ── Gemini Flash (Convers-AI Layer) ──────────────────────────────────
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL_NAME: str = "gemini-2.0-flash"
    GEMINI_TIMEOUT_SECONDS: int = 8
    GEMINI_MAX_TOKENS: int = 200
    GEMINI_TEMPERATURE: float = 0.3
    USE_GEMINI: str = "true"

    # ── Groq Fallback (when Gemini fails/times out) ──────────────────────
    GROQ_API_KEY: str = ""
    GROQ_MODEL_NAME: str = "llama-3.1-8b-instant"
    GROQ_TIMEOUT_SECONDS: int = 6

    # ── Local LLM (Ollama / LM Studio / LocalAI — OpenAI-compatible) ──
    LOCAL_LLM_URL: str = "http://localhost:11434/v1"
    LOCAL_LLM_MODEL: str = "llama3"
    LOCAL_LLM_TIMEOUT_SECONDS: int = 15
    LOCAL_LLM_ENABLED: bool = True

    # ── Database ─────────────────────────────────────────────────────────
    DATABASE_URL: str = "sqlite:///./lending_platform.db"

    # ── Logging ──────────────────────────────────────────────────────────
    LOG_LEVEL: str = "INFO"
    LOG_JSON_FORMAT: bool = True

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


settings = Settings()
