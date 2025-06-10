"""
Memory domain entity - Conversation and event memory
"""
from dataclasses import dataclass, field
from typing import Dict, Any, Optional
from datetime import datetime


@dataclass
class Memory:
    """Conversation and event memory for context"""
    
    # Identity
    guild_id: str
    episode_number: int
    
    # Content
    content: str
    memory_type: str = "general"  # interaction, event, combat, important, etc.
    
    # Context
    character_name: Optional[str] = None
    importance: int = 1  # 1-5 scale
    
    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    
    def __post_init__(self):
        """Validate memory data"""
        if not self.guild_id.strip():
            raise ValueError("Guild ID cannot be empty")
        
        if not self.content.strip():
            raise ValueError("Memory content cannot be empty")
        
        if not (1 <= self.importance <= 5):
            self.importance = 1  # Default to low importance
        
        if self.episode_number < 0:
            self.episode_number = 0
    
    def is_recent(self, hours: int = 24) -> bool:
        """Check if memory is within specified hours"""
        delta = datetime.now() - self.timestamp
        return delta.total_seconds() < (hours * 3600)
    
    def contains_character(self, character_name: str) -> bool:
        """Check if memory involves a specific character"""
        if self.character_name and self.character_name.lower() == character_name.lower():
            return True
        return character_name.lower() in self.content.lower()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "guild_id": self.guild_id,
            "episode_number": self.episode_number,
            "content": self.content,
            "memory_type": self.memory_type,
            "character_name": self.character_name,
            "importance": self.importance,
            "metadata": self.metadata,
            "timestamp": self.timestamp.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Memory":
        """Create memory from dictionary"""
        return cls(
            guild_id=data["guild_id"],
            episode_number=data["episode_number"],
            content=data["content"],
            memory_type=data.get("memory_type", "general"),
            character_name=data.get("character_name"),
            importance=data.get("importance", 1),
            metadata=data.get("metadata", {}),
            timestamp=datetime.fromisoformat(data["timestamp"])
        )