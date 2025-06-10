"""
Character Service - Pure business logic for character management
No external dependencies - only domain entities and interfaces!
"""
from typing import List, Optional, Dict, Any
from datetime import datetime

from ..entities.character import Character, Race, CharacterClass, AbilityScores
from ..interfaces.repositories import CharacterRepositoryInterface
from ..interfaces.ai_service import AIServiceInterface, AIContext


class CharacterService:
    """Service for character business logic and validation"""
    
    def __init__(self, 
                 character_repo: CharacterRepositoryInterface,
                 ai_service: Optional[AIServiceInterface] = None):
        self.character_repo = character_repo
        self.ai_service = ai_service
    
    async def create_character(self, 
                             name: str,
                             player_name: str, 
                             discord_user_id: str,
                             guild_id: str,
                             race: Race,
                             character_class: CharacterClass,
                             background: str = "",
                             ability_scores: Optional[AbilityScores] = None) -> Character:
        """Create a new character with validation"""
        
        # Check if character already exists
        existing = await self.character_repo.get_character(discord_user_id, guild_id)
        if existing:
            raise ValueError(f"Character already exists for user {discord_user_id} in guild {guild_id}")
        
        # Use default ability scores if not provided
        if ability_scores is None:
            ability_scores = self._generate_standard_array()
        
        # Create character entity
        character = Character(
            name=name.strip(),
            player_name=player_name.strip(),
            discord_user_id=discord_user_id,
            race=race,
            character_class=character_class,
            background=background.strip(),
            ability_scores=ability_scores,
            created_at=datetime.now().isoformat()
        )
        
        # Save to repository
        await self.character_repo.save_character(character)
        
        return character
    
    async def generate_character_from_description(self, 
                                                 description: str,
                                                 player_name: str,
                                                 discord_user_id: str,
                                                 guild_id: str) -> Character:
        """Generate character using AI from text description"""
        if not self.ai_service:
            raise ValueError("AI service required for character generation")
        
        # Check if character already exists
        existing = await self.character_repo.get_character(discord_user_id, guild_id)
        if existing:
            raise ValueError(f"Character already exists for user {discord_user_id}")
        
        # Generate character with AI
        character = await self.ai_service.generate_character_sheet(description)
        
        # Override with provided data
        character.player_name = player_name
        character.discord_user_id = discord_user_id
        character.created_at = datetime.now().isoformat()
        
        # Save to repository  
        await self.character_repo.save_character(character)
        
        return character
    
    async def get_character(self, discord_user_id: str, guild_id: str) -> Optional[Character]:
        """Get character by user and guild"""
        return await self.character_repo.get_character(discord_user_id, guild_id)
    
    async def update_character(self, character: Character) -> Character:
        """Update character with validation and timestamp"""
        character.last_updated = datetime.now().isoformat()
        await self.character_repo.save_character(character)
        return character
    
    async def delete_character(self, discord_user_id: str, guild_id: str) -> bool:
        """Delete a character"""
        return await self.character_repo.delete_character(discord_user_id, guild_id)
    
    async def get_guild_party(self, guild_id: str) -> List[Character]:
        """Get all characters in a guild (the party)"""
        return await self.character_repo.get_guild_characters(guild_id)
    
    async def level_up_character(self, discord_user_id: str, guild_id: str, new_level: int) -> Character:
        """Level up a character with business logic validation"""
        character = await self.character_repo.get_character(discord_user_id, guild_id)
        if not character:
            raise ValueError("Character not found")
        
        if not character.level_up(new_level):
            raise ValueError(f"Cannot level up from {character.level} to {new_level}")
        
        return await self.update_character(character)
    
    async def heal_character(self, discord_user_id: str, guild_id: str, amount: int) -> tuple[Character, int]:
        """Heal character and return character + actual healing amount"""
        character = await self.character_repo.get_character(discord_user_id, guild_id)
        if not character:
            raise ValueError("Character not found")
        
        actual_healing = character.heal(amount)
        updated_character = await self.update_character(character)
        
        return updated_character, actual_healing
    
    async def damage_character(self, discord_user_id: str, guild_id: str, amount: int) -> tuple[Character, bool]:
        """Damage character and return character + alive status"""
        character = await self.character_repo.get_character(discord_user_id, guild_id)
        if not character:
            raise ValueError("Character not found")
        
        is_alive = character.take_damage(amount)
        updated_character = await self.update_character(character)
        
        return updated_character, is_alive
    
    def validate_character_name(self, name: str, guild_characters: List[Character]) -> bool:
        """Validate character name is unique within guild"""
        name = name.strip().lower()
        
        # Check length
        if len(name) < 2 or len(name) > 30:
            return False
        
        # Check uniqueness
        existing_names = [char.name.lower() for char in guild_characters]
        return name not in existing_names
    
    def calculate_party_level(self, characters: List[Character]) -> float:
        """Calculate average party level"""
        if not characters:
            return 0.0
        
        total_level = sum(char.level for char in characters)
        return total_level / len(characters)
    
    def get_party_health_summary(self, characters: List[Character]) -> Dict[str, Any]:
        """Get summary of party health status"""
        if not characters:
            return {"total_characters": 0, "healthy": 0, "wounded": 0, "critical": 0, "unconscious": 0}
        
        summary = {"total_characters": len(characters), "healthy": 0, "wounded": 0, "critical": 0, "unconscious": 0}
        
        for char in characters:
            status = char.get_health_status().lower()
            if "unconscious" in status:
                summary["unconscious"] += 1
            elif "critical" in status or "badly" in status:
                summary["critical"] += 1
            elif "wound" in status:
                summary["wounded"] += 1
            else:
                summary["healthy"] += 1
        
        return summary
    
    def _generate_standard_array(self) -> AbilityScores:
        """Generate standard D&D ability score array (15,14,13,12,10,8)"""
        # This is the standard point-buy equivalent array
        return AbilityScores(
            strength=13,
            dexterity=14,
            constitution=15,
            intelligence=12,
            wisdom=10,
            charisma=8
        )
    
    def _generate_random_scores(self) -> AbilityScores:
        """Generate random ability scores using 4d6 drop lowest method"""
        import random
        
        def roll_ability():
            rolls = [random.randint(1, 6) for _ in range(4)]
            rolls.sort(reverse=True)
            return sum(rolls[:3])  # Sum the highest 3
        
        return AbilityScores(
            strength=roll_ability(),
            dexterity=roll_ability(),
            constitution=roll_ability(),
            intelligence=roll_ability(),
            wisdom=roll_ability(),
            charisma=roll_ability()
        )