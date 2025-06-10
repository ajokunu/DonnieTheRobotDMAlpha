"""
In-memory cache service implementation
"""
import asyncio
from typing import Any, Optional, Dict
from datetime import datetime, timedelta
from cachetools import TTLCache
import threading

from ...domain.interfaces.cache_service import CacheServiceInterface
from ..config.settings import CacheConfig


class MemoryCacheService(CacheServiceInterface):
    """In-memory cache service using TTLCache"""
    
    def __init__(self, config: CacheConfig):
        self.config = config
        self.enabled = config.enabled
        
        if self.enabled:
            # Main cache with TTL
            self._cache = TTLCache(
                maxsize=config.max_size,
                ttl=config.ttl_seconds
            )
            
            # Specialized caches with different TTLs
            self._character_cache = TTLCache(
                maxsize=config.max_size // 4,
                ttl=config.character_ttl
            )
            
            self._episode_cache = TTLCache(
                maxsize=config.max_size // 8,
                ttl=config.episode_ttl
            )
            
            self._memory_cache = TTLCache(
                maxsize=config.max_size // 2,
                ttl=config.memory_ttl
            )
            
            # Thread lock for thread safety
            self._lock = threading.RLock()
        else:
            self._cache = {}
            self._character_cache = {}
            self._episode_cache = {}
            self._memory_cache = {}
            self._lock = threading.RLock()
    
    async def get(self, key: str) -> Optional[Any]:
        """Get a value from cache"""
        if not self.enabled:
            return None
        
        with self._lock:
            # Check specialized caches first
            cache = self._get_specialized_cache(key)
            
            try:
                value = cache.get(key)
                if value is not None:
                    return value
                
                # Fallback to main cache
                return self._cache.get(key)
                
            except KeyError:
                return None
    
    async def set(self, key: str, value: Any, ttl: Optional[timedelta] = None) -> None:
        """Set a value in cache with optional TTL"""
        if not self.enabled:
            return
        
        with self._lock:
            # Use specialized cache if applicable
            cache = self._get_specialized_cache(key)
            
            if ttl:
                # For custom TTL, use main cache with timestamp
                expiry = datetime.now() + ttl
                cache[key] = {
                    'value': value,
                    'expiry': expiry,
                    'custom_ttl': True
                }
            else:
                # Use default TTL
                cache[key] = value
    
    async def delete(self, key: str) -> bool:
        """Delete a key from cache"""
        if not self.enabled:
            return False
        
        with self._lock:
            deleted = False
            
            # Check all caches
            for cache in [self._cache, self._character_cache, self._episode_cache, self._memory_cache]:
                if key in cache:
                    del cache[key]
                    deleted = True
            
            return deleted
    
    async def clear(self) -> None:
        """Clear all cache entries"""
        if not self.enabled:
            return
        
        with self._lock:
            self._cache.clear()
            self._character_cache.clear()
            self._episode_cache.clear()
            self._memory_cache.clear()
    
    async def exists(self, key: str) -> bool:
        """Check if key exists in cache"""
        if not self.enabled:
            return False
        
        with self._lock:
            # Check all caches
            for cache in [self._cache, self._character_cache, self._episode_cache, self._memory_cache]:
                if key in cache:
                    # Check for custom TTL expiry
                    value = cache[key]
                    if isinstance(value, dict) and value.get('custom_ttl'):
                        if datetime.now() > value['expiry']:
                            del cache[key]
                            continue
                    return True
            
            return False
    
    def _get_specialized_cache(self, key: str) -> TTLCache:
        """Get the appropriate specialized cache for a key"""
        if key.startswith('character:'):
            return self._character_cache
        elif key.startswith('episode:'):
            return self._episode_cache
        elif key.startswith('memory:'):
            return self._memory_cache
        else:
            return self._cache
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        if not self.enabled:
            return {"enabled": False}
        
        with self._lock:
            return {
                "enabled": True,
                "main_cache": {
                    "size": len(self._cache),
                    "max_size": self._cache.maxsize,
                    "ttl": self._cache.ttl
                },
                "character_cache": {
                    "size": len(self._character_cache),
                    "max_size": self._character_cache.maxsize,
                    "ttl": self._character_cache.ttl
                },
                "episode_cache": {
                    "size": len(self._episode_cache),
                    "max_size": self._episode_cache.maxsize,
                    "ttl": self._episode_cache.ttl
                },
                "memory_cache": {
                    "size": len(self._memory_cache),
                    "max_size": self._memory_cache.maxsize,
                    "ttl": self._memory_cache.ttl
                }
            }
    
    async def warm_cache(self, character_service, episode_service, guild_ids: list):
        """Warm up the cache with frequently accessed data"""
        if not self.enabled:
            return
        
        try:
            for guild_id in guild_ids:
                # Cache current episode
                episode = await episode_service.get_current_episode(guild_id)
                if episode:
                    await self.set(f"episode:{guild_id}:current", episode)
                
                # Cache guild characters
                characters = await character_service.get_guild_party(guild_id)
                for character in characters:
                    cache_key = f"character:{character.discord_user_id}:{guild_id}"
                    await self.set(cache_key, character)
        
        except Exception as e:
            print(f"❌ Error warming cache: {e}")


# Cache key builders for consistency
class CacheKeys:
    """Standard cache key builders"""
    
    @staticmethod
    def character(user_id: str, guild_id: str) -> str:
        return f"character:{user_id}:{guild_id}"
    
    @staticmethod
    def episode_current(guild_id: str) -> str:
        return f"episode:{guild_id}:current"
    
    @staticmethod
    def episode_history(guild_id: str) -> str:
        return f"episode:{guild_id}:history"
    
    @staticmethod
    def guild_settings(guild_id: str) -> str:
        return f"guild:{guild_id}:settings"
    
    @staticmethod
    def memory_recent(guild_id: str, limit: int = 50) -> str:
        return f"memory:{guild_id}:recent:{limit}"
    
    @staticmethod
    def party(guild_id: str) -> str:
        return f"party:{guild_id}"
    
    @staticmethod
    def ai_response(context_hash: str) -> str:
        return f"ai:response:{context_hash}"