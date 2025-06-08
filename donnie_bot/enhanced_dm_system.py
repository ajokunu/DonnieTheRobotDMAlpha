# enhanced_dm_system.py - COMPLETE FILE (Updated for Unified System)
"""
Enhanced DM System with Persistent Memory - MEMORY OPERATIONS ONLY
Provides memory management and context building for the Unified Response System

This file now focuses purely on memory operations and does NOT generate responses.
All response generation is handled by unified_dm_response.py
"""

import asyncio
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
import random
import time

class EnhancedMemoryManager:
    """
    Enhanced memory management for Storm King's Thunder campaign
    
    Handles:
    - Memory context building for responses
    - Conversation memory storage and retrieval
    - NPC tracking and relationship management
    - World state management
    - Episode memory consolidation
    
    Does NOT handle response generation (that's unified_dm_response.py's job)
    """
    
    def __init__(self, claude_client, campaign_context: Dict, database_operations=None):
        self.claude_client = claude_client
        self.campaign_context = campaign_context
        self.database_operations = database_operations
        
        # Memory system availability
        self.memory_available = False
        if database_operations:
            try:
                # Check if we have the required database operations
                required_methods = ['store_conversation_memory', 'retrieve_relevant_memories']
                if all(hasattr(database_operations, method) for method in required_methods):
                    self.memory_ops = database_operations
                    self.memory_available = True
                    print("✅ Enhanced memory operations initialized with database")
                else:
                    print("⚠️ Database operations missing required memory methods")
                    self.memory_ops = MockMemoryOperations()
                    self.memory_available = False
            except Exception as e:
                print(f"⚠️ Memory operations initialization failed: {e}")
                self.memory_ops = MockMemoryOperations()
                self.memory_available = False
        else:
            print("⚠️ No database operations provided")
            self.memory_ops = MockMemoryOperations()
            self.memory_available = False
        
        # Storm King's Thunder specific memory categories
        self.memory_categories = {
            "giant_encounters": ["cloud giant", "fire giant", "frost giant", "hill giant", "stone giant", "storm giant"],
            "important_npcs": ["zephyros", "harshnag", "serissa", "zalto", "imryth", "felgolos"],
            "key_locations": ["nightstone", "triboar", "waterdeep", "neverwinter", "bryn shander", "ironslag"],
            "plot_threads": ["ordning", "giant lords", "ancient artifacts", "draconic involvement"],
            "factions": ["harpers", "emerald enclave", "lords alliance", "order of the gauntlet", "zhentarim"]
        }
        
        print(f"🧠 Enhanced Memory Manager initialized (Memory: {'✅' if self.memory_available else 'Legacy Code Active but not broken'})")
    
    async def build_memory_context(self, campaign_id: str, player_input: str, 
                                 character_name: str, max_memories: int = 3) -> Dict[str, Any]:
        """
        Build comprehensive memory context for response generation
        
        This is the main interface used by unified_dm_response.py
        """
        
        context = {
            "relevant_memories": [],
            "active_npcs": [],
            "current_scene": self.campaign_context.get("current_scene", ""),
            "recent_events": [],
            "character_context": "",
            "world_state": {},
            "plot_threads": []
        }
        
        if not self.memory_available:
            # Build context from campaign_context session history
            recent_history = self.campaign_context.get("session_history", [])[-3:]
            context["recent_events"] = [
                f"{entry.get('player', 'Unknown')}: {entry.get('action', '')}"
                for entry in recent_history
            ]
            return context
        
        try:
            # Get relevant memories with timeout for performance
            if hasattr(self.memory_ops, 'retrieve_relevant_memories'):
                memories = await asyncio.wait_for(
                    self.memory_ops.retrieve_relevant_memories(
                        campaign_id=campaign_id,
                        query=player_input,
                        max_memories=max_memories,
                        min_importance=0.4
                    ),
                    timeout=2.0  # Fast timeout for performance
                )
                
                context["relevant_memories"] = [
                    {
                        "character": getattr(mem, 'character_name', 'Unknown'),
                        "summary": getattr(mem, 'summary', str(mem)[:100]),
                        "importance": getattr(mem, 'importance_score', 0.5),
                        "scene_context": getattr(mem, 'scene_context', '')
                    }
                    for mem in memories[:max_memories]
                ]
                
                print(f"🧠 Retrieved {len(context['relevant_memories'])} relevant memories")
            
            # Get important NPCs
            if hasattr(self.memory_ops, 'get_campaign_npcs'):
                npcs = await asyncio.wait_for(
                    self.memory_ops.get_campaign_npcs(campaign_id, "important"),
                    timeout=1.0
                )
                
                context["active_npcs"] = [
                    {
                        "name": getattr(npc, 'name', 'Unknown NPC'),
                        "personality": getattr(npc, 'personality_summary', 'Mysterious'),
                        "relationship": getattr(npc, 'relationship_with_party', 'Unknown'),
                        "location": getattr(npc, 'current_location', 'Unknown'),
                        "status": getattr(npc, 'status', 'Active')
                    }
                    for npc in npcs[:3]  # Limit to top 3 NPCs for speed
                ]
                
                print(f"🧠 Retrieved {len(context['active_npcs'])} active NPCs")
            
            # Add recent session history from campaign_context
            recent_history = self.campaign_context.get("session_history", [])[-3:]
            context["recent_events"] = [
                f"{entry.get('player', 'Unknown')}: {entry.get('action', '')}"
                for entry in recent_history
            ]
            
            # Analyze input for plot threads and important elements
            context["plot_threads"] = self._analyze_plot_threads(player_input)
            context["world_state"] = self._get_world_state_context(player_input)
            
            return context
            
        except asyncio.TimeoutError:
            print("⚠️ Memory context timeout - using session history only")
            recent_history = self.campaign_context.get("session_history", [])[-3:]
            context["recent_events"] = [
                f"{entry.get('player', 'Unknown')}: {entry.get('action', '')}"
                for entry in recent_history
            ]
            return context
        except Exception as e:
            print(f"⚠️ Error building memory context: {e}")
            return context
    
    async def store_interaction_memory(self, guild_id: str, episode_id: int, user_id: str, 
                                     player_input: str, dm_response: str) -> bool:
        """
        Store interaction in memory system (background task)
        
        Called by unified_dm_response.py after response generation
        """
        
        if not self.memory_available:
            print("⚠️ Memory system not available for storage")
            return False
        
        try:
            # Validate all parameters
            if not all([guild_id, user_id, player_input, dm_response]):
                print("❌ Missing required parameters for memory storage")
                return False
            
            if user_id not in self.campaign_context.get("players", {}):
                print(f"❌ User {user_id} not in campaign context")
                return False
            
            # Get character information
            player_data = self.campaign_context["players"][user_id]
            char_data = player_data["character_data"]
            character_name = char_data["name"]
            
            # Calculate importance score based on content
            importance_score = self._calculate_importance_score(player_input, dm_response)
            
            # Store using the memory operations interface
            success = await self.memory_ops.store_conversation_memory(
                campaign_id=guild_id,
                episode_id=episode_id,
                user_id=user_id,
                character_name=character_name,
                player_input=player_input,
                dm_response=dm_response,
                importance_score=importance_score,
                scene_context=self.campaign_context.get("current_scene", "")[:200]
            )
            
            if success:
                print(f"✅ Stored memory for {character_name} (importance: {importance_score:.2f})")
                
                # Background tasks: Update NPC memories and world state
                asyncio.create_task(self._update_related_memories(
                    guild_id, episode_id, player_input, dm_response, character_name
                ))
            else:
                print(f"⚠️ Failed to store memory for {character_name}")
            
            return success
            
        except Exception as e:
            print(f"❌ Memory storage error: {e}")
            return False
    
    async def consolidate_episode_memories(self, campaign_id: str, episode_id: int) -> Optional[Dict[str, Any]]:
        """Consolidate memories at episode end"""
        
        if not self.memory_available:
            print("⚠️ Memory consolidation skipped - memory operations not available")
            return None
        
        try:
            # Check if consolidation method exists in memory operations
            if hasattr(self.memory_ops, 'consolidate_episode_memories'):
                consolidation = await self.memory_ops.consolidate_episode_memories(campaign_id, episode_id)
                
                if consolidation:
                    print(f"✅ Episode {episode_id} memories consolidated successfully")
                    return consolidation
                else:
                    print(f"⚠️ No memories to consolidate for episode {episode_id}")
                    return None
            else:
                print("⚠️ Episode consolidation method not available in memory operations")
                # Create a basic consolidation summary
                return await self._create_basic_consolidation(campaign_id, episode_id)
                
        except Exception as e:
            print(f"❌ Episode consolidation failed: {e}")
            return None
    
    def _analyze_plot_threads(self, player_input: str) -> List[str]:
        """Analyze player input for relevant plot threads"""
        
        input_lower = player_input.lower()
        relevant_threads = []
        
        # Check for Storm King's Thunder plot elements
        for category, keywords in self.memory_categories.items():
            for keyword in keywords:
                if keyword in input_lower:
                    relevant_threads.append(f"{category}: {keyword}")
        
        # Check for general D&D plot elements
        plot_keywords = {
            "combat": ["attack", "fight", "combat", "initiative", "damage", "hit points"],
            "exploration": ["search", "investigate", "explore", "examine", "look"],
            "social": ["talk", "persuade", "intimidate", "deceive", "insight"],
            "magic": ["cast", "spell", "magic", "enchant", "summon"],
            "travel": ["go", "move", "travel", "journey", "walk", "ride"]
        }
        
        for thread_type, keywords in plot_keywords.items():
            if any(keyword in input_lower for keyword in keywords):
                relevant_threads.append(f"activity: {thread_type}")
        
        return relevant_threads[:3]  # Limit to top 3 for performance
    
    def _get_world_state_context(self, player_input: str) -> Dict[str, Any]:
        """Get relevant world state information"""
        
        world_state = {
            "giant_threat_level": "critical",
            "ordning_status": "collapsed",
            "affected_regions": ["sword coast", "northern regions", "ten towns"],
            "active_threats": []
        }
        
        input_lower = player_input.lower()
        
        # Determine which giant types might be relevant
        for giant_type in self.memory_categories["giant_encounters"]:
            if giant_type.replace(" ", "") in input_lower.replace(" ", ""):
                world_state["active_threats"].append(giant_type)
        
        # Add location-specific context
        for location in self.memory_categories["key_locations"]:
            if location in input_lower:
                world_state["current_location_context"] = location
                break
        
        return world_state
    
    def _calculate_importance_score(self, player_input: str, dm_response: str) -> float:
        """Calculate importance score for memory storage"""
        
        base_score = 0.5
        input_lower = player_input.lower()
        response_lower = dm_response.lower()
        combined_text = input_lower + " " + response_lower
        
        # High importance indicators
        high_importance_keywords = [
            "giant", "lord", "princess", "duke", "ancient", "artifact", "ordning",
            "death", "kill", "critical", "natural 20", "natural 1", "level up",
            "treasure", "magic item", "spell scroll", "important", "secret"
        ]
        
        # Medium importance indicators
        medium_importance_keywords = [
            "combat", "initiative", "damage", "healing", "spell", "ability",
            "npc", "conversation", "information", "clue", "discovery"
        ]
        
        # Low importance indicators
        low_importance_keywords = [
            "look", "search", "move", "walk", "continue", "rest", "eat"
        ]
        
        # Calculate score based on keywords
        for keyword in high_importance_keywords:
            if keyword in combined_text:
                base_score += 0.3
        
        for keyword in medium_importance_keywords:
            if keyword in combined_text:
                base_score += 0.1
        
        for keyword in low_importance_keywords:
            if keyword in combined_text:
                base_score -= 0.1
        
        # Length bonus (longer interactions often more important)
        if len(combined_text) > 200:
            base_score += 0.1
        
        # Storm King's Thunder specific bonuses
        skt_keywords = ["storm king", "giant lord", "maelstrom", "eye of the all-father"]
        for keyword in skt_keywords:
            if keyword in combined_text:
                base_score += 0.4
        
        # Clamp between 0.1 and 1.0
        return max(0.1, min(1.0, base_score))
    
    async def _update_related_memories(self, guild_id: str, episode_id: int, 
                                     player_input: str, dm_response: str, 
                                     character_name: str):
        """Update related NPC and world state memories in background"""
        
        try:
            # Extract potential NPC names from response
            potential_npcs = self._extract_npc_names(dm_response + " " + player_input)
            
            for npc_name in potential_npcs[:2]:  # Limit to 2 NPCs for speed
                try:
                    if hasattr(self.memory_ops, 'update_npc_memory'):
                        await asyncio.wait_for(
                            self.memory_ops.update_npc_memory(
                                campaign_id=guild_id,
                                npc_name=npc_name,
                                episode_id=episode_id,
                                updates={
                                    "last_interaction": dm_response[:80],
                                    "last_seen_episode": episode_id,
                                    "relationship_notes": f"Interacted with {character_name}"
                                }
                            ),
                            timeout=3.0
                        )
                        print(f"✅ Updated NPC memory for {npc_name}")
                    else:
                        print(f"⚠️ NPC {npc_name} detected but update_npc_memory method not available")
                except asyncio.TimeoutError:
                    print(f"⚠️ NPC update timeout for {npc_name}")
                except Exception as e:
                    print(f"⚠️ Failed to update NPC {npc_name}: {e}")
            
            # Update world state if significant events occurred
            if any(keyword in (player_input + dm_response).lower() 
                   for keyword in ["giant", "combat", "treasure", "magic item", "important"]):
                try:
                    if hasattr(self.memory_ops, 'update_world_state'):
                        await asyncio.wait_for(
                            self.memory_ops.update_world_state(
                                campaign_id=guild_id,
                                location=self.campaign_context.get("current_scene", "unknown")[:50],
                                event_summary=f"{character_name}: {player_input[:50]}...",
                                episode_id=episode_id
                            ),
                            timeout=3.0
                        )
                        print("✅ Updated world state")
                except Exception as e:
                    print(f"⚠️ Failed to update world state: {e}")
                    
        except Exception as e:
            print(f"⚠️ Related memories update failed: {e}")
    
    def _extract_npc_names(self, text: str) -> List[str]:
        """Extract potential NPC names from text"""
        
        text_lower = text.lower()
        found_npcs = []
        
        # Check for specific Storm King's Thunder NPCs
        for npc in self.memory_categories["important_npcs"]:
            if npc in text_lower:
                found_npcs.append(npc.title())
        
        # Check for common NPC types
        common_npc_types = [
            "guard", "captain", "merchant", "innkeeper", "villager", "priest",
            "mayor", "blacksmith", "tavern keeper", "shopkeeper", "wizard",
            "cleric", "fighter", "rogue", "bard", "ranger", "paladin"
        ]
        
        for npc_type in common_npc_types:
            if npc_type in text_lower and npc_type.title() not in found_npcs:
                found_npcs.append(npc_type.title())
        
        return found_npcs[:3]  # Limit to 3 for speed
    
    async def _create_basic_consolidation(self, campaign_id: str, episode_id: int) -> Dict[str, Any]:
        """Create basic episode consolidation when advanced method not available"""
        
        # Get recent session history for consolidation
        recent_history = self.campaign_context.get("session_history", [])
        
        if not recent_history:
            return {
                "campaign_id": campaign_id,
                "episode_id": episode_id,
                "consolidated_at": datetime.now().isoformat(),
                "summary": "Episode completed with no recorded interactions",
                "key_events": [],
                "npcs_encountered": [],
                "locations_visited": []
            }
        
        # Extract key information from session history
        key_events = []
        npcs_encountered = set()
        locations_mentioned = set()
        
        for entry in recent_history[-10:]:  # Last 10 interactions
            action = entry.get("action", "")
            response = entry.get("dm_response", "")
            combined = action + " " + response
            
            # Look for important events
            if any(keyword in combined.lower() for keyword in ["combat", "treasure", "important", "discovery"]):
                key_events.append({
                    "player": entry.get("player", "Unknown"),
                    "summary": action[:100] + "..." if len(action) > 100 else action
                })
            
            # Extract NPCs and locations
            npcs_in_text = self._extract_npc_names(combined)
            npcs_encountered.update(npcs_in_text)
            
            for location in self.memory_categories["key_locations"]:
                if location in combined.lower():
                    locations_mentioned.add(location.title())
        
        return {
            "campaign_id": campaign_id,
            "episode_id": episode_id,
            "consolidated_at": datetime.now().isoformat(),
            "summary": f"Episode with {len(recent_history)} interactions completed",
            "key_events": key_events[-5:],  # Top 5 key events
            "npcs_encountered": list(npcs_encountered)[:5],  # Top 5 NPCs
            "locations_visited": list(locations_mentioned)[:3],  # Top 3 locations
            "interaction_count": len(recent_history)
        }
    
    def get_memory_stats(self, campaign_id: str) -> Dict[str, Any]:
        """Get memory system statistics"""
        
        if not self.memory_available:
            return {"status": "Memory system not available"}
        
        # This would be implemented based on your actual database schema
        return {
            "memory_available": self.memory_available,
            "campaign_id": campaign_id,
            "last_context_build": "Available",
            "storage_available": "Available" if hasattr(self.memory_ops, 'store_conversation_memory') else "Limited"
        }

