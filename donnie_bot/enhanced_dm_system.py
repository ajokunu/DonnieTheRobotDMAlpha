# donnie_bot/enhanced_dm_system.py
"""
Enhanced DM System with Persistent Memory
Provides memory-aware DM responses with contextual understanding
"""

import asyncio
from typing import Dict, List, Optional, Any
from datetime import datetime
import random

class PersistentDMSystem:
    """Enhanced DM system with persistent memory integration"""
    
    def __init__(self, claude_client, campaign_context: Dict):
        self.claude_client = claude_client
        self.campaign_context = campaign_context
        
        # Initialize memory operations
        try:
            from database.memory_operations import AdvancedMemoryOperations
            self.memory_ops = AdvancedMemoryOperations(claude_client)
            self.memory_available = True
            print("✅ Memory operations initialized")
        except ImportError:
            self.memory_ops = None
            self.memory_available = False
            print("⚠️ Memory operations not available")
    
    async def get_enhanced_dm_response(self, user_id: str, player_input: str, 
                                     guild_id: str, episode_id: int) -> str:
        """Get DM response with enhanced memory context"""
        
        try:
            # Get character information
            player_data = self.campaign_context["players"][user_id]
            char_data = player_data["character_data"]
            character_name = char_data["name"]
            
            # Build context with memory
            context = await self._build_memory_context(guild_id, player_input, character_name)
            
            # Generate response with context
            dm_response = await self._generate_contextual_response(
                character_name, player_input, context
            )
            
            # Store this interaction in memory
            if self.memory_available:
                await self.memory_ops.store_conversation_memory(
                    campaign_id=guild_id,
                    episode_id=episode_id,
                    user_id=user_id,
                    character_name=character_name,
                    player_input=player_input,
                    dm_response=dm_response
                )
            
            # Update session history
            self.campaign_context["session_history"].append({
                "player": f"{character_name} ({player_data['player_name']})",
                "action": player_input,
                "dm_response": dm_response
            })
            
            # Keep only last 10 entries for performance
            if len(self.campaign_context["session_history"]) > 10:
                self.campaign_context["session_history"] = self.campaign_context["session_history"][-10:]
            
            return dm_response
            
        except Exception as e:
            print(f"❌ Enhanced DM response error: {e}")
            import traceback
            traceback.print_exc()
            
            # Fallback to basic response
            return await self._generate_fallback_response(user_id, player_input)
    
    async def end_episode_consolidation(self, campaign_id: str, episode_id: int) -> Optional[Dict[str, Any]]:
        """Consolidate memories at episode end"""
        
        if not self.memory_available:
            print("⚠️ Memory consolidation skipped - memory operations not available")
            return None
        
        try:
            consolidation = await self.memory_ops.consolidate_episode_memories(campaign_id, episode_id)
            
            if consolidation:
                print(f"✅ Episode {episode_id} memories consolidated successfully")
                return consolidation
            else:
                print(f"⚠️ No memories to consolidate for episode {episode_id}")
                return None
                
        except Exception as e:
            print(f"❌ Episode consolidation failed: {e}")
            return None
    
    async def _build_memory_context(self, campaign_id: str, player_input: str, character_name: str) -> Dict[str, Any]:
        """Build context from memory for the current situation"""
        
        context = {
            "relevant_memories": [],
            "active_npcs": [],
            "current_scene": self.campaign_context.get("current_scene", ""),
            "recent_events": [],
            "character_context": ""
        }
        
        if not self.memory_available:
            return context
        
        try:
            # Get relevant memories
            memories = await self.memory_ops.retrieve_relevant_memories(
                campaign_id, player_input, max_memories=5, min_importance=0.4
            )
            
            context["relevant_memories"] = [
                {
                    "character": mem.character_name,
                    "summary": mem.summary,
                    "importance": mem.importance_score,
                    "context": mem.scene_context
                }
                for mem in memories
            ]
            
            # Get important NPCs
            npcs = await self.memory_ops.get_campaign_npcs(campaign_id, "important")
            npcs.extend(await self.memory_ops.get_campaign_npcs(campaign_id, "major"))
            
            context["active_npcs"] = [
                {
                    "name": npc.name,
                    "personality": npc.personality_summary,
                    "relationship": npc.relationship_with_party,
                    "location": npc.current_location,
                    "status": npc.status
                }
                for npc in npcs[:5]  # Limit to top 5 NPCs
            ]
            
            # Add recent session history
            context["recent_events"] = [
                f"{entry['player']}: {entry['action']}"
                for entry in self.campaign_context.get("session_history", [])[-3:]
            ]
            
            return context
            
        except Exception as e:
            print(f"⚠️ Error building memory context: {e}")
            return context
    
    async def _generate_contextual_response(self, character_name: str, player_input: str, 
                                          context: Dict[str, Any]) -> str:
        """Generate DM response with memory context"""
        
        # Build the enhanced prompt with memory context
        enhanced_prompt = self._build_enhanced_prompt(character_name, player_input, context)
        
        try:
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self.claude_client.messages.create(
                    model="claude-sonnet-4-20250514",
                    max_tokens=300,  # Slightly increased for contextual responses
                    messages=[{"role": "user", "content": enhanced_prompt}]
                )
            )
            
            dm_response = ""
            if hasattr(response.content[0], 'text'):
                dm_response = response.content[0].text.strip()
            else:
                dm_response = str(response.content[0]).strip()
            
            # Ensure response is reasonable length
            if len(dm_response) > 800:
                dm_response = dm_response[:797] + "..."
            
            return dm_response
            
        except Exception as e:
            print(f"❌ Contextual response generation error: {e}")
            return await self._generate_fallback_response("", player_input)
    
    def _build_enhanced_prompt(self, character_name: str, player_input: str, 
                             context: Dict[str, Any]) -> str:
        """Build enhanced prompt with memory context"""
        
        # Base Storm King's Thunder context
        base_context = f"""You are Donnie, DM for Storm King's Thunder D&D 5e 2024.

SETTING: {self.campaign_context.get('setting', 'The Sword Coast during the giant crisis')}
CURRENT SCENE: {context.get('current_scene', 'Adventure in progress')}"""
        
        # Add party information
        party_info = []
        for user_id, player_data in self.campaign_context.get("players", {}).items():
            char_data = player_data["character_data"]
            party_info.append(f"{char_data['name']} (Lvl {char_data['level']} {char_data['race']} {char_data['class']})")
        
        if party_info:
            base_context += f"\nPARTY: {', '.join(party_info)}"
        
        # Add memory context
        memory_context = ""
        
        # Recent events
        recent_events = context.get("recent_events", [])
        if recent_events:
            memory_context += f"\n\nRECENT EVENTS:\n" + "\n".join(recent_events)
        
        # Relevant memories
        relevant_memories = context.get("relevant_memories", [])
        if relevant_memories:
            memory_context += f"\n\nRELEVANT PAST EVENTS:"
            for memory in relevant_memories:
                memory_context += f"\n- {memory['character']}: {memory['summary']} (Importance: {memory['importance']:.1f})"
        
        # Active NPCs
        active_npcs = context.get("active_npcs", [])
        if active_npcs:
            memory_context += f"\n\nKNOWN NPCs:"
            for npc in active_npcs:
                npc_desc = f"\n- {npc['name']}: {npc['personality']}"
                if npc['relationship']:
                    npc_desc += f" (Relationship: {npc['relationship']})"
                if npc['location']:
                    npc_desc += f" (Location: {npc['location']})"
                memory_context += npc_desc
        
        # Combat context if active
        combat_context = ""
        if self.campaign_context.get("combat_active"):
            # Import combat state from main
            try:
                from main import combat_state
                if combat_state["active"]:
                    combat_context = f"\n\nCOMBAT ACTIVE - Round {combat_state['round']}"
                    if combat_state["initiative_order"]:
                        current_turn = combat_state["initiative_order"][combat_state["current_turn_index"]][0]
                        combat_context += f" - {current_turn}'s turn"
            except ImportError:
                pass
        
        # Build final prompt
        enhanced_prompt = f"""{base_context}{memory_context}{combat_context}

**MEMORY-AWARE RESPONSE GUIDELINES:**
- Reference relevant past events naturally when appropriate
- Maintain NPC personality consistency based on their known traits
- Build on previous player choices and their consequences
- Keep responses under 700 characters for gameplay flow
- React to the current action while maintaining campaign continuity

CURRENT PLAYER ACTION: {character_name}: {player_input}

Respond as Donnie with enhanced memory and campaign continuity:"""
        
        return enhanced_prompt
    
    async def _generate_fallback_response(self, user_id: str, player_input: str) -> str:
        """Fallback response generation without memory"""
        
        # Simple fallback prompt
        fallback_prompt = f"""You are Donnie, DM for Storm King's Thunder D&D 5e 2024.

The giants threaten the Sword Coast. The ancient ordning has collapsed.

PLAYER ACTION: {player_input}

Respond as the DM (under 700 characters):"""
        
        try:
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self.claude_client.messages.create(
                    model="claude-sonnet-4-20250514",
                    max_tokens=200,
                    messages=[{"role": "user", "content": fallback_prompt}]
                )
            )
            
            dm_response = ""
            if hasattr(response.content[0], 'text'):
                dm_response = response.content[0].text.strip()
            else:
                dm_response = str(response.content[0]).strip()
            
            if len(dm_response) > 700:
                dm_response = dm_response[:697] + "..."
            
            return dm_response
            
        except Exception as e:
            print(f"❌ Fallback response error: {e}")
            return f"Donnie pauses thoughtfully... *The adventure continues, but Donnie seems momentarily distracted by the complexities of the giant crisis.*"

# Convenience function for main.py integration
async def get_persistent_dm_response(claude_client, campaign_context: Dict, 
                                   user_id: str, player_input: str, 
                                   guild_id: str, episode_id: int) -> str:
    """Convenience function for main.py integration"""
    
    dm_system = PersistentDMSystem(claude_client, campaign_context)
    return await dm_system.get_enhanced_dm_response(user_id, player_input, guild_id, episode_id)