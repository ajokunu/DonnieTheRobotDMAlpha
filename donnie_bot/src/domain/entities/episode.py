"""
Episode domain entity - Campaign session management
"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from enum import Enum
from datetime import datetime

class EpisodeStatus(Enum):
    PLANNED = "planned"
    ACTIVE = "active"
    COMPLETED = "completed"
    CANCELLED = "cancelled"

@dataclass
class SessionInteraction:
    """Single player interaction within an episode"""
    character_name: str
    player_action: str
    dm_response: str
    timestamp: str
    mode: str = "standard"  # How the response was generated
    
    def to_dict(self) -> Dict:
        return {
            "character_name": self.character_name,
            "player_action": self.player_action,
            "dm_response": self.dm_response,
            "timestamp": self.timestamp,
            "mode": self.mode,
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> "SessionInteraction":
        return cls(**data)

@dataclass
class Episode:
    """Campaign episode with session tracking"""
    
    # Identity
    guild_id: str
    episode_number: int
    name: str
    
    # Status
    status: EpisodeStatus = EpisodeStatus.PLANNED
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    
    # Content
    opening_scene: str = ""
    closing_scene: str = ""
    summary: str = ""
    
    # Session Data
    interactions: List[SessionInteraction] = field(default_factory=list)
    character_snapshots: Dict[str, Dict] = field(default_factory=dict)  # user_id -> snapshot
    
    # Metadata
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    def __post_init__(self):
        """Validate episode data"""
        if self.episode_number < 1:
            raise ValueError("Episode number must be positive")
        
        if not self.name.strip():
            raise ValueError("Episode name cannot be empty")
        
        if not self.guild_id.strip():
            raise ValueError("Guild ID cannot be empty")
    
    def start_episode(self, opening_scene: str = None) -> bool:
        """Start the episode"""
        if self.status != EpisodeStatus.PLANNED:
            return False
        
        self.status = EpisodeStatus.ACTIVE
        self.start_time = datetime.now()
        
        if opening_scene:
            self.opening_scene = opening_scene
        
        return True
    
    def end_episode(self, summary: str = "", closing_scene: str = "") -> bool:
        """End the episode"""
        if self.status != EpisodeStatus.ACTIVE:
            return False
        
        self.status = EpisodeStatus.COMPLETED
        self.end_time = datetime.now()
        
        if summary:
            self.summary = summary
        if closing_scene:
            self.closing_scene = closing_scene
        
        return True
    
    def add_interaction(self, character_name: str, player_action: str, 
                       dm_response: str, mode: str = "standard") -> None:
        """Add a player interaction to the session"""
        if self.status != EpisodeStatus.ACTIVE:
            raise ValueError("Cannot add interactions to inactive episode")
        
        interaction = SessionInteraction(
            character_name=character_name,
            player_action=player_action,
            dm_response=dm_response,
            timestamp=datetime.now().isoformat(),
            mode=mode
        )
        
        self.interactions.append(interaction)
        self.updated_at = datetime.now()
    
    def add_character_snapshot(self, user_id: str, character_data: Dict) -> None:
        """Take a snapshot of character state"""
        self.character_snapshots[user_id] = {
            **character_data,
            "snapshot_time": datetime.now().isoformat(),
            "episode_number": self.episode_number
        }
    
    def get_duration_hours(self) -> float:
        """Get episode duration in hours"""
        if not self.start_time:
            return 0.0
        
        end = self.end_time or datetime.now()
        delta = end - self.start_time
        return delta.total_seconds() / 3600
    
    def get_interaction_count(self) -> int:
        """Get total number of interactions"""
        return len(self.interactions)
    
    def get_character_count(self) -> int:
        """Get number of unique characters"""
        return len(set(interaction.character_name for interaction in self.interactions))
    
    def get_recent_interactions(self, count: int = 5) -> List[SessionInteraction]:
        """Get the most recent interactions"""
        return self.interactions[-count:] if self.interactions else []
    
    def is_active(self) -> bool:
        """Check if episode is currently active"""
        return self.status == EpisodeStatus.ACTIVE
    
    def is_completed(self) -> bool:
        """Check if episode is completed"""
        return self.status == EpisodeStatus.COMPLETED
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization"""
        return {
            "guild_id": self.guild_id,
            "episode_number": self.episode_number,
            "name": self.name,
            "status": self.status.value,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "opening_scene": self.opening_scene,
            "closing_scene": self.closing_scene,
            "summary": self.summary,
            "interactions": [interaction.to_dict() for interaction in self.interactions],
            "character_snapshots": self.character_snapshots,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> "Episode":
        """Create episode from dictionary"""
        interactions = [
            SessionInteraction.from_dict(interaction_data) 
            for interaction_data in data.get("interactions", [])
        ]
        
        return cls(
            guild_id=data["guild_id"],
            episode_number=data["episode_number"],
            name=data["name"],
            status=EpisodeStatus(data["status"]),
            start_time=datetime.fromisoformat(data["start_time"]) if data.get("start_time") else None,
            end_time=datetime.fromisoformat(data["end_time"]) if data.get("end_time") else None,
            opening_scene=data.get("opening_scene", ""),
            closing_scene=data.get("closing_scene", ""),
            summary=data.get("summary", ""),
            interactions=interactions,
            character_snapshots=data.get("character_snapshots", {}),
            created_at=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else None,
            updated_at=datetime.fromisoformat(data["updated_at"]) if data.get("updated_at") else None,
        )