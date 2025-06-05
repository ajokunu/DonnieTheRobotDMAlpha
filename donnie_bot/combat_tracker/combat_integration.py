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
        
        # Get minimal combat context
        combat_context = combat_manager.get_minimal_context()
        
        # Use existing fast response system with combat context
        dm_response = await self._get_fast_response_with_context(
            user_id, player_input, combat_context
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
            
            # Build prompt with combat context
            base_prompt = f"""Donnie DM responds to {character_name}: {player_input}
Storm King's Thunder. {combat_context}
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
            
        except Exception as e:
            print(f"❌ Background combat processing error: {e}")
    
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