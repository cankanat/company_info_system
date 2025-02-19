from enum import Enum
from typing import Dict

class CacheTTL:
    DEFAULT = 86400
    NEWS = 3600 
    LOCATION = 604800 
    BUSINESS = 43200
    INVESTMENT = 21600

class CachePrefix:
    COMPANY_INFO = "company_info"
    WIKI = "wiki"
    TAVILY = "tavily"
    INTENT = "intent"
    AMBIGUITY = "ambiguity"

class CacheErrorMessages:
    CONNECTION_ERROR = "Failed to connect to Redis server"
    OPERATION_ERROR = "Cache operation failed"
    INVALID_DATA = "Invalid data format for caching"
    KEY_NOT_FOUND = "Cache key not found"
    SERIALIZATION_ERROR = "Failed to serialize cache data"
    DESERIALIZATION_ERROR = "Failed to deserialize cache data"

class QueryType(str, Enum):
    NEWS = "news"
    LOCATION = "location"
    BUSINESS = "business"
    INVESTMENT = "investment"
    GENERAL = "general"

TTL_MAPPING: Dict[str, int] = {
    QueryType.NEWS.value: CacheTTL.NEWS,
    QueryType.LOCATION.value: CacheTTL.LOCATION,
    QueryType.BUSINESS.value: CacheTTL.BUSINESS,
    QueryType.INVESTMENT.value: CacheTTL.INVESTMENT,
    QueryType.GENERAL.value: CacheTTL.DEFAULT
}