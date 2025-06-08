# structured_memory.py - SAFE VERSION
import asyncio
from typing import Dict, List, Optional, Any

class StructuredMemoryBuilder:
    """Prevents AI hallucination by providing only verified, structured context"""
    
    def __init__(self, memory_ops, campaign_context):
        self.memory_ops = memory_ops
        self.campaign_context = campaign_context
        
        # Import validator safely
        try:
            from memory_validator import MemoryValidator
            self.validator = MemoryValidator()
            print("✅ Memory validator loaded")
        except ImportError:
            print("⚠️ Memory validator not available, using basic validation")
            self.validator = None
    
    async def build_reliable_context(self, guild_id: str, player_input: str, 
                                   character_name: str, channel_id: Optional[int] = None) -> Dict[str, Any]:
        """Build context that prevents hallucination - SAFE VERSION"""
        
        context = {
            "recent_events": [],
            "character_memories": [],
            "combat_state": "No active combat",
            "current_scene": self.campaign_context.get("current_scene", ""),
            "npc_info": [],
            "party_status": self._get_party_status(),
            "rules_authority": True,  # AI can use D&D rules
            "skt_content_authority": True  # AI can use Storm King's Thunder content
        }
        
        # SAFE: Get recent session events
        try:
            recent_events = self.campaign_context.get("session_history", [])[-5:]
            context["recent_events"] = [
                f"SESSION EVENT: {e.get('player', 'Unknown')}: {e.get('action', '')}" 
                for e in recent_events if e.get('action')
            ]
            print(f"✅ Found {len(context['recent_events'])} recent events")
        except Exception as e:
            print(f"⚠️ Error getting recent events: {e}")
            context["recent_events"] = []
        
        # SAFE: Get memories only if memory_ops available
        if self.memory_ops:
            try:
                memories = await asyncio.wait_for(
                    self.memory_ops.retrieve_relevant_memories(
                        campaign_id=guild_id,
                        query=f"{character_name} {player_input}",
                        max_memories=3,
                        min_importance=0.6
                    ),
                    timeout=3.0
                )
                
                # SAFE: Filter memories if validator available
                if self.validator:
                    memories = self.validator.filter_reliable_memories(memories)
                
                context["character_memories"] = [
                    f"CAMPAIGN MEMORY: {getattr(m, 'summary', str(m)[:100])}" 
                    for m in memories[:3]
                ]
                print(f"✅ Found {len(context['character_memories'])} campaign memories")
                
            except asyncio.TimeoutError:
                print("⚠️ Memory retrieval timeout")
                context["character_memories"] = []
            except Exception as e:
                print(f"⚠️ Error retrieving memories: {e}")
                context["character_memories"] = []
        else:
            print("⚠️ Memory operations not available")
            context["character_memories"] = []
        
        # SAFE: Get combat state if channel_id provided
        if channel_id is not None:
            context["combat_state"] = self._get_combat_context(channel_id)
        
        return context
    
    def _get_party_status(self) -> str:
        """SAFE: Get current party status"""
        try:
            party_info = []
            for user_id, player_data in self.campaign_context.get("players", {}).items():
                char_data = player_data.get("character_data", {})
                name = char_data.get("name", "Unknown")
                level = char_data.get("level", 1)
                race = char_data.get("race", "Unknown")
                char_class = char_data.get("class", "Unknown")
                party_info.append(f"{name} (Lvl {level} {race} {char_class})")
            
            return ", ".join(party_info) if party_info else "No party registered"
        except Exception as e:
            print(f"⚠️ Error getting party status: {e}")
            return "Party status unknown"
    
    def _get_combat_context(self, channel_id: int) -> str:
        """SAFE: Get combat context with error handling"""
        try:
            # SAFE: Try to import combat system
            from combat_system.combat_integration import get_combat_integration
            combat = get_combat_integration()
            
            if not combat:
                return "No combat system available"
            
            if not combat.is_combat_active(channel_id):
                return "No active combat"
            
            status = combat.get_combat_status(channel_id)
            return f"COMBAT ACTIVE: {status[:100]}" if status else "Combat active, no details"
                
        except ImportError:
            print("⚠️ Combat system not available")
            return "Combat system not available"
        except Exception as e:
            print(f"⚠️ Error getting combat context: {e}")
            return "Combat state unknown"