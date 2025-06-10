"""
Character management use cases
"""
import logging
from typing import Optional

from ...domain.services import CharacterService
from ...domain.interfaces.cache_service import CacheServiceInterface
from ...infrastructure.cache.memory_cache import CacheKeys
from ..dto import (
    CreateCharacterCommand, GenerateCharacterCommand, UpdateCharacterCommand,
    LevelUpCommand, HealCommand, DamageCommand, GetContextCommand,
    CharacterResult, HealthUpdateResult, PartyResult, ContextResult
)

logger = logging.getLogger(__name__)


class ManageCharacterUseCase:
    """Use case for character management operations"""
    
    def __init__(self, 
                 character_service: CharacterService,
                 cache_service: Optional[CacheServiceInterface] = None):
        self.character_service = character_service
        self.cache_service = cache_service
    
    async def create_character(self, command: CreateCharacterCommand) -> CharacterResult:
        """Create a new character"""
        try:
            logger.info(f"Creating character {command.name} for user {command.discord_user_id}")
            
            # Check if character already exists
            existing = await self.character_service.get_character(
                command.discord_user_id, 
                command.guild_id
            )
            
            if existing:
                return CharacterResult.failure(
                    f"You already have a character ({existing.name}) in this server. "
                    f"Delete it first if you want to create a new one."
                )
            
            # Create character
            character = await self.character_service.create_character(
                name=command.name,
                player_name=command.player_name,
                discord_user_id=command.discord_user_id,
                guild_id=command.guild_id,
                race=command.race,
                character_class=command.character_class,
                background=command.background,
                ability_scores=command.ability_scores
            )
            
            # Cache the character
            if self.cache_service:
                cache_key = CacheKeys.character(command.discord_user_id, command.guild_id)
                await self.cache_service.set(cache_key, character)
            
            logger.info(f"Successfully created character {character.name}")
            
            return CharacterResult.success_with_character(
                character=character,
                message=f"✨ Created **{character.name}**, a Level {character.level} {character.race.value} {character.character_class.value}!\n"
                       f"💚 HP: {character.current_hp}/{character.max_hp} | Initiative: +{character.get_initiative_modifier()}"
            )
            
        except ValueError as e:
            logger.warning(f"Character creation validation error: {e}")
            return CharacterResult.failure(str(e))
        except Exception as e:
            logger.error(f"Error creating character: {e}")
            return CharacterResult.failure(f"Failed to create character: {str(e)}")
    
    async def generate_character(self, command: GenerateCharacterCommand) -> CharacterResult:
        """Generate a character using AI"""
        try:
            logger.info(f"Generating character from description for user {command.discord_user_id}")
            
            # Check if character already exists
            existing = await self.character_service.get_character(
                command.discord_user_id,
                command.guild_id
            )
            
            if existing:
                return CharacterResult.failure(
                    f"You already have a character ({existing.name}) in this server."
                )
            
            # Generate character
            character = await self.character_service.generate_character_from_description(
                description=command.description,
                player_name=command.player_name,
                discord_user_id=command.discord_user_id,
                guild_id=command.guild_id
            )
            
            # Cache the character
            if self.cache_service:
                cache_key = CacheKeys.character(command.discord_user_id, command.guild_id)
                await self.cache_service.set(cache_key, character)
            
            logger.info(f"Successfully generated character {character.name}")
            
            return CharacterResult.success_with_character(
                character=character,
                message=f"🎲 Generated **{character.name}**, a Level {character.level} {character.race.value} {character.character_class.value}!\n"
                       f"💚 HP: {character.current_hp}/{character.max_hp}\n"
                       f"📜 Background: {character.background[:100]}{'...' if len(character.background) > 100 else ''}"
            )
            
        except ValueError as e:
            logger.warning(f"Character generation validation error: {e}")
            return CharacterResult.failure(str(e))
        except Exception as e:
            logger.error(f"Error generating character: {e}")
            return CharacterResult.failure(f"Failed to generate character: {str(e)}")
    
    async def get_character(self, discord_user_id: str, guild_id: str) -> CharacterResult:
        """Get a character"""
        try:
            # Check cache first
            if self.cache_service:
                cache_key = CacheKeys.character(discord_user_id, guild_id)
                cached_character = await self.cache_service.get(cache_key)
                if cached_character:
                    return CharacterResult.success_with_character(
                        character=cached_character,
                        message="Character retrieved from cache"
                    )
            
            # Get from repository
            character = await self.character_service.get_character(discord_user_id, guild_id)
            
            if not character:
                return CharacterResult.failure("No character found. Create one with `/character create`!")
            
            # Cache for next time
            if self.cache_service:
                cache_key = CacheKeys.character(discord_user_id, guild_id)
                await self.cache_service.set(cache_key, character)
            
            return CharacterResult.success_with_character(
                character=character,
                message=f"Found {character.name}"
            )
            
        except Exception as e:
            logger.error(f"Error getting character: {e}")
            return CharacterResult.failure(f"Failed to get character: {str(e)}")
    
    async def level_up_character(self, command: LevelUpCommand) -> CharacterResult:
        """Level up a character"""
        try:
            logger.info(f"Leveling up character for user {command.discord_user_id} to level {command.new_level}")
            
            character = await self.character_service.level_up_character(
                command.discord_user_id,
                command.guild_id,
                command.new_level
            )
            
            # Update cache
            if self.cache_service:
                cache_key = CacheKeys.character(command.discord_user_id, command.guild_id)
                await self.cache_service.set(cache_key, character)
            
            logger.info(f"Successfully leveled up {character.name} to level {character.level}")
            
            return CharacterResult.success_with_character(
                character=character,
                message=f"🎉 **{character.name}** leveled up to Level {character.level}!\n"
                       f"💚 Max HP increased to {character.max_hp}"
            )
            
        except ValueError as e:
            logger.warning(f"Level up validation error: {e}")
            return CharacterResult.failure(str(e))
        except Exception as e:
            logger.error(f"Error leveling up character: {e}")
            return CharacterResult.failure(f"Failed to level up: {str(e)}")
    
    async def heal_character(self, command: HealCommand) -> HealthUpdateResult:
        """Heal a character"""
        try:
            logger.info(f"Healing character for user {command.discord_user_id} by {command.amount}")
            
            character, actual_healing = await self.character_service.heal_character(
                command.discord_user_id,
                command.guild_id,
                command.amount
            )
            
            # Update cache
            if self.cache_service:
                cache_key = CacheKeys.character(command.discord_user_id, command.guild_id)
                await self.cache_service.set(cache_key, character)
            
            if actual_healing > 0:
                message = f"💚 **{character.name}** healed for {actual_healing} HP!\n" \
                         f"Current HP: {character.current_hp}/{character.max_hp} ({character.get_health_status()})"
            else:
                message = f"**{character.name}** is already at full health!"
            
            logger.info(f"Healed {character.name} for {actual_healing} HP")
            
            return HealthUpdateResult.success_with_health_change(
                character=character,
                amount_changed=actual_healing,
                message=message
            )
            
        except Exception as e:
            logger.error(f"Error healing character: {e}")
            return HealthUpdateResult(success=False, error=f"Failed to heal: {str(e)}")
    
    async def damage_character(self, command: DamageCommand) -> HealthUpdateResult:
        """Damage a character"""
        try:
            logger.info(f"Damaging character for user {command.discord_user_id} by {command.amount}")
            
            character, is_alive = await self.character_service.damage_character(
                command.discord_user_id,
                command.guild_id,
                command.amount
            )
            
            # Update cache
            if self.cache_service:
                cache_key = CacheKeys.character(command.discord_user_id, command.guild_id)
                await self.cache_service.set(cache_key, character)
            
            if is_alive:
                message = f"💔 **{character.name}** took {command.amount} {command.damage_type} damage!\n" \
                         f"Current HP: {character.current_hp}/{character.max_hp} ({character.get_health_status()})"
            else:
                message = f"💀 **{character.name}** took {command.amount} damage and is now unconscious!\n" \
                         f"HP: 0/{character.max_hp} - Make death saving throws!"
            
            logger.info(f"Damaged {character.name} for {command.amount} HP (alive: {is_alive})")
            
            return HealthUpdateResult.success_with_health_change(
                character=character,
                amount_changed=-command.amount,
                message=message
            )
            
        except Exception as e:
            logger.error(f"Error damaging character: {e}")
            return HealthUpdateResult(success=False, error=f"Failed to apply damage: {str(e)}")
    
    async def get_party(self, guild_id: str) -> PartyResult:
        """Get all party members in a guild"""
        try:
            logger.info(f"Getting party for guild {guild_id}")
            
            # Check cache first
            if self.cache_service:
                cache_key = CacheKeys.party(guild_id)
                cached_party = await self.cache_service.get(cache_key)
                if cached_party:
                    party_level = self.character_service.calculate_party_level(cached_party)
                    health_summary = self.character_service.get_party_health_summary(cached_party)
                    
                    return PartyResult.success_with_party(
                        party=cached_party,
                        level=party_level,
                        health_summary=health_summary,
                        message="Party retrieved from cache"
                    )
            
            # Get from repository
            party = await self.character_service.get_guild_party(guild_id)
            
            if not party:
                return PartyResult.success_with_party(
                    party=[],
                    level=0.0,
                    health_summary={},
                    message="No characters found in this server."
                )
            
            # Calculate party stats
            party_level = self.character_service.calculate_party_level(party)
            health_summary = self.character_service.get_party_health_summary(party)
            
            # Cache for next time
            if self.cache_service:
                cache_key = CacheKeys.party(guild_id)
                await self.cache_service.set(cache_key, party)
            
            logger.info(f"Found {len(party)} party members")
            
            return PartyResult.success_with_party(
                party=party,
                level=party_level,
                health_summary=health_summary,
                message=f"Found {len(party)} party members (avg level {party_level:.1f})"
            )
            
        except Exception as e:
            logger.error(f"Error getting party: {e}")
            return PartyResult(success=False, error=f"Failed to get party: {str(e)}")
    
    async def delete_character(self, discord_user_id: str, guild_id: str) -> CharacterResult:
        """Delete a character"""
        try:
            logger.info(f"Deleting character for user {discord_user_id}")
            
            # Get character first for confirmation message
            character = await self.character_service.get_character(discord_user_id, guild_id)
            if not character:
                return CharacterResult.failure("No character found to delete.")
            
            # Delete character
            deleted = await self.character_service.delete_character(discord_user_id, guild_id)
            
            if not deleted:
                return CharacterResult.failure("Failed to delete character.")
            
            # Remove from cache
            if self.cache_service:
                cache_key = CacheKeys.character(discord_user_id, guild_id)
                await self.cache_service.delete(cache_key)
                
                # Also invalidate party cache
                party_key = CacheKeys.party(guild_id)
                await self.cache_service.delete(party_key)
            
            logger.info(f"Successfully deleted character {character.name}")
            
            return CharacterResult(
                success=True,
                message=f"🗑️ Deleted **{character.name}**. You can create a new character anytime!"
            )
            
        except Exception as e:
            logger.error(f"Error deleting character: {e}")
            return CharacterResult.failure(f"Failed to delete character: {str(e)}")