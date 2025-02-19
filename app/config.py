from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import Optional
import logging

class Settings(BaseSettings):
    
    AZURE_OPENAI_API_KEY: str
    AZURE_OPENAI_ENDPOINT: str
    AZURE_OPENAI_API_VERSION: str
    AZURE_OPENAI_DEPLOYMENT_NAME: str
    
    LANGSMITH_API_KEY: Optional[str] = None
    LANGSMITH_TRACING: Optional[bool] = False
    LANGSMITH_ENDPOINT: Optional[str] = None
    LANGSMITH_PROJECT: Optional[str] = None
    
    TAVILY_API_KEY: Optional[str] = None
    
    # Redis settings
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_PASSWORD: Optional[str] = None
    REDIS_SSL: bool = False
    REDIS_TIMEOUT: int = 5
    CACHE_TTL: int = 3600
    CACHE_ENABLED: bool = True
    
    LOG_LEVEL: str = "INFO" 
    MAX_RETRIES: int = 3
    TIMEOUT_SECONDS: int = 30
    DEBUG: bool = False
    
    CACHE_TTL: int = 3600  
    
    class Config:
        env_file = ".env"
        case_sensitive = True
        env_prefix = ""

@lru_cache()
def get_settings() -> Settings:
    return Settings()

def get_log_level(log_level: str) -> int:
    log_level = log_level.upper()
    if log_level == 'DEBUG':
        return logging.DEBUG
    return getattr(logging, log_level, logging.INFO)