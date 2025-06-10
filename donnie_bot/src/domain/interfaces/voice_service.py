from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
from dataclasses import dataclass


@dataclass
class VoiceConfig:
    """Configuration for voice synthesis."""
    voice_id: str = "default"
    speed: float = 1.0
    pitch: float = 1.0
    volume: float = 1.0
    language: str = "en"


@dataclass
class AudioData:
    """Audio data container."""
    data: bytes
    format: str = "mp3"
    duration_seconds: Optional[float] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class VoiceServiceInterface(ABC):
    """Interface for voice synthesis and playback services."""
    
    @abstractmethod
    async def text_to_speech(self, text: str, config: VoiceConfig = None) -> AudioData:
        """Convert text to speech audio."""
        pass
    
    @abstractmethod
    async def play_audio(self, guild_id: str, audio_data: AudioData) -> bool:
        """Play audio in a voice channel. Returns True if successful."""
        pass
    
    @abstractmethod
    async def join_voice_channel(self, guild_id: str, channel_id: str) -> bool:
        """Join a voice channel. Returns True if successful."""
        pass
    
    @abstractmethod
    async def leave_voice_channel(self, guild_id: str) -> None:
        """Leave the current voice channel."""
        pass
    
    @abstractmethod
    async def is_connected(self, guild_id: str) -> bool:
        """Check if connected to a voice channel in guild."""
        pass
    
    @abstractmethod
    async def get_supported_voices(self) -> List[str]:
        """Get list of available voice IDs."""
        pass