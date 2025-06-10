from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from datetime import datetime

from ..entities.character import Character
from ..entities.episode import Episode
from ..entities.guild import Guild
from ..entities.memory import Memory


class CharacterRepositoryInterface(ABC):
    """Repository for character data persistence."""
    
    @abstractmethod
    async def get_character(self, user_id: str, guild_id: str) -> Optional[Character]:
        """Get character by user and guild ID."""
        pass
    
    @abstractmethod
    async def save_character(self, character: Character) -> None:
        """Save or update a character."""
        pass
    
    @abstractmethod
    async def delete_character(self, user_id: str, guild_id: str) -> bool:
        """Delete a character. Returns True if deleted."""
        pass
    
    @abstractmethod
    async def get_guild_characters(self, guild_id: str) -> List[Character]:
        """Get all characters in a guild."""
        pass


class EpisodeRepositoryInterface(ABC):
    """Repository for episode data persistence."""
    
    @abstractmethod
    async def get_current_episode(self, guild_id: str) -> Optional[Episode]:
        """Get the currently active episode for a guild."""
        pass
    
    @abstractmethod
    async def save_episode(self, episode: Episode) -> None:
        """Save or update an episode."""
        pass
    
    @abstractmethod
    async def get_episode_history(self, guild_id: str, limit: int = 10) -> List[Episode]:
        """Get recent episode history for a guild."""
        pass
    
    @abstractmethod
    async def end_episode(self, episode_id: str) -> None:
        """Mark an episode as ended."""
        pass


class GuildRepositoryInterface(ABC):
    """Repository for guild settings persistence."""
    
    @abstractmethod
    async def get_guild_settings(self, guild_id: str) -> Optional[Guild]:
        """Get guild settings."""
        pass
    
    @abstractmethod
    async def save_guild_settings(self, guild: Guild) -> None:
        """Save or update guild settings."""
        pass


class MemoryRepositoryInterface(ABC):
    """Repository for conversation memory persistence."""
    
    @abstractmethod
    async def save_memory(self, memory: Memory) -> None:
        """Save a memory entry."""
        pass
    
    @abstractmethod
    async def get_recent_memories(self, guild_id: str, limit: int = 50) -> List[Memory]:
        """Get recent memories for context."""
        pass
    
    @abstractmethod
    async def search_memories(self, guild_id: str, query: str, limit: int = 10) -> List[Memory]:
        """Search memories by content."""
        pass
    
    @abstractmethod
    async def clear_old_memories(self, guild_id: str, older_than: datetime) -> int:
        """Clear memories older than specified date. Returns count deleted."""
        pass