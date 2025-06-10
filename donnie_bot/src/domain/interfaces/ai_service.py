from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from dataclasses import dataclass

from ..entities.character import Character
from ..entities.episode import Episode
from ..entities.memory import Memory


@dataclass
class AIResponse:
    """Response from AI service."""
    text: str
    audio_url: Optional[str] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@dataclass
class AIContext:
    """Context for AI generation."""
    episode: Episode
    character: Optional[Character] = None
    recent_memories: List[Memory] = None
    action_text: Optional[str] = None
    
    def __post_init__(self):
        if self.recent_memories is None:
            self.recent_memories = []


class AIServiceInterface(ABC):
    """Interface for AI text generation services."""
    
    @abstractmethod
    async def generate_dm_response(self, context: AIContext) -> AIResponse:
        """Generate a DM response for game progression."""
        pass
    
    @abstractmethod
    async def generate_character_action_result(self, context: AIContext) -> AIResponse:
        """Generate result of a character's action."""
        pass
    
    @abstractmethod
    async def generate_combat_narration(self, context: AIContext) -> AIResponse:
        """Generate combat narration and results."""
        pass
    
    @abstractmethod
    async def generate_character_sheet(self, character_description: str) -> Character:
        """Generate a character sheet from a description."""
        pass
    
    @abstractmethod
    async def summarize_episode(self, episode: Episode, memories: List[Memory]) -> str:
        """Create a summary of an episode."""
        pass
    
    @abstractmethod
    async def analyze_player_intent(self, action_text: str) -> Dict[str, Any]:
        """Analyze what the player is trying to do."""
        pass