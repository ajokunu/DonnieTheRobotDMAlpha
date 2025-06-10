"""
Episode management use cases
"""
import logging
from typing import Optional

from ...domain.services import EpisodeService, CharacterService, MemoryService
from ...domain.interfaces.cache_service import CacheServiceInterface
from ...infrastructure.cache.memory_cache import CacheKeys
from ..dto import (
    StartEpisodeCommand, EndEpisodeCommand, GetContextCommand,
    EpisodeResult, ContextResult
)

logger = logging.getLogger(__name__)


class StartEpisodeUseCase:
    """Use case for episode management operations"""
    
    def __init__(self,
                 episode_service: EpisodeService,
                 character_service: CharacterService,
                 memory_service: Optional[MemoryService] = None,
                 cache_service: Optional[CacheServiceInterface] = None):
        self.episode_service = episode_service
        self.character_service = character_service
        self.memory_service = memory_service
        self.cache_service = cache_service
    
    async def start_new_episode(self, command: StartEpisodeCommand) -> EpisodeResult:
        """Start a new episode"""
        try:
            logger.info(f"Starting new episode '{command.episode_name}' in guild {command.guild_id}")
            
            # Validate episode name
            if not self.episode_service.validate_episode_name(command.episode_name):
                return EpisodeResult.failure("Episode name must be between 3-100 characters.")
            
            # Check if there's already an active episode
            current_episode = await self.episode_service.get_current_episode(command.guild_id)
            if current_episode and current_episode.is_active():
                return EpisodeResult.failure(
                    f"Episode '{current_episode.name}' is already active. "
                    f"End it first with `/episode end` or use `/episode continue`."
                )
            
            # Create new episode
            episode = await self.episode_service.create_episode(
                guild_id=command.guild_id,
                name=command.episode_name,
                opening_scene=command.opening_scene
            )
            
            # Start the episode
            started_episode = await self.episode_service.start_episode(
                command.guild_id,
                command.opening_scene
            )
            
            # Take character snapshots for this episode
            party = await self.character_service.get_guild_party(command.guild_id)
            for character in party:
                started_episode.add_character_snapshot(
                    character.discord_user_id,
                    character.to_dict()
                )
            
            # Save episode with snapshots
            await self.episode_service.episode_repo.save_episode(started_episode)
            
            # Update cache
            if self.cache_service:
                episode_key = CacheKeys.episode_current(command.guild_id)
                await self.cache_service.set(episode_key, started_episode)
            
            # Create opening memory if we have memory service
            if self.memory_service and command.opening_scene:
                await self.memory_service.save_event_memory(
                    guild_id=command.guild_id,
                    episode_number=started_episode.episode_number,
                    event_description=f"Episode {started_episode.episode_number} begins: {command.opening_scene}",
                    memory_type="episode_start"
                )
            
            logger.info(f"Successfully started episode {started_episode.episode_number}: {started_episode.name}")
            
            message = f"🎬 **Episode {started_episode.episode_number}: {started_episode.name}** has begun!\n"
            if command.opening_scene:
                message += f"\n*{command.opening_scene}*\n"
            message += f"\n📊 Party size: {len(party)} characters"
            
            return EpisodeResult.success_with_episode(
                episode=started_episode,
                message=message
            )
            
        except ValueError as e:
            logger.warning(f"Episode creation validation error: {e}")
            return EpisodeResult.failure(str(e))
        except Exception as e:
            logger.error(f"Error starting episode: {e}")
            return EpisodeResult.failure(f"Failed to start episode: {str(e)}")
    
    async def continue_episode(self, guild_id: str) -> EpisodeResult:
        """Continue the current episode"""
        try:
            logger.info(f"Continuing episode in guild {guild_id}")
            
            episode = await self.episode_service.get_current_episode(guild_id)
            if not episode:
                return EpisodeResult.failure("No episode to continue. Start a new one with `/episode start`!")
            
            if not episode.is_active():
                # Restart the episode
                episode.status = episode.status.ACTIVE
                episode.start_time = episode.start_time or episode.created_at
                await self.episode_service.episode_repo.save_episode(episode)
                
                # Update cache
                if self.cache_service:
                    episode_key = CacheKeys.episode_current(guild_id)
                    await self.cache_service.set(episode_key, episode)
            
            # Get current context
            context = await self.episode_service.get_episode_context(guild_id)
            current_scene = context.get("current_scene", episode.opening_scene) if context else episode.opening_scene
            
            message = f"📖 **Continuing Episode {episode.episode_number}: {episode.name}**\n"
            if current_scene:
                message += f"\n*Current scene: {current_scene[:200]}{'...' if len(current_scene) > 200 else ''}*\n"
            message += f"\n⏰ Duration: {episode.get_duration_hours():.1f} hours"
            message += f"\n💬 Interactions: {episode.get_interaction_count()}"
            
            return EpisodeResult.success_with_episode(
                episode=episode,
                message=message
            )
            
        except Exception as e:
            logger.error(f"Error continuing episode: {e}")
            return EpisodeResult.failure(f"Failed to continue episode: {str(e)}")
    
    async def end_episode(self, command: EndEpisodeCommand) -> EpisodeResult:
        """End the current episode"""
        try:
            logger.info(f"Ending episode in guild {command.guild_id}")
            
            episode = await self.episode_service.end_current_episode(
                command.guild_id,
                command.summary,
                command.closing_scene
            )
            
            # Update cache
            if self.cache_service:
                episode_key = CacheKeys.episode_current(command.guild_id)
                await self.cache_service.set(episode_key, episode)
                
                # Also clear history cache to force refresh
                history_key = CacheKeys.episode_history(command.guild_id)
                await self.cache_service.delete(history_key)
            
            # Get episode stats
            stats = self.episode_service.get_episode_stats(episode)
            
            message = f"🏁 **Episode {episode.episode_number}: {episode.name}** has ended!\n"
            message += f"\n📊 **Episode Statistics:**"
            message += f"\n⏰ Duration: {stats['duration_hours']:.1f} hours"
            message += f"\n💬 Interactions: {stats['interaction_count']}"
            message += f"\n👥 Characters: {stats['character_count']}"
            
            if stats.get('most_active_character'):
                message += f"\n🌟 Most Active: {stats['most_active_character']}"
            
            if command.summary:
                message += f"\n\n📝 **Summary:** {command.summary}"
            
            if command.closing_scene:
                message += f"\n\n*{command.closing_scene}*"
            
            logger.info(f"Successfully ended episode {episode.episode_number}")
            
            return EpisodeResult.success_with_episode(
                episode=episode,
                message=message
            )
            
        except ValueError as e:
            logger.warning(f"Episode end validation error: {e}")
            return EpisodeResult.failure(str(e))
        except Exception as e:
            logger.error(f"Error ending episode: {e}")
            return EpisodeResult.failure(f"Failed to end episode: {str(e)}")
    
    async def get_episode_summary(self, guild_id: str, episode_number: Optional[int] = None) -> EpisodeResult:
        """Get a summary of an episode"""
        try:
            logger.info(f"Getting episode summary for guild {guild_id}, episode {episode_number}")
            
            summary = await self.episode_service.generate_episode_summary(guild_id, episode_number)
            
            # Get the episode for additional context
            if episode_number:
                history = await self.episode_service.get_episode_history(guild_id, limit=50)
                episode = next((ep for ep in history if ep.episode_number == episode_number), None)
            else:
                episode = await self.episode_service.get_current_episode(guild_id)
            
            if not episode:
                return EpisodeResult.failure("Episode not found.")
            
            return EpisodeResult.success_with_episode(
                episode=episode,
                message=f"📚 **Episode Summary**\n\n{summary}"
            )
            
        except Exception as e:
            logger.error(f"Error getting episode summary: {e}")
            return EpisodeResult.failure(f"Failed to get summary: {str(e)}")
    
    async def get_episode_history(self, guild_id: str, limit: int = 10) -> EpisodeResult:
        """Get episode history"""
        try:
            logger.info(f"Getting episode history for guild {guild_id}")
            
            # Check cache first
            if self.cache_service:
                history_key = CacheKeys.episode_history(guild_id)
                cached_history = await self.cache_service.get(history_key)
                if cached_history:
                    limited_history = cached_history[:limit]
                    return EpisodeResult(
                        success=True,
                        message="Episode history retrieved from cache",
                        metadata={"episodes": [ep.to_dict() for ep in limited_history]}
                    )
            
            # Get from repository
            episodes = await self.episode_service.get_episode_history(guild_id, limit)
            
            if not episodes:
                return EpisodeResult(
                    success=True,
                    message="No episodes found in this server.",
                    metadata={"episodes": []}
                )
            
            # Cache for next time
            if self.cache_service:
                history_key = CacheKeys.episode_history(guild_id)
                await self.cache_service.set(history_key, episodes)
            
            # Format history message
            message = f"📚 **Episode History** ({len(episodes)} episodes)\n\n"
            
            for episode in episodes[:5]:  # Show top 5 in message
                status_emoji = "🎬" if episode.is_active() else "✅" if episode.is_completed() else "📝"
                message += f"{status_emoji} **Episode {episode.episode_number}:** {episode.name}\n"
                message += f"   └ {episode.get_interaction_count()} interactions, {episode.get_duration_hours():.1f}h\n"
            
            if len(episodes) > 5:
                message += f"\n*(and {len(episodes) - 5} more episodes...)*"
            
            return EpisodeResult(
                success=True,
                message=message,
                metadata={"episodes": [ep.to_dict() for ep in episodes]}
            )
            
        except Exception as e:
            logger.error(f"Error getting episode history: {e}")
            return EpisodeResult.failure(f"Failed to get history: {str(e)}")
    
    async def get_current_context(self, command: GetContextCommand) -> ContextResult:
        """Get current context for the guild"""
        try:
            logger.info(f"Getting context for guild {command.guild_id}")
            
            # Get current episode
            episode = await self.episode_service.get_current_episode(command.guild_id)
            
            # Get active character if user provided
            character = None
            if command.discord_user_id:
                char_result = await self.character_service.get_character(
                    command.discord_user_id,
                    command.guild_id
                )
                if char_result:
                    character = char_result
            
            # Get recent memories
            memories = []
            if self.memory_service and command.include_recent_memories:
                memories = await self.memory_service.get_recent_context(
                    command.guild_id,
                    command.memory_limit
                )
            
            # Get party
            party = await self.character_service.get_guild_party(command.guild_id)
            
            # Build context summary
            summary_parts = []
            
            if episode:
                if episode.is_active():
                    summary_parts.append(f"Active Episode: {episode.name}")
                else:
                    summary_parts.append(f"Last Episode: {episode.name} ({episode.status.value})")
                summary_parts.append(f"Interactions: {episode.get_interaction_count()}")
            else:
                summary_parts.append("No episodes yet")
            
            if party:
                avg_level = self.character_service.calculate_party_level(party)
                summary_parts.append(f"Party: {len(party)} characters (avg level {avg_level:.1f})")
            
            if memories:
                summary_parts.append(f"Recent memories: {len(memories)} entries")
            
            context_summary = " | ".join(summary_parts)
            
            return ContextResult.success_with_context(
                episode=episode,
                character=character,
                memories=memories,
                party=party,
                summary=context_summary
            )
            
        except Exception as e:
            logger.error(f"Error getting context: {e}")
            return ContextResult(success=False, error=f"Failed to get context: {str(e)}")