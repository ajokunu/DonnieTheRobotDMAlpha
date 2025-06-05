# combat_integration.py
"""
DM Donnie Combat Integration Module
Connects combat system to main bot with minimal changes
"""

import asyncio
from typing import Dict, Optional, Tuple
from .combat_manager import CombatManager
from .combat_display import CombatDisplayManager

class CombatIntegration:
    """Manages combat for DM Donnie with separate auto-updating displays"""
    
    def __init__(self, bot, campaign_context):
        self.bot = bot
        self.campaign_context = campaign_context
        self.display_manager = CombatDisplayManager(bot)
        self.combat_managers: Dict[int, CombatManager] = {}
        
    async def initialize(self):
        """Initialize combat system"""
        await self.display_manager.start()
        print("✅ DM Donnie combat system initialized")
    
    def get_combat_manager(self, channel_id: int) -> CombatManager:
        """Get or create combat manager for channel"""
        if channel_id not in self.combat_managers:
            self.combat_managers[channel_id] = CombatManager(channel_id)
        return self.combat_managers[channel_id]
    
    async def process_action_with_combat(self, user_id: str, player_input: str, 
                                       channel_id: int) -> Tuple[str, Optional[str]]:
        """Process action with combat awareness"""
        combat_manager = self.get_combat_manager(channel_id)
        
        # Only get combat context if combat is active
        combat_context = None
        if combat_manager.is_combat_active():
            combat_context = self._get_enhanced_combat_context(combat_manager)
        
        # Use existing fast response system with combat context
        dm_response = await self._get_fast_response_with_context(
            user_id, player_input, combat_context or ""
        )
        
        # Process combat state in background
        asyncio.create_task(self._update_combat_background(
            combat_manager, player_input, dm_response, channel_id
        ))
        
        return dm_response, combat_context
    
    async def _get_fast_response_with_context(self, user_id: str, player_input: str, 
                                            combat_context: str) -> str:
        """Enhanced fast response with combat context"""
        try:
            # Get character info
            player_data = self.campaign_context["players"][user_id]
            char_data = player_data["character_data"]
            character_name = char_data["name"]
            
            # Build prompt with enhanced combat context
            if combat_context:
                base_prompt = f"""Donnie DM responds to {character_name}: {player_input}
Storm King's Thunder. {combat_context}
Keep under 300 chars:"""
            else:
                base_prompt = f"""Donnie DM responds to {character_name}: {player_input}
Storm King's Thunder.
Keep under 300 chars:"""
            
            # Import Claude client from main
            from main import claude_client, RESPONSE_TIMEOUT
            
            response = await asyncio.wait_for(
                asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: claude_client.messages.create(
                        model="claude-sonnet-4-20250514",
                        max_tokens=80,
                        temperature=0.7,
                        messages=[{"role": "user", "content": base_prompt}]
                    )
                ),
                timeout=RESPONSE_TIMEOUT
            )
            
            dm_response = response.content[0].text.strip()
            
            if len(dm_response) > 450:
                dm_response = dm_response[:447] + "..."
            
            return dm_response
            
        except asyncio.TimeoutError:
            return "Donnie pauses to assess the tactical situation..."
        except Exception as e:
            print(f"❌ Combat response error: {e}")
            return "Donnie gathers his thoughts momentarily..."
    
    async def _update_combat_background(self, combat_manager: CombatManager, 
                                      player_input: str, dm_response: str, 
                                      channel_id: int):
        """Update combat state in background"""
        try:
            await asyncio.sleep(0.1)  # Ensure response sent first
            
            # Parse DM response for combat info
            combat_detected = combat_manager.quick_parse_dm_response(dm_response)
            
            if combat_detected:
                # Queue display update (happens in background)
                await self.display_manager.queue_update(channel_id, combat_manager)
                print(f"✅ Combat state updated for channel {channel_id}")
                
                # Check for turn changes and announce
                await self._check_and_announce_turn(channel_id, combat_manager)
            
        except Exception as e:
            print(f"❌ Background combat processing error: {e}")
    
    async def _check_and_announce_turn(self, channel_id: int, combat_manager: CombatManager):
        """Check for turn changes and announce next player"""
        try:
            if hasattr(combat_manager, 'get_current_turn') and hasattr(combat_manager, 'get_round_number'):
                current_turn = combat_manager.get_current_turn()
                round_num = combat_manager.get_round_number()
                
                if current_turn and hasattr(combat_manager, 'turn_announced'):
                    # Check if we need to announce this turn
                    turn_key = f"{round_num}_{current_turn}"
                    if not getattr(combat_manager, 'last_announced_turn', None) == turn_key:
                        combat_manager.last_announced_turn = turn_key
                        
                        channel = self.bot.get_channel(channel_id)
                        if channel:
                            # Get status effects for current player
                            status_text = self._get_status_reminder(combat_manager, current_turn)
                            status_part = f" {status_text}" if status_text else ""
                            
                            await channel.send(f"🎯 **Round {round_num}** - It's {current_turn}'s turn!{status_part}")
        except Exception as e:
            print(f"❌ Turn announcement error: {e}")
    
    def _get_enhanced_combat_context(self, combat_manager: CombatManager) -> str:
        """Get enhanced combat context with round counter and status effects"""
        try:
            # Start with minimal context
            context = combat_manager.get_minimal_context()
            
            # Add round information
            if hasattr(combat_manager, 'get_round_number'):
                round_num = combat_manager.get_round_number()
                if round_num > 0:
                    context += f" Round {round_num}."
            
            # Add current turn info
            if hasattr(combat_manager, 'get_current_turn'):
                current_turn = combat_manager.get_current_turn()
                if current_turn:
                    context += f" {current_turn}'s turn."
                    
                    # Add status effects for current character
                    status_reminder = self._get_status_reminder(combat_manager, current_turn)
                    if status_reminder:
                        context += f" Status: {status_reminder}"
            
            return context
            
        except Exception as e:
            print(f"❌ Enhanced combat context error: {e}")
            # Fallback to minimal context
            return combat_manager.get_minimal_context()
    
    def _get_status_reminder(self, combat_manager: CombatManager, character_name: str) -> str:
        """Get status effect reminders for character"""
        try:
            if hasattr(combat_manager, 'get_character_status'):
                status_effects = combat_manager.get_character_status(character_name)
                if status_effects:
                    return f"({', '.join(status_effects)})"
        except:
            pass
        return ""
    
    def add_player_to_combat(self, channel_id: int, user_id: str, initiative: int):
        """Add player to combat"""
        if user_id in self.campaign_context["players"]:
            char_data = self.campaign_context["players"][user_id]["character_data"]
            combat_manager = self.get_combat_manager(channel_id)
            combat_manager.add_player(user_id, char_data["name"], initiative)
            
            # Queue display update
            asyncio.create_task(
                self.display_manager.queue_update(channel_id, combat_manager)
            )
    
    async def quick_join_combat(self, channel_id: int, user_id: str, initiative_roll: int = None):
        """Quick initiative roll and join combat"""
        if user_id in self.campaign_context["players"]:
            char_data = self.campaign_context["players"][user_id]["character_data"]
            character_name = char_data["name"]
            
            # Auto-roll initiative if not provided
            if initiative_roll is None:
                import random
                initiative_modifier = char_data.get("initiative_modifier", 0)
                d20_roll = random.randint(1, 20)
                initiative_roll = d20_roll + initiative_modifier
                roll_text = f" (rolled {d20_roll} + {initiative_modifier})"
            else:
                roll_text = ""
            
            # Add to combat
            self.add_player_to_combat(channel_id, user_id, initiative_roll)
            
            # Send join message
            channel = self.bot.get_channel(channel_id)
            if channel:
                await channel.send(f"🎲 {character_name} joins combat with initiative {initiative_roll}{roll_text}!")
            
            return initiative_roll
    
    async def start_combat_with_announcement(self, channel_id: int):
        """Start combat and announce it"""
        combat_manager = self.get_combat_manager(channel_id)
        
        if hasattr(combat_manager, 'start_combat'):
            combat_manager.start_combat()
            
            channel = self.bot.get_channel(channel_id)
            if channel:
                await channel.send("⚔️ **COMBAT BEGINS!** ⚔️\nRoll for initiative!")
                
            # Queue display update
            await self.display_manager.queue_update(channel_id, combat_manager)
            return True
        return False
    
    async def end_combat(self, channel_id: int):
        """End combat in channel"""
        if channel_id in self.combat_managers:
            combat_manager = self.combat_managers[channel_id]
            result = combat_manager.end_combat()
            await self.display_manager.end_combat(channel_id)
            del self.combat_managers[channel_id]
            return result
        return None

# Global combat integration instance
combat_integration: Optional[CombatIntegration] = None

async def initialize_combat_system(bot, campaign_context):
    """Initialize combat system"""
    global combat_integration
    combat_integration = CombatIntegration(bot, campaign_context)
    await combat_integration.initialize()

def get_combat_integration() -> Optional[CombatIntegration]:
    """Get combat integration instance"""
    return combat_integration