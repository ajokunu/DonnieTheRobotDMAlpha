"""
Player and DM action handling use cases
"""
import logging
from typing import Optional
import hashlib

from ...domain.services import EpisodeService, CharacterService, MemoryService, CombatService
from ...domain.interfaces.ai_service import AIServiceInterface, AIContext
from ...domain.interfaces.cache_service import CacheServiceInterface
from ...infrastructure.cache.memory_cache import CacheKeys
from ..dto import (
    PlayerActionCommand, DMActionCommand, CombatActionCommand,
    ActionResult, CombatResult
)

logger = logging.getLogger(__name__)


class HandleActionUseCase:
    """Use case for handling player and DM actions"""
    
    def __init__(self,
                 episode_service: EpisodeService,
                 character_service: CharacterService,
                 ai_service: AIServiceInterface,
                 memory_service: Optional[MemoryService] = None,
                 combat_service: Optional[CombatService] = None,
                 cache_service: Optional[CacheServiceInterface] = None):
        self.episode_service = episode_service
        self.character_service = character_service
        self.ai_service = ai_service
        self.memory_service = memory_service
        self.combat_service = combat_service
        self.cache_service = cache_service
    
    async def handle_player_action(self, command: PlayerActionCommand) -> ActionResult:
        """Handle a player action in the current episode"""
        try:
            logger.info(f"Handling player action for user {command.discord_user_id}: {command.action_text[:50]}...")
            
            # Get current episode
            episode = await self.episode_service.get_current_episode(command.guild_id)
            if not episode:
                return ActionResult.failure("No active episode. Start one with `/episode start`!")
            
            if not episode.is_active():
                return ActionResult.failure(f"Episode '{episode.name}' is not active. Continue it with `/episode continue`!")
            
            # Get player's character
            character = await self.character_service.get_character(
                command.discord_user_id,
                command.guild_id
            )
            
            if not character:
                return ActionResult.failure("You don't have a character! Create one with `/character create`.")
            
            # Check if character is conscious
            if not character.is_conscious():
                return ActionResult.failure(f"**{character.name}** is unconscious and cannot act!")
            
            # Get recent memories for context
            recent_memories = []
            if self.memory_service:
                recent_memories = await self.memory_service.get_recent_context(command.guild_id, limit=10)
            
            # Build AI context
            context = AIContext(
                episode=episode,
                character=character,
                recent_memories=recent_memories,
                action_text=command.action_text
            )
            
            # Check cache for similar actions
            ai_response = None
            if self.cache_service:
                context_hash = self._hash_action_context(command.action_text, character.name, episode.episode_number)
                cache_key = CacheKeys.ai_response(context_hash)
                ai_response = await self.cache_service.get(cache_key)
            
            # Generate AI response if not cached
            if not ai_response:
                if command.action_type.lower() == "combat":
                    ai_response = await self.ai_service.generate_combat_narration(context)
                else:
                    ai_response = await self.ai_service.generate_character_action_result(context)
                
                # Cache the response
                if self.cache_service:
                    context_hash = self._hash_action_context(command.action_text, character.name, episode.episode_number)
                    cache_key = CacheKeys.ai_response(context_hash)
                    await self.cache_service.set(cache_key, ai_response)
            
            # Add interaction to episode
            updated_episode = await self.episode_service.add_player_interaction(
                guild_id=command.guild_id,
                character=character,
                player_action=command.action_text,
                dm_response=ai_response.text,
                mode="ai_generated"
            )
            
            # Update caches
            if self.cache_service:
                # Update episode cache
                episode_key = CacheKeys.episode_current(command.guild_id)
                await self.cache_service.set(episode_key, updated_episode)
                
                # Clear memory cache to force refresh
                memory_key = CacheKeys.memory_recent(command.guild_id)
                await self.cache_service.delete(memory_key)
            
            logger.info(f"Successfully processed action for {character.name}")
            
            return ActionResult.success_with_response(
                dm_response=ai_response,
                character=character,
                episode=updated_episode,
                message=f"Action processed for **{character.name}**"
            )
            
        except Exception as e:
            logger.error(f"Error handling player action: {e}")
            return ActionResult.failure(f"Failed to process action: {str(e)}")
    
    async def handle_dm_action(self, command: DMActionCommand) -> ActionResult:
        """Handle a DM-initiated action or scene change"""
        try:
            logger.info(f"Handling DM action in guild {command.guild_id}: {command.scene_description[:50]}...")
            
            # Get current episode
            episode = await self.episode_service.get_current_episode(command.guild_id)
            if not episode:
                return ActionResult.failure("No active episode. Start one with `/episode start`!")
            
            # Get recent memories for context
            recent_memories = []
            if self.memory_service:
                recent_memories = await self.memory_service.get_recent_context(command.guild_id, limit=5)
            
            # Build AI context for DM narration
            context = AIContext(
                episode=episode,
                recent_memories=recent_memories,
                action_text=command.scene_description
            )
            
            # Generate DM response
            ai_response = await self.ai_service.generate_dm_response(context)
            
            # Save as memory
            if self.memory_service:
                await self.memory_service.save_event_memory(
                    guild_id=command.guild_id,
                    episode_number=episode.episode_number,
                    event_description=f"DM: {command.scene_description}\nNarration: {ai_response.text}",
                    memory_type="dm_narration"
                )
            
            # Update episode with DM action
            episode.interactions.append(
                episode.SessionInteraction(
                    character_name="DM",
                    player_action=command.scene_description,
                    dm_response=ai_response.text,
                    timestamp=episode.datetime.now().isoformat(),
                    mode="dm_narration"
                )
            )
            
            await self.episode_service.episode_repo.save_episode(episode)
            
            # Update cache
            if self.cache_service:
                episode_key = CacheKeys.episode_current(command.guild_id)
                await self.cache_service.set(episode_key, episode)
            
            logger.info(f"Successfully processed DM action")
            
            return ActionResult.success_with_response(
                dm_response=ai_response,
                episode=episode,
                message="DM narration added to episode"
            )
            
        except Exception as e:
            logger.error(f"Error handling DM action: {e}")
            return ActionResult.failure(f"Failed to process DM action: {str(e)}")
    
    async def handle_combat_action(self, command: CombatActionCommand) -> CombatResult:
        """Handle a combat action with D&D mechanics"""
        try:
            logger.info(f"Handling combat action for user {command.discord_user_id}: {command.action_type}")
            
            if not self.combat_service:
                # Fallback to regular action if no combat service
                action_command = PlayerActionCommand(
                    guild_id=command.guild_id,
                    discord_user_id=command.discord_user_id,
                    action_text=f"{command.action_type}: {command.details}",
                    action_type="combat",
                    target=command.target
                )
                
                action_result = await self.handle_player_action(action_command)
                
                if action_result.success:
                    return CombatResult.success_with_combat(
                        outcome={"action": command.action_type, "target": command.target},
                        narrative=action_result.dm_response.text if action_result.dm_response else "",
                        message="Combat action processed (basic mode)"
                    )
                else:
                    return CombatResult(success=False, error=action_result.error)
            
            # Get character
            character = await self.character_service.get_character(
                command.discord_user_id,
                command.guild_id
            )
            
            if not character:
                return CombatResult(success=False, error="Character not found!")
            
            if not character.is_conscious():
                return CombatResult(success=False, error=f"**{character.name}** is unconscious!")
            
            # Create combat action
            from ...domain.services.combat_service import CombatAction
            combat_action = CombatAction(
                character_name=character.name,
                action_type=command.action_type,
                target=command.target,
                description=command.details
            )
            
            # Resolve combat action
            # Note: This is simplified - in a real implementation, you'd need target character data
            combat_result = self.combat_service.resolve_combat_action(
                action=combat_action,
                attacker=character,
                target=None,  # Would need to resolve target character
                combat_conditions={}
            )
            
            # Get current episode for narrative context
            episode = await self.episode_service.get_current_episode(command.guild_id)
            if episode and episode.is_active():
                # Add combat interaction to episode
                await self.episode_service.add_player_interaction(
                    guild_id=command.guild_id,
                    character=character,
                    player_action=f"Combat: {command.action_type} {command.target or ''}",
                    dm_response=combat_result.narrative,
                    mode="combat"
                )
            
            # Apply damage if any
            if combat_result.damage_dealt > 0:
                # This would typically damage the target character
                # For now, we'll just include it in the narrative
                pass
            
            logger.info(f"Successfully processed combat action for {character.name}")
            
            return CombatResult.success_with_combat(
                outcome={
                    "action": command.action_type,
                    "target": command.target,
                    "roll_result": combat_result.roll_result.to_dict() if combat_result.roll_result else None,
                    "damage_dealt": combat_result.damage_dealt,
                    "effects": combat_result.effects
                },
                narrative=combat_result.narrative,
                message=f"Combat action resolved for **{character.name}**"
            )
            
        except Exception as e:
            logger.error(f"Error handling combat action: {e}")
            return CombatResult(success=False, error=f"Failed to process combat: {str(e)}")
    
    async def analyze_player_intent(self, guild_id: str, action_text: str) -> ActionResult:
        """Analyze what a player is trying to do"""
        try:
            logger.info(f"Analyzing player intent: {action_text[:50]}...")
            
            # Use AI service to analyze intent
            analysis = await self.ai_service.analyze_player_intent(action_text)
            
            # Get current episode for additional context
            episode = await self.episode_service.get_current_episode(guild_id)
            
            return ActionResult(
                success=True,
                message=f"Intent Analysis: {analysis.get('action_type', 'unknown')} action",
                metadata={
                    "analysis": analysis,
                    "suggestions": {
                        "action_type": analysis.get("action_type"),
                        "difficulty": analysis.get("difficulty"),
                        "requires_roll": analysis.get("requires_roll"),
                        "suggested_dc": analysis.get("suggested_dc"),
                        "risks": analysis.get("risks", []),
                        "opportunities": analysis.get("opportunities", [])
                    },
                    "episode_context": episode.name if episode else "No active episode"
                }
            )
            
        except Exception as e:
            logger.error(f"Error analyzing player intent: {e}")
            return ActionResult.failure(f"Failed to analyze intent: {str(e)}")
    
    def _hash_action_context(self, action_text: str, character_name: str, episode_number: int) -> str:
        """Create a hash for action context caching"""
        context_string = f"{action_text.lower().strip()}_{character_name}_{episode_number}"
        return hashlib.md5(context_string.encode()).hexdigest()[:16]