class MockMemoryOperations:
    """Mock memory operations for when database isn't available"""
    
    async def store_conversation_memory(self, **kwargs):
        """Mock storage - always returns True"""
        return True
    
    async def retrieve_relevant_memories(self, **kwargs):
        """Mock retrieval - returns empty list"""
        return []
    
    async def get_campaign_npcs(self, **kwargs):
        """Mock NPC retrieval - returns Storm King's Thunder default NPCs"""
        return [
            MockNPC("Zephyros", "Ancient cloud giant wizard", "Helpful guide"),
            MockNPC("Harshnag", "Frost giant ally", "Trusted ally"),
            MockNPC("Princess Serissa", "Storm giant princess", "Important quest giver")
        ]
    
    async def consolidate_episode_memories(self, **kwargs):
        """Mock consolidation - returns basic result"""
        return {
            "campaign_id": kwargs.get("campaign_id", "unknown"),
            "episode_id": kwargs.get("episode_id", 0),
            "consolidated_at": datetime.now().isoformat(),
            "summary": "Basic consolidation completed (mock mode)"
        }
    
    async def update_npc_memory(self, **kwargs):
        """Mock NPC update"""
        return True
    
    async def update_world_state(self, **kwargs):
        """Mock world state update"""
        return True

class MockNPC:
    """Mock NPC object for compatibility"""
    def __init__(self, name: str, personality: str, relationship: str):
        self.name = name
        self.personality_summary = personality
        self.relationship_with_party = relationship
        self.current_location = "Unknown"
        self.status = "Active"

