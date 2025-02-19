import json
import redis
from typing import Any, Optional
from app.config import get_settings
from app.utils.logger import logger

settings = get_settings()

class CacheService:
    def __init__(self):
        redis_params = {
            "host": settings.REDIS_HOST,
            "port": settings.REDIS_PORT,
            "db": settings.REDIS_DB,
            "socket_timeout": settings.REDIS_TIMEOUT,
            "decode_responses": True,
            "ssl": settings.REDIS_SSL
        }
        
        if settings.REDIS_PASSWORD:
            redis_params["password"] = settings.REDIS_PASSWORD
            
        try:
            self.client = redis.Redis(**redis_params)
            self.client.ping()  # Test connection
            logger.info("Redis connection established successfully")
        except redis.ConnectionError as e:
            logger.warning(f"Failed to connect to Redis: {str(e)}. Cache will be disabled.")
            self.enabled = False
        else:
            self.enabled = settings.CACHE_ENABLED
            
        self.ttl = settings.CACHE_TTL
    
    def get(self, key: str) -> Optional[Any]:
        if not self.enabled:
            return None
            
        try:
            value = self.client.get(key)
            if value:
                return json.loads(value)
            return None
        except Exception as e:
            logger.error(f"Cache get error: {str(e)}")
            return None
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        if not self.enabled:
            return False
            
        try:
            serialized_value = json.dumps(value, default=str)
            return bool(self.client.setex(
                key,
                ttl or self.ttl,
                serialized_value
            ))
        except Exception as e:
            logger.error(f"Cache set error: {str(e)}")
            return False
    
    def delete(self, key: str) -> bool:
        if not self.enabled:
            return False
            
        try:
            return bool(self.client.delete(key))
        except Exception as e:
            logger.error(f"Cache delete error: {str(e)}")
            return False
    
    def generate_key(self, prefix: str, *args, **kwargs) -> str:
        key_parts = [prefix]
        
        if args:
            key_parts.extend([str(arg) for arg in args])
            
        if kwargs:
            sorted_kwargs = sorted(kwargs.items())
            key_parts.extend([f"{k}:{v}" for k, v in sorted_kwargs])
            
        return ":".join(key_parts)

cache_service = CacheService()