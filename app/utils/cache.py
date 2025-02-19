import asyncio
from functools import wraps
from typing import Any, Callable, Optional
from app.utils.cache_service import cache_service
from app.utils.logger import logger

def cache(prefix: str, ttl: Optional[int] = None):
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs) -> Any:
            try:
                cache_key = cache_service.generate_key(prefix, *args, **kwargs)
                cached_result = cache_service.get(cache_key)
                
                if cached_result is not None:
                    logger.debug(f"Cache hit for key: {cache_key}")
                    return cached_result
                
                logger.debug(f"Cache miss for key: {cache_key}")
                result = await func(*args, **kwargs)
                
                cache_service.set(cache_key, result, ttl)
                return result
                
            except Exception as e:
                logger.error(f"Cache decorator error: {str(e)}")
                return await func(*args, **kwargs)
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs) -> Any:
            try:
                cache_key = cache_service.generate_key(prefix, *args, **kwargs)
                cached_result = cache_service.get(cache_key)
                
                if cached_result is not None:
                    logger.debug(f"Cache hit for key: {cache_key}")
                    return cached_result
                
                logger.debug(f"Cache miss for key: {cache_key}")
                result = func(*args, **kwargs)
                
                cache_service.set(cache_key, result, ttl)
                return result
                
            except Exception as e:
                logger.error(f"Cache decorator error: {str(e)}")
                return func(*args, **kwargs)
        
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    
    return decorator