class MockMemory:
    """Mock memory object for compatibility"""
    def __init__(self, character_name: str, summary: str, importance_score: float, scene_context: str = ""):
        self.character_name = character_name
        self.summary = summary
        self.importance_score = importance_score
        self.scene_context = scene_context

# ===== CONVENIENCE FUNCTIONS FOR BACKWARD COMPATIBILITY =====

async def get_persistent_dm_response(*args, **kwargs):
    """
    Deprecated: Use unified_dm_response.generate_dm_response() instead
    This function is kept for backward compatibility but will print a warning
    """
    print("⚠️ WARNING: get_persistent_dm_response() is deprecated. Use unified_dm_response.generate_dm_response() instead.")
    
    # Try to import and use the unified system
    try:
        from unified_dm_response import generate_dm_response
        # Extract the required parameters from args/kwargs
        if len(args) >= 4:
            user_id = args[1]
            player_input = args[2] 
            guild_id = args[3]
            episode_id = args[4] if len(args) > 4 else kwargs.get('episode_id', 1)
        else:
            user_id = kwargs.get('user_id')
            player_input = kwargs.get('player_input')
            guild_id = kwargs.get('guild_id')
            episode_id = kwargs.get('episode_id', 1)
        
        if all([user_id, player_input, guild_id]):
            response, mode = await generate_dm_response(user_id, player_input, guild_id, episode_id)
            return response
        else:
            return "Error: Missing required parameters for response generation"
            
    except Exception as e:
        print(f"❌ Failed to use unified response system: {e}")
        return "Donnie pauses thoughtfully as the giant crisis unfolds around you..."

