from typing import Optional, Any, Dict
import json
import hashlib
from datetime import datetime
import redis
from app.config import get_settings
from app.utils.logger import logger, log_error
from app.interfaces.cache_interface import ICacheService
from app.constants.cache_constants import CacheTTL, CachePrefix, QueryType, TTL_MAPPING
from app.exceptions.cache_exceptions import (
    CacheConnectionError,
    CacheOperationError,
    CacheSerializationError,
    CacheKeyError,
    CacheConfigurationError
)

settings = get_settings()

class RedisCacheService(ICacheService):
    def __init__(self):
        try:
            self.redis_client = redis.Redis(
                host=settings.REDIS_HOST,
                port=settings.REDIS_PORT,
                db=settings.REDIS_DB,
                password=settings.REDIS_PASSWORD,
                ssl=settings.REDIS_SSL,
                socket_timeout=settings.REDIS_TIMEOUT,
                decode_responses=True
            )
            self.ttl = settings.CACHE_TTL
            self.enabled = settings.CACHE_ENABLED
        except redis.ConnectionError as e:
            raise CacheConnectionError(str(e))
        except Exception as e:
            raise CacheConfigurationError(str(e))

    def _generate_cache_key(self, key: str, source: str) -> str:
        try:
            key_lower = key.lower().strip()
            
            if any(term in key_lower for term in ['news', 'latest', 'recent']):
                today = datetime.now().strftime('%Y-%m-%d')
                key_content = f"{key_lower}:{source}:{today}"
            else:
                key_content = f"{key_lower}:{source}"
                
            hashed = hashlib.sha256(key_content.encode()).hexdigest()
            return f"{CachePrefix.COMPANY_INFO}:{hashed}"
        except Exception as e:
            raise CacheKeyError(str(e))

    def _calculate_ttl(self, query_type: str) -> int:
        return TTL_MAPPING.get(query_type, CacheTTL.DEFAULT)

    @log_error(logger)
    async def get_cached_data(self, key: str, source: str) -> Optional[Dict[str, Any]]:
        if not self.enabled:
            return None
            
        try:
            cache_key = self._generate_cache_key(key, source)
            cached_data = self.redis_client.get(cache_key)
            
            if cached_data:
                logger.info(f"Cache hit for key: {cache_key}")
                try:
                    return json.loads(cached_data)
                except json.JSONDecodeError as e:
                    raise CacheSerializationError("deserialization", str(e))
                    
            logger.info(f"Cache miss for key: {cache_key}")
            return None
            
        except redis.RedisError as e:
            raise CacheOperationError("get", str(e))

    @log_error(logger)
    async def set_cached_data(self, key: str, source: str, data: Dict[str, Any], ttl: Optional[int] = None) -> bool:
        if not self.enabled:
            return False
            
        try:
            cache_key = self._generate_cache_key(key, source)
            
            try:
                serialized_data = json.dumps(data)
            except (TypeError, json.JSONDecodeError) as e:
                raise CacheSerializationError("serialization", str(e))
            
            expiration = ttl if ttl is not None else self._calculate_ttl(
                QueryType.GENERAL.value
            )
            
            success = self.redis_client.setex(
                cache_key,
                expiration,
                serialized_data
            )
            
            if success:
                logger.info(f"Successfully cached data for key: {cache_key}")
            else:
                logger.warning(f"Failed to cache data for key: {cache_key}")
                
            return bool(success)
            
        except redis.RedisError as e:
            raise CacheOperationError("set", str(e))

    @log_error(logger)
    async def invalidate_cache(self, key: str, source: str) -> bool:
        if not self.enabled:
            return False
            
        try:
            cache_key = self._generate_cache_key(key, source)
            success = self.redis_client.delete(cache_key)
            
            if success:
                logger.info(f"Successfully invalidated cache for key: {cache_key}")
            else:
                logger.warning(f"Failed to invalidate cache for key: {cache_key}")
                
            return bool(success)
            
        except redis.RedisError as e:
            raise CacheOperationError("invalidate", str(e))

    @log_error(logger)
    async def bulk_invalidate(self, pattern: str) -> int:
        if not self.enabled:
            return 0
            
        try:
            keys = []
            cursor = 0
            while True:
                cursor, partial_keys = self.redis_client.scan(
                    cursor,
                    match=f"{CachePrefix.COMPANY_INFO}:{pattern}*",
                    count=100
                )
                keys.extend(partial_keys)
                if cursor == 0:
                    break
            
            if keys:
                deleted = self.redis_client.delete(*keys)
                logger.info(f"Bulk invalidated {deleted} keys matching pattern: {pattern}")
                return deleted
            
            return 0
            
        except redis.RedisError as e:
            raise CacheOperationError("bulk_invalidate", str(e))

    async def health_check(self) -> bool:
        try:
            return bool(self.redis_client.ping())
        except Exception as e:
            logger.error(f"Redis health check failed: {str(e)}")
            return False

    @log_error(logger)
    async def get_cache_stats(self) -> Dict[str, Any]:
        try:
            info = self.redis_client.info()
            return {
                "used_memory": info.get("used_memory_human", "N/A"),
                "connected_clients": info.get("connected_clients", 0),
                "total_connections_received": info.get("total_connections_received", 0),
                "total_commands_processed": info.get("total_commands_processed", 0)
            }
        except redis.RedisError as e:
            raise CacheOperationError("get_stats", str(e))

    @log_error(logger)
    async def clear_all(self) -> bool:
        if not self.enabled:
            return False
            
        try:
            return bool(self.redis_client.flushdb())
        except redis.RedisError as e:
            raise CacheOperationError("clear_all", str(e))