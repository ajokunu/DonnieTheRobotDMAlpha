# combat_integration.py
"""
DM Donnie Combat Integration Module (REWRITTEN)
Connects combat system to main bot WITHOUT narrative interference
REMOVED: Combat context override, enhanced combat context injection
KEPT: Combat tracking, displays, turn management, all useful features
"""

import asyncio
from typing import Dict, Optional, Tuple
from .combat_manager import CombatManager
from .combat_display import CombatDisplayManager

class CombatIntegration:
    """Manages combat for DM Donnie WITHOUT narrative interference"""
    
    def __init__(self, bot, campaign_context):
        self.bot = bot
        self.campaign_context = campaign_context
        self.display_manager = CombatDisplayManager(bot)
        self.combat_managers: Dict[int, CombatManager] = {}
        
    async def initialize(self):
        """Initialize combat system"""
        await self.display_manager.start()
        print("✅ DM Donnie combat system initialized (NO NARRATIVE INTERFERENCE)")
    
    def get_combat_manager(self, channel_id: int) -> CombatManager:
        """Get or create combat manager for channel"""
        if channel_id not in self.combat_managers:
            self.combat_managers[channel_id] = CombatManager(channel_id)
        return self.combat_managers[channel_id]
    
    async def process_action_with_combat(self, user_id: str, player_input: str, 
                                       channel_id: int) -> Tuple[str, Optional[str]]:
        """Process action with combat awareness - NO CONTEXT OVERRIDE"""
        combat_manager = self.get_combat_manager(channel_id)
        
        # REMOVED: Combat context override that was interfering with narrative
        # OLD PROBLEMATIC CODE:
        # combat_context = None
        # if combat_manager.is_combat_active():
        #     combat_context = self._get_enhanced_combat_context(combat_manager)
        # dm_response = await self._get_fast_response_with_context(
        #     user_id, player_input, combat_context or ""
        # )
        
        # NEW: Let the main response system handle everything without interference
        try:
            # Import and use the main response function directly
            from main import get_enhanced_claude_dm_response
            dm_response = await get_enhanced_claude_dm_response(user_id, player_input)
        except ImportError:
            # Fallback to streamlined version if enhanced not available
            try:
                from main import get_streamlined_claude_response
                dm_response = await get_streamlined_claude_response(user_id, player_input)
            except ImportError:
                # Last resort fallback
                dm_response = "Donnie considers the situation carefully..."
        
        # Process combat state in background (tracking only, no narrative changes)
        asyncio.create_task(self._update_combat_background(
            combat_manager, player_input, dm_response, channel_id
        ))
        
        # Return response WITHOUT combat context override
        return dm_response, None
    
    # REMOVED: def _get_enhanced_combat_context(self, combat_manager: CombatManager) -> str:
    # This method was overriding the main scene context with combat-specific context,
    # causing narrative inconsistencies like inn → fortress jumps and inappropriate enemies
    
    # REMOVED: async def _get_fast_response_with_context(self, user_id: str, player_input: str, combat_context: str) -> str:
    # This method was injecting combat context that conflicted with scene constraints,
    # leading to giants appearing in village inns and other narrative problems
    
    async def _update_combat_background(self, combat_manager: CombatManager, 
                                      player_input: str, dm_response: str, 
                                      channel_id: int):
        """Update combat state in background - TRACKING ONLY, NO NARRATIVE CHANGES"""
        try:
            await asyncio.sleep(0.1)  # Ensure response sent first
            
            # Parse DM response for combat info (no auto scene/enemy generation)
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
    
    async def add_enemy_to_combat(self, channel_id: int, enemy_name: str, 
                                initiative: int, hp: int = None):
        """Manually add enemy to combat (replaces auto-generation)"""
        combat_manager = self.get_combat_manager(channel_id)
        
        # Use the manual enemy addition method from cleaned combat manager
        if hasattr(combat_manager, 'add_enemy_manually'):
            combat_manager.add_enemy_manually(enemy_name, initiative, hp)
        else:
            # Fallback for older combat manager
            combat_manager.add_player(f"enemy_{enemy_name}", enemy_name, initiative)
        
        # Queue display update
        await self.display_manager.queue_update(channel_id, combat_manager)
        
        # Send notification
        channel = self.bot.get_channel(channel_id)
        if channel:
            hp_text = f" ({hp} HP)" if hp else ""
            await channel.send(f"⚔️ {enemy_name} enters combat with initiative {initiative}{hp_text}!")
    
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
    
    async def advance_turn(self, channel_id: int):
        """Manually advance to next turn"""
        combat_manager = self.get_combat_manager(channel_id)
        if combat_manager.is_combat_active():
            combat_manager.advance_turn()
            await self.display_manager.queue_update(channel_id, combat_manager)
            
            # Announce new turn
            await self._check_and_announce_turn(channel_id, combat_manager)
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
    
    def get_combat_status(self, channel_id: int) -> Optional[str]:
        """Get current combat status for channel"""
        if channel_id in self.combat_managers:
            combat_manager = self.combat_managers[channel_id]
            if combat_manager.is_combat_active():
                return combat_manager.get_minimal_context()
        return None
    
    def is_combat_active(self, channel_id: int) -> bool:
        """Check if combat is active in channel"""
        if channel_id in self.combat_managers:
            return self.combat_managers[channel_id].is_combat_active()
        return False

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