async def store_interaction_background(*args, **kwargs):
    """
    Deprecated: Use unified_dm_response.store_interaction_background() instead
    This function is kept for backward compatibility
    """
    print("⚠️ WARNING: store_interaction_background() from enhanced_dm_system is deprecated. Use unified_dm_response.store_interaction_background() instead.")
    
    try:
        from unified_dm_response import store_interaction_background as unified_store
        return await unified_store(*args, **kwargs)
    except Exception as e:
        print(f"❌ Failed to use unified memory storage: {e}")
        return False

class PersistentDMSystem:
    """
    Deprecated: Use unified_dm_response.UnifiedDMResponseSystem instead
    This class is kept for backward compatibility but will print warnings
    """
    
    def __init__(self, *args, **kwargs):
        print("⚠️ WARNING: PersistentDMSystem is deprecated. Use unified_dm_response.UnifiedDMResponseSystem instead.")
        self.memory_manager = EnhancedMemoryManager(*args, **kwargs)
    
    async def get_enhanced_dm_response(self, *args, **kwargs):
        print("⚠️ WARNING: get_enhanced_dm_response() is deprecated. Use unified_dm_response.generate_dm_response() instead.")
        return await get_persistent_dm_response(None, *args, **kwargs)
    
    async def store_interaction_memory(self, *args, **kwargs):
        return await self.memory_manager.store_interaction_memory(*args, **kwargs)
    
    async def end_episode_consolidation(self, *args, **kwargs):
        return await self.memory_manager.consolidate_episode_memories(*args, **kwargs)