"""
Guild domain entity - Discord server settings
"""
from dataclasses import dataclass
from typing import Dict, Optional
from datetime import datetime

@dataclass
class VoiceSettings:
    """Voice/TTS settings for the guild"""
    enabled: bool = False
    speed: float = 1.25
    quality: str = "smart"  # "speed", "quality", "smart"
    
    def __post_init__(self):
        """Validate voice settings"""
        if not (0.25 <= self.speed <= 4.0):
            raise ValueError("Voice speed must be between 0.25 and 4.0")
        
        if self.quality not in ["speed", "quality", "smart"]:
            raise ValueError("Voice quality must be 'speed', 'quality', or 'smart'")
    
    def to_dict(self) -> Dict:
        return {
            "enabled": self.enabled,
            "speed": self.speed,
            "quality": self.quality,
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> "VoiceSettings":
        return cls(**data)

@dataclass
class Guild:
    """Discord guild configuration and state"""
    
    # Identity
    guild_id: str
    name: str = ""
    
    # Campaign State
    current_episode_number: int = 0
    current_scene: str = ""
    
    # Settings
    voice_settings: VoiceSettings = None
    
    # Metadata
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    def __post_init__(self):
        """Initialize default values"""
        if not self.guild_id.strip():
            raise ValueError("Guild ID cannot be empty")
        
        if self.voice_settings is None:
            self.voice_settings = VoiceSettings()
        
        if self.created_at is None:
            self.created_at = datetime.now()
        
        self.updated_at = datetime.now()
    
    def start_new_episode(self, episode_number: int) -> bool:
        """Start a new episode"""
        if episode_number <= self.current_episode_number:
            return False
        
        self.current_episode_number = episode_number
        self.updated_at = datetime.now()
        return True
    
    def update_scene(self, scene: str) -> None:
        """Update the current scene"""
        self.current_scene = scene
        self.updated_at = datetime.now()
    
    def update_voice_settings(self, **settings) -> None:
        """Update voice settings"""
        for key, value in settings.items():
            if hasattr(self.voice_settings, key):
                setattr(self.voice_settings, key, value)
        
        self.updated_at = datetime.now()
    
    def is_voice_enabled(self) -> bool:
        """Check if voice is enabled"""
        return self.voice_settings.enabled
    
    def has_active_episode(self) -> bool:
        """Check if there's an active episode"""
        return self.current_episode_number > 0
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization"""
        return {
            "guild_id": self.guild_id,
            "name": self.name,
            "current_episode_number": self.current_episode_number,
            "current_scene": self.current_scene,
            "voice_settings": self.voice_settings.to_dict(),
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> "Guild":
        """Create guild from dictionary"""
        voice_settings = VoiceSettings.from_dict(data.get("voice_settings", {}))
        
        return cls(
            guild_id=data["guild_id"],
            name=data.get("name", ""),
            current_episode_number=data.get("current_episode_number", 0),
            current_scene=data.get("current_scene", ""),
            voice_settings=voice_settings,
            created_at=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else None,
            updated_at=datetime.fromisoformat(data["updated_at"]) if data.get("updated_at") else None,
        )