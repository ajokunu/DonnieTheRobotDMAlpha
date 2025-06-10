"""Domain interfaces for dependency inversion."""

from .repositories import (
    CharacterRepositoryInterface,
    EpisodeRepositoryInterface,
    GuildRepositoryInterface,
    MemoryRepositoryInterface,
)

from .ai_service import (
    AIServiceInterface,
    AIResponse,
    AIContext,
)

from .voice_service import (
    VoiceServiceInterface,
    VoiceConfig,
    AudioData,
)

from .cache_service import CacheServiceInterface

__all__ = [
    # Repository interfaces
    "CharacterRepositoryInterface",
    "EpisodeRepositoryInterface", 
    "GuildRepositoryInterface",
    "MemoryRepositoryInterface",
    
    # AI service interfaces
    "AIServiceInterface",
    "AIResponse",
    "AIContext",
    
    # Voice service interfaces
    "VoiceServiceInterface",
    "VoiceConfig",
    "AudioData",
    
    # Cache service interface
    "CacheServiceInterface",
]