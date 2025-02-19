from abc import ABC, abstractmethod
from typing import Optional, Any, Dict, List

class ICacheService(ABC):
    
    @abstractmethod
    async def get_cached_data(self, key: str, source: str) -> Optional[Dict[str, Any]]:
        """Retrieve data from cache"""
        pass

    @abstractmethod
    async def set_cached_data(self, key: str, source: str, data: Dict[str, Any], ttl: Optional[int] = None) -> bool:
        pass

    @abstractmethod
    async def invalidate_cache(self, key: str, source: str) -> bool:
        pass

    @abstractmethod
    async def bulk_invalidate(self, pattern: str) -> int:
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        pass

    @abstractmethod
    def _generate_cache_key(self, key: str, source: str) -> str:
        pass

    @abstractmethod
    def _calculate_ttl(self, query_type: str) -> int:
        pass

    @abstractmethod
    async def get_cache_stats(self) -> Dict[str, Any]:
        pass

    @abstractmethod
    async def clear_all(self) -> bool:
        pass