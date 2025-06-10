"""
Claude AI service implementation
"""
import asyncio
from typing import List, Optional, Dict, Any
from anthropic import AsyncAnthropic

from ...domain.entities import Character, Episode, Memory
from ...domain.entities.character import Race, CharacterClass, AbilityScores
from ...domain.interfaces.ai_service import AIServiceInterface, AIResponse, AIContext
from ..config.settings import AIConfig


class ClaudeService(AIServiceInterface):
    """Claude AI service implementation"""
    
    def __init__(self, config: AIConfig):
        self.config = config
        self.client = AsyncAnthropic(api_key=config.api_key)
        
        # D&D context prompt
        self.system_prompt = """You are Donnie, an expert D&D Dungeon Master with years of experience running campaigns. 

Key traits:
- Creative storyteller who builds immersive worlds
- Fair but challenging gameplay
- Responds to player actions with consequences  
- Descriptive narration with vivid details
- Adapts to player choices dynamically
- Maintains campaign continuity and character development
- Uses appropriate D&D mechanics and terminology

Always respond in character as the DM, providing engaging narrative responses to player actions."""
    
    async def generate_dm_response(self, context: AIContext) -> AIResponse:
        """Generate a DM response for game progression"""
        
        # Build context prompt
        prompt = self._build_dm_prompt(context)
        
        try:
            message = await self.client.messages.create(
                model=self.config.model,
                max_tokens=self.config.max_tokens,
                temperature=self.config.temperature,
                system=self.system_prompt,
                messages=[{
                    "role": "user",
                    "content": prompt
                }]
            )
            
            response_text = message.content[0].text.strip()
            
            return AIResponse(
                text=response_text,
                metadata={
                    "model": self.config.model,
                    "tokens_used": message.usage.input_tokens + message.usage.output_tokens,
                    "type": "dm_response"
                }
            )
            
        except Exception as e:
            return AIResponse(
                text=f"*The DM pauses, gathering their thoughts...* (Error: {str(e)})",
                metadata={"error": str(e)}
            )
    
    async def generate_character_action_result(self, context: AIContext) -> AIResponse:
        """Generate result of a character's action"""
        
        prompt = f"""
        Character Action Resolution:
        
        Episode: {context.episode.name}
        Current Scene: {context.episode.interactions[-1].dm_response if context.episode.interactions else context.episode.opening_scene}
        
        Character: {context.character.name if context.character else "Unknown"}
        Player Action: {context.action_text}
        
        Provide a detailed result of this action, including:
        - Immediate consequences
        - Any dice rolls needed (describe the roll and outcome)
        - Environmental changes
        - NPC reactions
        - Next story beats
        
        Be descriptive and engaging while maintaining game balance.
        """
        
        try:
            message = await self.client.messages.create(
                model=self.config.model,
                max_tokens=self.config.max_tokens,
                temperature=self.config.temperature,
                system=self.system_prompt,
                messages=[{"role": "user", "content": prompt}]
            )
            
            return AIResponse(
                text=message.content[0].text.strip(),
                metadata={
                    "model": self.config.model,
                    "type": "action_result",
                    "character": context.character.name if context.character else None
                }
            )
            
        except Exception as e:
            return AIResponse(
                text=f"*Something magical interferes with the action...* (Error: {str(e)})",
                metadata={"error": str(e)}
            )
    
    async def generate_combat_narration(self, context: AIContext) -> AIResponse:
        """Generate combat narration and results"""
        
        prompt = f"""
        Combat Narration:
        
        Episode: {context.episode.name}
        Character: {context.character.name if context.character else "Unknown"}
        Combat Action: {context.action_text}
        
        Recent Context:
        {self._format_recent_memories(context.recent_memories)}
        
        Provide exciting combat narration including:
        - Vivid description of the action
        - Environmental details
        - Enemy reactions
        - Tactical situation updates
        - Dramatic tension
        
        Keep it fast-paced and engaging for D&D combat.
        """
        
        try:
            message = await self.client.messages.create(
                model=self.config.model,
                max_tokens=self.config.max_tokens,
                temperature=self.config.temperature + 0.1,  # Slightly more creative for combat
                system=self.system_prompt,
                messages=[{"role": "user", "content": prompt}]
            )
            
            return AIResponse(
                text=message.content[0].text.strip(),
                metadata={
                    "model": self.config.model,
                    "type": "combat_narration"
                }
            )
            
        except Exception as e:
            return AIResponse(
                text=f"*The battle rages on...* (Error: {str(e)})",
                metadata={"error": str(e)}
            )
    
    async def generate_character_sheet(self, character_description: str) -> Character:
        """Generate a character sheet from a description"""
        
        prompt = f"""
        Create a D&D 5e character based on this description:
        "{character_description}"
        
        Respond with ONLY a JSON object containing:
        {{
            "name": "Character Name",
            "race": "Race (Human/Elf/Dwarf/etc)",
            "character_class": "Class (Fighter/Wizard/etc)",
            "level": 1,
            "background": "Background description",
            "ability_scores": {{
                "strength": 10,
                "dexterity": 10,
                "constitution": 10,
                "intelligence": 10,
                "wisdom": 10,
                "charisma": 10
            }},
            "equipment": ["list", "of", "starting", "equipment"],
            "spells": ["list", "of", "spells", "if", "applicable"],
            "personality_traits": ["trait1", "trait2"]
        }}
        
        Use standard D&D ability scores (8-15 range), appropriate equipment for the class, and make it balanced for level 1.
        """
        
        try:
            message = await self.client.messages.create(
                model=self.config.model,
                max_tokens=800,
                temperature=0.7,
                messages=[{"role": "user", "content": prompt}]
            )
            
            # Parse JSON response
            import json
            response_text = message.content[0].text.strip()
            
            # Extract JSON from response (in case there's extra text)
            start = response_text.find('{')
            end = response_text.rfind('}') + 1
            json_text = response_text[start:end]
            
            char_data = json.loads(json_text)
            
            # Create character entity
            ability_scores = AbilityScores(**char_data["ability_scores"])
            
            character = Character(
                name=char_data["name"],
                player_name="Generated",  # Will be overridden
                discord_user_id="",  # Will be overridden
                race=Race(char_data["race"]),
                character_class=CharacterClass(char_data["character_class"]),
                level=char_data.get("level", 1),
                background=char_data.get("background", ""),
                ability_scores=ability_scores,
                equipment=char_data.get("equipment", []),
                spells=char_data.get("spells", []),
                personality_traits=char_data.get("personality_traits", [])
            )
            
            return character
            
        except Exception as e:
            # Return a default fighter if generation fails
            return Character(
                name="Generated Hero",
                player_name="Generated",
                discord_user_id="",
                race=Race.HUMAN,
                character_class=CharacterClass.FIGHTER,
                level=1,
                background=f"A hero born from: {character_description[:100]}...",
                equipment=["Longsword", "Shield", "Chain Mail", "Backpack", "50 gold pieces"]
            )
    
    async def summarize_episode(self, episode: Episode, memories: List[Memory]) -> str:
        """Create a summary of an episode"""
        
        # Format memories for context
        memory_text = "\n".join([
            f"- {memory.content[:200]}..." if len(memory.content) > 200 else f"- {memory.content}"
            for memory in memories[-20:]  # Last 20 memories
        ])
        
        prompt = f"""
        Create a concise summary of this D&D episode:
        
        Episode: {episode.name}
        Duration: {episode.get_duration_hours():.1f} hours
        Interactions: {episode.get_interaction_count()}
        Characters: {episode.get_character_count()}
        
        Key Events and Memories:
        {memory_text}
        
        Provide a 2-3 paragraph summary covering:
        - Main story beats and accomplishments
        - Character developments
        - Important discoveries or plot advances
        - Current status/cliffhangers
        
        Keep it engaging and suitable for campaign records.
        """
        
        try:
            message = await self.client.messages.create(
                model=self.config.model,
                max_tokens=500,
                temperature=0.5,
                system="You are a D&D campaign chronicler who creates engaging session summaries.",
                messages=[{"role": "user", "content": prompt}]
            )
            
            return message.content[0].text.strip()
            
        except Exception as e:
            # Fallback summary
            return f"""
            Episode {episode.episode_number}: {episode.name}
            
            The party continued their adventure with {episode.get_interaction_count()} interactions over {episode.get_duration_hours():.1f} hours. {episode.get_character_count()} characters participated in this session.
            
            {episode.opening_scene[:200] if episode.opening_scene else "The adventure continued..."}
            
            (Summary generation encountered an error: {str(e)})
            """
    
    async def analyze_player_intent(self, action_text: str) -> Dict[str, Any]:
        """Analyze what the player is trying to do"""
        
        prompt = f"""
        Analyze this D&D player action and respond with JSON:
        "{action_text}"
        
        {{
            "action_type": "combat/exploration/social/magic/skill_check",
            "difficulty": "easy/medium/hard/impossible",
            "requires_roll": true/false,
            "suggested_dc": 15,
            "ability_check": "strength/dexterity/etc or null",
            "risks": ["list", "of", "potential", "risks"],
            "opportunities": ["list", "of", "potential", "benefits"]
        }}
        """
        
        try:
            message = await self.client.messages.create(
                model=self.config.model,
                max_tokens=300,
                temperature=0.3,
                messages=[{"role": "user", "content": prompt}]
            )
            
            import json
            response_text = message.content[0].text.strip()
            start = response_text.find('{')
            end = response_text.rfind('}') + 1
            json_text = response_text[start:end]
            
            return json.loads(json_text)
            
        except Exception as e:
            # Default analysis
            return {
                "action_type": "exploration",
                "difficulty": "medium",
                "requires_roll": True,
                "suggested_dc": 15,
                "ability_check": None,
                "risks": ["Unknown consequences"],
                "opportunities": ["Potential discovery"],
                "error": str(e)
            }
    
    def _build_dm_prompt(self, context: AIContext) -> str:
        """Build a comprehensive prompt for DM responses"""
        
        parts = [
            f"Episode: {context.episode.name}",
            f"Current Scene: {context.episode.interactions[-1].dm_response if context.episode.interactions else context.episode.opening_scene}"
        ]
        
        if context.character:
            parts.append(f"Active Character: {context.character.name} (Level {context.character.level} {context.character.race.value} {context.character.character_class.value})")
            parts.append(f"Character Health: {context.character.current_hp}/{context.character.max_hp} HP ({context.character.get_health_status()})")
        
        if context.action_text:
            parts.append(f"Player Action: {context.action_text}")
        
        if context.recent_memories:
            parts.append("Recent Context:")
            parts.append(self._format_recent_memories(context.recent_memories))
        
        parts.append("\nProvide an engaging DM response that:")
        parts.append("- Acknowledges the player's action")
        parts.append("- Describes consequences and new developments") 
        parts.append("- Advances the story")
        parts.append("- Maintains immersion and excitement")
        
        return "\n".join(parts)
    
    def _format_recent_memories(self, memories: List[Memory]) -> str:
        """Format recent memories for AI context"""
        if not memories:
            return "No recent context available."
        
        formatted = []
        for memory in memories[-5:]:  # Last 5 memories
            if memory.character_name:
                formatted.append(f"- {memory.character_name}: {memory.content[:150]}...")
            else:
                formatted.append(f"- {memory.content[:150]}...")
        
        return "\n".join(formatted)