from typing import Optional

class CacheBaseException(Exception):
    def __init__(self, message: str, details: Optional[str] = None):
        self.message = message
        self.details = details
        super().__init__(self.message)

class CacheConnectionError(CacheBaseException):
    def __init__(self, details: Optional[str] = None):
        super().__init__("Failed to connect to Redis server", details)

class CacheOperationError(CacheBaseException):
    def __init__(self, operation: str, details: Optional[str] = None):
        super().__init__(f"Cache operation failed: {operation}", details)

class CacheConfigurationError(CacheBaseException):
    def __init__(self, details: Optional[str] = None):
        super().__init__("Invalid cache configuration", details)

class CacheSerializationError(CacheBaseException):
    def __init__(self, operation: str, details: Optional[str] = None):
        super().__init__(f"Cache serialization error: {operation}", details)

class CacheKeyError(CacheBaseException):
    def __init__(self, details: Optional[str] = None):
        super().__init__("Invalid cache key operation", details)
