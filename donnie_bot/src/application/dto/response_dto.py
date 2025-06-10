"""
Response DTOs - Output data from use cases
"""
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List
from datetime import datetime

from ...domain.entities import Character, Episode, Guild, Memory
from ...domain.interfaces.ai_service import AIResponse
from ...domain.interfaces.voice_service import AudioData


@dataclass
class CommandResult:
    """Base result for all commands"""
    success: bool
    message: str = ""
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CharacterResult(CommandResult):
    """Result containing character data"""
    character: Optional[Character] = None
    
    @classmethod
    def success_with_character(cls, character: Character, message: str = "") -> "CharacterResult":
        return cls(success=True, character=character, message=message)
    
    @classmethod
    def failure(cls, error: str) -> "CharacterResult":
        return cls(success=False, error=error)


@dataclass
class EpisodeResult(CommandResult):
    """Result containing episode data"""
    episode: Optional[Episode] = None
    
    @classmethod
    def success_with_episode(cls, episode: Episode, message: str = "") -> "EpisodeResult":
        return cls(success=True, episode=episode, message=message)
    
    @classmethod
    def failure(cls, error: str) -> "EpisodeResult":
        return cls(success=False, error=error)


@dataclass
class ActionResult(CommandResult):
    """Result of a player or DM action"""
    dm_response: Optional[AIResponse] = None
    updated_character: Optional[Character] = None
    updated_episode: Optional[Episode] = None
    requires_voice: bool = False
    
    @classmethod
    def success_with_response(cls, 
                            dm_response: AIResponse, 
                            character: Optional[Character] = None,
                            episode: Optional[Episode] = None,
                            message: str = "") -> "ActionResult":
        return cls(
            success=True, 
            dm_response=dm_response,
            updated_character=character,
            updated_episode=episode,
            message=message
        )


@dataclass
class VoiceResult(CommandResult):
    """Result of voice operations"""
    audio_data: Optional[AudioData] = None
    is_connected: bool = False
    
    @classmethod
    def success_with_audio(cls, audio_data: AudioData, message: str = "") -> "VoiceResult":
        return cls(success=True, audio_data=audio_data, message=message)
    
    @classmethod
    def connection_success(cls, is_connected: bool, message: str = "") -> "VoiceResult":
        return cls(success=True, is_connected=is_connected, message=message)


@dataclass
class MemorySearchResult(CommandResult):
    """Result of memory search"""
    memories: List[Memory] = field(default_factory=list)
    total_found: int = 0
    
    @classmethod
    def success_with_memories(cls, memories: List[Memory], message: str = "") -> "MemorySearchResult":
        return cls(
            success=True, 
            memories=memories, 
            total_found=len(memories),
            message=message
        )


@dataclass
class ContextResult(CommandResult):
    """Result containing current context"""
    current_episode: Optional[Episode] = None
    active_character: Optional[Character] = None
    recent_memories: List[Memory] = field(default_factory=list)
    guild_settings: Optional[Guild] = None
    party_members: List[Character] = field(default_factory=list)
    context_summary: str = ""
    
    @classmethod
    def success_with_context(cls, 
                           episode: Optional[Episode] = None,
                           character: Optional[Character] = None,
                           memories: List[Memory] = None,
                           guild: Optional[Guild] = None,
                           party: List[Character] = None,
                           summary: str = "") -> "ContextResult":
        return cls(
            success=True,
            current_episode=episode,
            active_character=character,
            recent_memories=memories or [],
            guild_settings=guild,
            party_members=party or [],
            context_summary=summary
        )


@dataclass
class CombatResult(CommandResult):
    """Result of combat actions"""
    combat_outcome: Optional[Dict[str, Any]] = None
    damage_dealt: int = 0
    damage_taken: int = 0
    effects_applied: List[str] = field(default_factory=list)
    narrative: str = ""
    
    @classmethod
    def success_with_combat(cls,
                          outcome: Dict[str, Any],
                          narrative: str = "",
                          message: str = "") -> "CombatResult":
        return cls(
            success=True,
            combat_outcome=outcome,
            narrative=narrative,
            message=message
        )


@dataclass
class HealthUpdateResult(CommandResult):
    """Result of healing or damage commands"""
    updated_character: Optional[Character] = None
    amount_changed: int = 0
    health_status: str = ""
    is_alive: bool = True
    
    @classmethod
    def success_with_health_change(cls,
                                 character: Character,
                                 amount_changed: int,
                                 message: str = "") -> "HealthUpdateResult":
        return cls(
            success=True,
            updated_character=character,
            amount_changed=amount_changed,
            health_status=character.get_health_status(),
            is_alive=character.is_alive(),
            message=message
        )


@dataclass
class PartyResult(CommandResult):
    """Result containing party information"""
    party_members: List[Character] = field(default_factory=list)
    party_level: float = 0.0
    health_summary: Dict[str, Any] = field(default_factory=dict)
    
    @classmethod
    def success_with_party(cls, 
                         party: List[Character],
                         level: float,
                         health_summary: Dict[str, Any],
                         message: str = "") -> "PartyResult":
        return cls(
            success=True,
            party_members=party,
            party_level=level,
            health_summary=health_summary,
            message=message
        )