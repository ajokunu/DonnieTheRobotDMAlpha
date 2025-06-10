"""
Episode Service - Business logic for episode and session management
"""
from typing import List, Optional, Dict, Any
from datetime import datetime

from ..entities.episode import Episode, EpisodeStatus, SessionInteraction
from ..entities.character import Character
from ..entities.memory import Memory
from ..interfaces.repositories import EpisodeRepositoryInterface, MemoryRepositoryInterface
from ..interfaces.ai_service import AIServiceInterface, AIContext


class EpisodeService:
    """Service for episode management and session progression"""
    
    def __init__(self,
                 episode_repo: EpisodeRepositoryInterface,
                 memory_repo: Optional[MemoryRepositoryInterface] = None,
                 ai_service: Optional[AIServiceInterface] = None):
        self.episode_repo = episode_repo
        self.memory_repo = memory_repo
        self.ai_service = ai_service
    
    async def create_episode(self, 
                           guild_id: str,
                           name: str,
                           opening_scene: str = "") -> Episode:
        """Create a new episode"""
        
        # Get current episode to determine next number
        current = await self.episode_repo.get_current_episode(guild_id)
        next_number = 1 if not current else current.episode_number + 1
        
        # End current episode if it exists and is active
        if current and current.is_active():
            await self.end_current_episode(guild_id, "Episode ended to start new one")
        
        # Create new episode
        episode = Episode(
            guild_id=guild_id,
            episode_number=next_number,
            name=name.strip(),
            opening_scene=opening_scene.strip(),
            status=EpisodeStatus.PLANNED,
            created_at=datetime.now()
        )
        
        await self.episode_repo.save_episode(episode)
        return episode
    
    async def start_episode(self, 
                          guild_id: str,
                          opening_scene: Optional[str] = None) -> Episode:
        """Start the current planned episode"""
        
        episode = await self.episode_repo.get_current_episode(guild_id)
        if not episode:
            raise ValueError("No episode found to start")
        
        if not episode.start_episode(opening_scene):
            raise ValueError(f"Cannot start episode in {episode.status.value} status")
        
        await self.episode_repo.save_episode(episode)
        
        # Save opening as memory if provided
        if opening_scene and self.memory_repo:
            opening_memory = Memory(
                guild_id=guild_id,
                episode_number=episode.episode_number,
                content=f"Episode {episode.episode_number} begins: {opening_scene}",
                memory_type="episode_start",
                timestamp=datetime.now()
            )
            await self.memory_repo.save_memory(opening_memory)
        
        return episode
    
    async def end_current_episode(self, 
                                guild_id: str,
                                summary: str = "",
                                closing_scene: str = "") -> Episode:
        """End the current active episode"""
        
        episode = await self.episode_repo.get_current_episode(guild_id)
        if not episode:
            raise ValueError("No active episode found")
        
        # Generate summary if not provided and AI is available
        if not summary and self.ai_service and self.memory_repo:
            memories = await self.memory_repo.get_recent_memories(guild_id, limit=100)
            summary = await self.ai_service.summarize_episode(episode, memories)
        
        if not episode.end_episode(summary, closing_scene):
            raise ValueError(f"Cannot end episode in {episode.status.value} status")
        
        await self.episode_repo.save_episode(episode)
        
        # Save closing as memory
        if closing_scene and self.memory_repo:
            closing_memory = Memory(
                guild_id=guild_id,
                episode_number=episode.episode_number,
                content=f"Episode {episode.episode_number} ends: {closing_scene}",
                memory_type="episode_end",
                timestamp=datetime.now()
            )
            await self.memory_repo.save_memory(closing_memory)
        
        return episode
    
    async def add_player_interaction(self,
                                   guild_id: str,
                                   character: Character,
                                   player_action: str,
                                   dm_response: str,
                                   mode: str = "standard") -> Episode:
        """Add a player interaction to the current episode"""
        
        episode = await self.episode_repo.get_current_episode(guild_id)
        if not episode:
            raise ValueError("No active episode found")
        
        if not episode.is_active():
            raise ValueError("Episode is not active")
        
        # Add interaction to episode
        episode.add_interaction(character.name, player_action, dm_response, mode)
        
        # Save character snapshot
        episode.add_character_snapshot(character.discord_user_id, character.to_dict())
        
        await self.episode_repo.save_episode(episode)
        
        # Save as memory
        if self.memory_repo:
            interaction_memory = Memory(
                guild_id=guild_id,
                episode_number=episode.episode_number,
                character_name=character.name,
                content=f"{character.name}: {player_action}\nDM: {dm_response}",
                memory_type="interaction",
                timestamp=datetime.now()
            )
            await self.memory_repo.save_memory(interaction_memory)
        
        return episode
    
    async def get_current_episode(self, guild_id: str) -> Optional[Episode]:
        """Get the current episode for a guild"""
        return await self.episode_repo.get_current_episode(guild_id)
    
    async def get_episode_history(self, guild_id: str, limit: int = 10) -> List[Episode]:
        """Get episode history for a guild"""
        return await self.episode_repo.get_episode_history(guild_id, limit)
    
    async def get_episode_context(self, guild_id: str) -> Optional[Dict[str, Any]]:
        """Get context for current episode including recent interactions"""
        episode = await self.episode_repo.get_current_episode(guild_id)
        if not episode:
            return None
        
        recent_interactions = episode.get_recent_interactions(5)
        
        context = {
            "episode_number": episode.episode_number,
            "episode_name": episode.name,
            "status": episode.status.value,
            "opening_scene": episode.opening_scene,
            "current_scene": episode.interactions[-1].dm_response if episode.interactions else episode.opening_scene,
            "recent_interactions": [interaction.to_dict() for interaction in recent_interactions],
            "character_count": episode.get_character_count(),
            "interaction_count": episode.get_interaction_count(),
            "duration_hours": episode.get_duration_hours()
        }
        
        return context
    
    def validate_episode_name(self, name: str) -> bool:
        """Validate episode name"""
        name = name.strip()
        return 3 <= len(name) <= 100
    
    def get_episode_stats(self, episode: Episode) -> Dict[str, Any]:
        """Get statistics for an episode"""
        if not episode.interactions:
            return {
                "duration_hours": episode.get_duration_hours(),
                "interaction_count": 0,
                "character_count": 0,
                "average_response_length": 0,
                "most_active_character": None
            }
        
        # Calculate stats
        response_lengths = [len(interaction.dm_response) for interaction in episode.interactions]
        character_counts = {}
        
        for interaction in episode.interactions:
            character_counts[interaction.character_name] = character_counts.get(interaction.character_name, 0) + 1
        
        most_active = max(character_counts.items(), key=lambda x: x[1]) if character_counts else None
        
        return {
            "duration_hours": episode.get_duration_hours(),
            "interaction_count": len(episode.interactions),
            "character_count": len(character_counts),
            "average_response_length": sum(response_lengths) / len(response_lengths),
            "most_active_character": most_active[0] if most_active else None,
            "character_interaction_counts": character_counts
        }
    
    async def generate_episode_summary(self, guild_id: str, episode_number: Optional[int] = None) -> str:
        """Generate a summary of an episode"""
        if episode_number:
            # Get specific episode from history
            history = await self.episode_repo.get_episode_history(guild_id, limit=50)
            episode = next((ep for ep in history if ep.episode_number == episode_number), None)
        else:
            # Get current episode
            episode = await self.episode_repo.get_current_episode(guild_id)
        
        if not episode:
            raise ValueError("Episode not found")
        
        # If AI service available, generate intelligent summary
        if self.ai_service and self.memory_repo:
            memories = await self.memory_repo.get_recent_memories(guild_id, limit=100)
            episode_memories = [m for m in memories if m.episode_number == episode.episode_number]
            return await self.ai_service.summarize_episode(episode, episode_memories)
        
        # Otherwise, create basic summary
        stats = self.get_episode_stats(episode)
        summary_parts = [
            f"Episode {episode.episode_number}: {episode.name}",
            f"Duration: {stats['duration_hours']:.1f} hours",
            f"Interactions: {stats['interaction_count']}",
            f"Characters: {stats['character_count']}"
        ]
        
        if episode.opening_scene:
            summary_parts.append(f"Opening: {episode.opening_scene[:100]}...")
        
        if episode.closing_scene:
            summary_parts.append(f"Closing: {episode.closing_scene[:100]}...")
        
        return "\n".join(summary_parts)