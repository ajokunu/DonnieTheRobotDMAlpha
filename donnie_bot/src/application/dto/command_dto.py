"""
Command DTOs - Input data for use cases
"""
from dataclasses import dataclass
from typing import Optional, Dict, Any, List
from datetime import datetime

from ...domain.entities.character import Race, CharacterClass, AbilityScores
from ...domain.interfaces.voice_service import VoiceConfig


@dataclass
class CreateCharacterCommand:
    """Command to create a new character"""
    name: str
    player_name: str
    discord_user_id: str
    guild_id: str
    race: Race
    character_class: CharacterClass
    background: str = ""
    ability_scores: Optional[AbilityScores] = None


@dataclass
class GenerateCharacterCommand:
    """Command to AI-generate a character from description"""
    description: str
    player_name: str
    discord_user_id: str
    guild_id: str


@dataclass
class UpdateCharacterCommand:
    """Command to update character details"""
    discord_user_id: str
    guild_id: str
    updates: Dict[str, Any]


@dataclass
class LevelUpCommand:
    """Command to level up a character"""
    discord_user_id: str
    guild_id: str
    new_level: int


@dataclass
class HealCommand:
    """Command to heal a character"""
    discord_user_id: str
    guild_id: str
    amount: int
    source: str = "unknown"  # potion, spell, rest, etc.


@dataclass
class DamageCommand:
    """Command to damage a character"""
    discord_user_id: str
    guild_id: str
    amount: int
    damage_type: str = "untyped"
    source: str = "unknown"


@dataclass
class StartEpisodeCommand:
    """Command to start a new episode"""
    guild_id: str
    episode_name: str
    opening_scene: str = ""
    dm_user_id: str = ""


@dataclass
class EndEpisodeCommand:
    """Command to end current episode"""
    guild_id: str
    summary: str = ""
    closing_scene: str = ""
    dm_user_id: str = ""


@dataclass
class PlayerActionCommand:
    """Command for player action in episode"""
    guild_id: str
    discord_user_id: str
    action_text: str
    action_type: str = "general"  # combat, exploration, social, etc.
    target: Optional[str] = None


@dataclass
class DMActionCommand:
    """Command for DM-initiated action"""
    guild_id: str
    dm_user_id: str
    scene_description: str
    action_type: str = "narration"


@dataclass
class VoiceCommand:
    """Command for voice-related actions"""
    guild_id: str
    action: str  # join, leave, speak, change_voice
    channel_id: Optional[str] = None
    text_to_speak: Optional[str] = None
    voice_config: Optional[VoiceConfig] = None


@dataclass
class CombatActionCommand:
    """Command for combat actions"""
    guild_id: str
    discord_user_id: str
    action_type: str  # attack, spell, move, dodge, etc.
    target: Optional[str] = None
    details: str = ""


@dataclass
class SearchMemoryCommand:
    """Command to search conversation memory"""
    guild_id: str
    query: str
    limit: int = 10
    episode_number: Optional[int] = None


@dataclass
class UpdateGuildSettingsCommand:
    """Command to update guild settings"""
    guild_id: str
    settings: Dict[str, Any]
    updated_by: str = ""


@dataclass
class GetContextCommand:
    """Command to get current context for AI"""
    guild_id: str
    discord_user_id: Optional[str] = None
    include_recent_memories: bool = True
    memory_limit: int = 20