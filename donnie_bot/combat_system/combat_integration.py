"""
DM Donnie Combat Integration Module (FIXED)
FIXED: Combat manager creation, player addition, error handling, async operations
KEPT: All useful features without narrative interference
"""

import asyncio
from typing import Dict, Optional, Tuple
from .combat_manager import CombatManager, CombatPhase
from .combat_display import CombatDisplayManager

class CombatIntegration:
    """FIXED: Combat integration with comprehensive error handling"""
    
    def __init__(self, bot, campaign_context):
        self.bot = bot
        self.campaign_context = campaign_context
        self.display_manager = CombatDisplayManager(bot)
        self.combat_managers: Dict[int, CombatManager] = {}
        
        print("✅ Combat Integration initialized (NO NARRATIVE INTERFERENCE)")
    
    async def initialize(self):
        """Initialize combat system"""
        try:
            await self.display_manager.start()
            print("✅ Combat integration system initialized successfully")
        except Exception as e:
            print(f"❌ Combat integration initialization failed: {e}")
    
    def get_combat_manager(self, channel_id: int) -> CombatManager:
        """FIXED: Get or create combat manager for channel with validation"""
        try:
            # Ensure channel_id is int
            if not isinstance(channel_id, int):
                channel_id = int(channel_id)
            
            if channel_id not in self.combat_managers:
                print(f"🔄 Creating new combat manager for channel {channel_id}")
                self.combat_managers[channel_id] = CombatManager(channel_id)
            
            return self.combat_managers[channel_id]
            
        except Exception as e:
            print(f"❌ Error getting combat manager for channel {channel_id}: {e}")
            # Create a fallback manager
            self.combat_managers[channel_id] = CombatManager(channel_id)
            return self.combat_managers[channel_id]
    
    def add_player_to_combat(self, channel_id: int, user_id: str, initiative: int) -> bool:
        """FIXED: Add player to combat with comprehensive validation"""
        try:
            print(f"🎯 Adding player {user_id} to combat in channel {channel_id} with initiative {initiative}")
            
            # Validate inputs
            if not isinstance(channel_id, int):
                channel_id = int(channel_id)
            
            if not isinstance(user_id, str):
                user_id = str(user_id)
            
            if not isinstance(initiative, int):
                initiative = int(initiative)
            
            # Check if user exists in campaign
            if user_id not in self.campaign_context.get("players", {}):
                print(f"❌ User {user_id} not found in campaign context")
                return False
            
            # Get character data
            player_data = self.campaign_context["players"][user_id]
            char_data = player_data.get("character_data")
            
            if not char_data:
                print(f"❌ No character data found for user {user_id}")
                return False
            
            character_name = char_data.get("name")
            if not character_name:
                print(f"❌ No character name found for user {user_id}")
                return False
            
            # Get combat manager
            combat_manager = self.get_combat_manager(channel_id)
            
            # Add player to combat
            success = combat_manager.add_player(user_id, character_name, initiative)
            
            if success:
                print(f"✅ Successfully added {character_name} to combat")
                
                # Queue display update
                try:
                    asyncio.create_task(
                        self.display_manager.queue_update(channel_id, combat_manager)
                    )
                    print(f"✅ Combat display update queued for channel {channel_id}")
                except Exception as e:
                    print(f"⚠️ Display update failed: {e}")
                
                return True
            else:
                print(f"❌ Failed to add {character_name} to combat manager")
                return False
            
        except Exception as e:
            print(f"❌ Critical error in add_player_to_combat: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    async def quick_join_combat(self, channel_id: int, user_id: str, initiative_roll: int = None) -> Optional[int]:
        """FIXED: Quick initiative roll and join combat"""
        try:
            if user_id not in self.campaign_context.get("players", {}):
                print(f"❌ User {user_id} not in campaign for quick join")
                return None
            
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
            success = self.add_player_to_combat(channel_id, user_id, initiative_roll)
            
            if success:
                # Send join message
                channel = self.bot.get_channel(channel_id)
                if channel:
                    await channel.send(f"🎲 {character_name} joins combat with initiative {initiative_roll}{roll_text}!")
                
                return initiative_roll
            else:
                print(f"❌ Quick join failed for {character_name}")
                return None
                
        except Exception as e:
            print(f"❌ Error in quick_join_combat: {e}")
            return None
    
    async def add_enemy_to_combat(self, channel_id: int, enemy_name: str, 
                                initiative: int, hp: int = None) -> bool:
        """FIXED: Add enemy to combat with validation"""
        try:
            print(f"🎯 Adding enemy {enemy_name} to combat in channel {channel_id}")
            
            # Validate inputs
            if not isinstance(channel_id, int):
                channel_id = int(channel_id)
            
            if not enemy_name or not isinstance(enemy_name, str):
                print(f"❌ Invalid enemy name: {enemy_name}")
                return False
            
            if not isinstance(initiative, int):
                initiative = int(initiative)
            
            if hp is not None and not isinstance(hp, int):
                try:
                    hp = int(hp)
                except (ValueError, TypeError):
                    hp = None
            
            combat_manager = self.get_combat_manager(channel_id)
            
            # Add enemy using the manual method
            success = combat_manager.add_enemy_manually(enemy_name, initiative, hp)
            
            if success:
                # Queue display update
                try:
                    await self.display_manager.queue_update(channel_id, combat_manager)
                    print(f"✅ Enemy {enemy_name} added and display updated")
                except Exception as e:
                    print(f"⚠️ Display update failed after adding enemy: {e}")
                
                # Send notification
                try:
                    channel = self.bot.get_channel(channel_id)
                    if channel:
                        hp_text = f" ({hp} HP)" if hp else ""
                        await channel.send(f"⚔️ {enemy_name} enters combat with initiative {initiative}{hp_text}!")
                except Exception as e:
                    print(f"⚠️ Notification send failed: {e}")
                
                return True
            else:
                print(f"❌ Failed to add enemy {enemy_name} to combat manager")
                return False
                
        except Exception as e:
            print(f"❌ Critical error in add_enemy_to_combat: {e}")
            return False
    
    async def start_combat_with_announcement(self, channel_id: int) -> bool:
        """FIXED: Start combat and announce it"""
        try:
            combat_manager = self.get_combat_manager(channel_id)
            
            success = combat_manager.start_combat()
            
            if success:
                try:
                    channel = self.bot.get_channel(channel_id)
                    if channel:
                        await channel.send("⚔️ **COMBAT BEGINS!** ⚔️\nUse `/initiative <roll>` to join!")
                except Exception as e:
                    print(f"⚠️ Combat start announcement failed: {e}")
                
                # Queue display update
                try:
                    await self.display_manager.queue_update(channel_id, combat_manager)
                    print(f"✅ Combat started and display updated for channel {channel_id}")
                except Exception as e:
                    print(f"⚠️ Display update failed after combat start: {e}")
                
                return True
            else:
                print(f"❌ Failed to start combat in channel {channel_id}")
                return False
                
        except Exception as e:
            print(f"❌ Error in start_combat_with_announcement: {e}")
            return False
    
    async def advance_turn(self, channel_id: int) -> bool:
        """FIXED: Manually advance to next turn"""
        try:
            combat_manager = self.get_combat_manager(channel_id)
            
            if not combat_manager.is_combat_active():
                print(f"⚠️ Cannot advance turn: no active combat in channel {channel_id}")
                return False
            
            success = combat_manager.advance_turn()
            
            if success:
                try:
                    await self.display_manager.queue_update(channel_id, combat_manager)
                    print(f"✅ Turn advanced and display updated for channel {channel_id}")
                except Exception as e:
                    print(f"⚠️ Display update failed after turn advance: {e}")
                
                # Announce new turn
                try:
                    await self._check_and_announce_turn(channel_id, combat_manager)
                except Exception as e:
                    print(f"⚠️ Turn announcement failed: {e}")
                
                return True
            else:
                print(f"❌ Failed to advance turn in channel {channel_id}")
                return False
                
        except Exception as e:
            print(f"❌ Error in advance_turn: {e}")
            return False
    
    async def end_combat(self, channel_id: int) -> Optional[Dict]:
        """FIXED: End combat in channel"""
        try:
            if channel_id not in self.combat_managers:
                print(f"⚠️ No combat manager found for channel {channel_id}")
                return None
            
            combat_manager = self.combat_managers[channel_id]
            result = combat_manager.end_combat()
            
            if result:
                try:
                    await self.display_manager.end_combat(channel_id)
                    print(f"✅ Combat ended and display cleared for channel {channel_id}")
                except Exception as e:
                    print(f"⚠️ Display cleanup failed: {e}")
                
                # Clean up combat manager
                del self.combat_managers[channel_id]
                
                return result
            else:
                print(f"⚠️ No active combat to end in channel {channel_id}")
                return None
                
        except Exception as e:
            print(f"❌ Error in end_combat: {e}")
            return None
    
    def get_combat_status(self, channel_id: int) -> Optional[str]:
        """Get current combat status for channel"""
        try:
            if channel_id in self.combat_managers:
                combat_manager = self.combat_managers[channel_id]
                if combat_manager.is_combat_active():
                    return combat_manager.get_minimal_context()
            return None
            
        except Exception as e:
            print(f"❌ Error getting combat status: {e}")
            return None
    
    def is_combat_active(self, channel_id: int) -> bool:
        """Check if combat is active in channel"""
        try:
            if channel_id in self.combat_managers:
                return self.combat_managers[channel_id].is_combat_active()
            return False
            
        except Exception as e:
            print(f"❌ Error checking if combat active: {e}")
            return False
    
    async def _check_and_announce_turn(self, channel_id: int, combat_manager: CombatManager):
        """FIXED: Check for turn changes and announce next player"""
        try:
            current = combat_manager.get_current_combatant()
            round_num = combat_manager.get_round_number()
            
            if current:
                # Check if we need to announce this turn
                turn_key = f"{round_num}_{current.name}"
                
                # Simple turn announcement tracking
                if not hasattr(combat_manager, 'last_announced_turn'):
                    combat_manager.last_announced_turn = None
                
                if combat_manager.last_announced_turn != turn_key:
                    combat_manager.last_announced_turn = turn_key
                    
                    channel = self.bot.get_channel(channel_id)
                    if channel:
                        # Get status effects for current player
                        status_text = self._get_status_reminder(combat_manager, current.name)
                        status_part = f" {status_text}" if status_text else ""
                        
                        await channel.send(f"🎯 **Round {round_num}** - It's {current.name}'s turn!{status_part}")
                        print(f"✅ Turn announced: {current.name} in round {round_num}")
                        
        except Exception as e:
            print(f"❌ Turn announcement error: {e}")
    
    def _get_status_reminder(self, combat_manager: CombatManager, character_name: str) -> str:
        """Get status effect reminders for character"""
        try:
            status_effects = combat_manager.get_character_status(character_name)
            if status_effects:
                return f"({', '.join(status_effects)})"
            return ""
            
        except Exception as e:
            print(f"❌ Error getting status reminder: {e}")
            return ""
    
    def get_integration_status(self) -> Dict:
        """Get comprehensive integration status for debugging"""
        try:
            return {
                "combat_managers_count": len(self.combat_managers),
                "active_combats": sum(1 for cm in self.combat_managers.values() if cm.is_active()),
                "display_manager_active": bool(self.display_manager),
                "channels_with_combat": list(self.combat_managers.keys()),
                "bot_connected": bool(self.bot and hasattr(self.bot, 'user')),
                "campaign_context_available": bool(self.campaign_context)
            }
            
        except Exception as e:
            return {"error": str(e)}

# Global combat integration instance - FIXED initialization
combat_integration: Optional[CombatIntegration] = None

async def initialize_combat_system(bot, campaign_context):
    """FIXED: Initialize combat system with comprehensive error handling"""
    global combat_integration
    
    try:
        print("🔄 Initializing combat system...")
        
        # Validate inputs
        if not bot:
            raise ValueError("Bot instance is required")
        
        if not campaign_context:
            raise ValueError("Campaign context is required")
        
        # Create combat integration
        combat_integration = CombatIntegration(bot, campaign_context)
        
        # Initialize the combat integration
        await combat_integration.initialize()
        
        print("✅ Combat system initialized successfully")
        
        # Test the system
        status = combat_integration.get_integration_status()
        print(f"🔍 Combat system status: {status}")
        
        return combat_integration
        
    except Exception as e:
        print(f"❌ Combat system initialization failed: {e}")
        import traceback
        traceback.print_exc()
        
        # Set to None on failure
        combat_integration = None
        raise e

def get_combat_integration() -> Optional[CombatIntegration]:
    """FIXED: Get combat integration instance with validation"""
    try:
        if combat_integration is None:
            print("⚠️ Combat integration not initialized")
            return None
        
        # Validate the integration is still working
        if not hasattr(combat_integration, 'bot') or not combat_integration.bot:
            print("⚠️ Combat integration has invalid bot reference")
            return None
        
        return combat_integration
        
    except Exception as e:
        print(f"❌ Error getting combat integration: {e}")
        return None