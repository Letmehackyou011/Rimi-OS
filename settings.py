"""
Application Settings & Configuration
"""

from pydantic_settings import BaseSettings
from typing import List
import os

class Settings(BaseSettings):
    """Application Settings"""
    
    # App Configuration
    APP_NAME: str = "AI Security Research OS"
    VERSION: str = "1.0.0"
    DEBUG: bool = True
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    
    # CORS
    ALLOWED_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://localhost:8080",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:8080",
    ]
    
    # Database Configuration
    DATABASE_URL: str = "postgresql://user:password@localhost:5432/security_os"
    DATABASE_ECHO: bool = False
    
    # LLM Configuration
    ACTIVE_LLM: str = "ollama"  # "ollama", "claude", "gemini", "openai", "nvidia"
    
    # Ollama Configuration
    OLLAMA_ENDPOINT: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "mistral"
    
    # Claude Configuration
    CLAUDE_API_KEY: str = ""
    CLAUDE_MODEL: str = "claude-3-5-sonnet-20241022"
    
    # Gemini Configuration
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-2.0-flash"
    
    # OpenAI Configuration
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4"
    
    # Nvidia Configuration
    NVIDIA_API_KEY: str = ""
    NVIDIA_ENDPOINT: str = "https://integrate.api.nvidia.com/v1"
    
    # Token & Context Settings
    MAX_TOKENS: int = 8000
    CONTEXT_WINDOW: int = 32000
    
    # Agent Settings
    AGENT_TIMEOUT: int = 300  # 5 minutes
    MAX_RETRIES: int = 3
    
    # Security
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # Report Settings
    REPORT_FORMAT: str = "pdf"  # "pdf", "docx", "json"
    REPORT_STORAGE_PATH: str = "./reports"
    
    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FILE: str = "app.log"
    
    class Config:
        env_file = ".env"
        env_file_encoding = 'utf-8'
        case_sensitive = True

# Create settings instance
settings = Settings()

# Validate LLM configuration
def validate_llm_config():
    """Validate that required LLM configuration is set"""
    if settings.ACTIVE_LLM == "claude" and not settings.CLAUDE_API_KEY:
        raise ValueError("CLAUDE_API_KEY not set but ACTIVE_LLM is 'claude'")
    if settings.ACTIVE_LLM == "gemini" and not settings.GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY not set but ACTIVE_LLM is 'gemini'")
    if settings.ACTIVE_LLM == "openai" and not settings.OPENAI_API_KEY:
        raise ValueError("OPENAI_API_KEY not set but ACTIVE_LLM is 'openai'")

# Create reports directory if it doesn't exist
os.makedirs(settings.REPORT_STORAGE_PATH, exist_ok=True)
