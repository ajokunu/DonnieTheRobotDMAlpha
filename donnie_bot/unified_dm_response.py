# unified_dm_response.py - COMPLETE FILE
"""
Unified DM Response System for Storm King's Thunder
Single entry point for all DM response generation with clear fallback hierarchy:
Enhanced Memory → Streamlined → Basic Fallback

This replaces all duplicate response generators in main.py and enhanced_dm_system.py
"""

import asyncio
import time
import random
from typing import Dict, Optional, Tuple, List, Any  # Make sure Optional is imported
from enum import Enum
from datetime import datetime

class ResponseMode(Enum):
    """Response generation modes in order of preference"""
    ENHANCED_MEMORY = "enhanced_memory"
    STREAMLINED = "streamlined" 
    BASIC_FALLBACK = "basic_fallback"
    EMERGENCY_FALLBACK = "emergency_fallback"

class UnifiedDMResponseSystem:
    """
    Single, unified system for generating DM responses with clear fallback hierarchy.
    
    This eliminates duplicate response generators and provides:
    - Single entry point for all DM responses
    - Intelligent fallback system
    - Memory integration when available
    - Performance optimizations
    - Centralized error handling
    """
    
    def __init__(self, claude_client, campaign_context: Dict, 
                persistent_memory_available: bool = False,
                database_operations=None,
                max_response_length: int = 450,
                response_timeout: float = 8.0, **kwargs):
        
        self.claude_client = claude_client
        self.campaign_context = campaign_context
        self.persistent_memory_available = persistent_memory_available
        self.database_operations = database_operations
        self.max_response_length = max_response_length
        self.response_timeout = response_timeout
        
        # Performance tracking
        self.response_count = {"enhanced_memory": 0, "streamlined": 0, "basic_fallback": 0, "emergency_fallback": 0}
        self.total_requests = 0
        
        # FIXED: Use the real memory operations instead of deprecated enhanced_dm_system
        self.memory_ops = None
        if persistent_memory_available and database_operations:
            if hasattr(database_operations, 'memory_ops') and database_operations.memory_ops:
                self.memory_ops = database_operations.memory_ops
                print("✅ Real memory operations connected to unified response system")
            else:
                print("⚠️ Database operations available but no memory_ops found")
                self.persistent_memory_available = False
        else:
            print("⚠️ Memory operations not available")
            self.persistent_memory_available = False
            
        self.structured_memory = None
        if self.persistent_memory_available and self.memory_ops:
            try:
                # SAFE: Import with relative path
                import sys
                import os
                sys.path.append(os.path.dirname(__file__))
                
                from structured_memory import StructuredMemoryBuilder
                self.structured_memory = StructuredMemoryBuilder(self.memory_ops, campaign_context)
                print("✅ Structured memory builder initialized")
            except ImportError as e:
                print(f"⚠️ Structured memory not available: {e}")
            except Exception as e:
                print(f"⚠️ Structured memory initialization failed: {e}")
        else:
            print("⚠️ Prerequisites not available for structured memory")
        
        # Storm King's Thunder specific context
        self.campaign_prompts = {
            "setting_context": "The Sword Coast during the giant crisis. The ancient ordning that kept giant society in check has collapsed, throwing giantkind into chaos.",
            "threat_level": "Giants of all types roam the land unchecked, raiding settlements and terrorizing the small folk.",
            "tone": "Epic fantasy adventure with real consequences and meaningful choices."
        }
        
        print(f"🎯 Unified DM Response System initialized (Memory: {'✅' if self.persistent_memory_available else '❌'})")
    
    async def generate_dm_response(self, user_id: str, player_input: str, 
                                guild_id: str, episode_id: int) -> Tuple[str, ResponseMode]:
        """
        MAIN ENTRY POINT: Generate DM response using unified system
        
        Args:
            user_id: Discord user ID
            player_input: What the player wants to do
            guild_id: Discord guild ID  
            episode_id: Current episode ID
            
        Returns:
            Tuple of (response_text, mode_used)
        """
        
        start_time = time.time()
        self.total_requests += 1
        
        # Validate inputs
        if not self._validate_inputs(user_id, player_input, guild_id):
            response = self._get_emergency_fallback_response(player_input)
            self.response_count["emergency_fallback"] += 1
            return response, ResponseMode.EMERGENCY_FALLBACK
        
        # Ensure guild_id is string for consistency
        guild_id = str(guild_id)
        
        # Get character info for context
        char_data = self.campaign_context["players"][user_id]["character_data"]
        character_name = char_data["name"]
        
        print(f"🎯 Unified Response: {character_name} in guild {guild_id}: '{player_input[:50]}...'")
        
        # Try Enhanced Memory first (if available)
        if self.persistent_memory_available and self.memory_ops:
            try:
                print("🧠 Attempting enhanced memory response...")
                response = await asyncio.wait_for(
                    self._generate_enhanced_memory_response(
                        user_id, player_input, guild_id, episode_id, character_name
                    ),
                    timeout=self.response_timeout
                )
                
                if response and len(response.strip()) > 10:
                    elapsed = time.time() - start_time
                    self.response_count["enhanced_memory"] += 1
                    print(f"✅ Enhanced memory response generated in {elapsed:.2f}s")
                    return response, ResponseMode.ENHANCED_MEMORY
                else:
                    print("⚠️ Enhanced memory response too short, falling back...")
                    
            except asyncio.TimeoutError:
                print("⚠️ Enhanced memory response timeout, falling back to streamlined...")
            except Exception as e:
                print(f"⚠️ Enhanced memory response error: {e}, falling back...")
        
        # Fallback to Streamlined response
        try:
            print("⚡ Attempting streamlined response...")
            response = await asyncio.wait_for(
                self._generate_streamlined_response(user_id, player_input, character_name),
                timeout=self.response_timeout
            )
            
            if response and len(response.strip()) > 10:
                elapsed = time.time() - start_time
                self.response_count["streamlined"] += 1
                print(f"✅ Streamlined response generated in {elapsed:.2f}s")
                return response, ResponseMode.STREAMLINED
            else:
                print("⚠️ Streamlined response too short, using basic fallback...")
                
        except asyncio.TimeoutError:
            print("⚠️ Streamlined response timeout, using basic fallback...")
        except Exception as e:
            print(f"⚠️ Streamlined response error: {e}, using basic fallback...")
        
        # Final fallback to basic response (no API calls)
        print("🔄 Using basic fallback response...")
        response = self._get_basic_fallback_response(player_input, character_name)
        elapsed = time.time() - start_time
        self.response_count["basic_fallback"] += 1
        print(f"✅ Basic fallback response in {elapsed:.2f}s")
        return response, ResponseMode.BASIC_FALLBACK
    
    async def _generate_enhanced_memory_response(self, user_id: str, player_input: str, 
                                        guild_id: str, episode_id: int, 
                                        character_name: str) -> str:
        """Generate response with enhanced memory context using REAL memory operations"""
        
        if not self.memory_ops:
            raise Exception("Memory operations not available")
        
        # Get memory context using REAL memory operations
        try:
            # Get relevant memories
            memories = await self.memory_ops.retrieve_relevant_memories(
                campaign_id=guild_id,
                query=player_input,
                max_memories=3,
                min_importance=0.4
            )
            
            # Get important NPCs
            npcs = await self.memory_ops.get_campaign_npcs(guild_id, "important")
            
            # Build memory context
            memory_context = {
                "relevant_memories": [
                    {
                        "character": getattr(mem, 'character_name', 'Unknown'),
                        "summary": getattr(mem, 'summary', str(mem)[:100]),
                        "importance": getattr(mem, 'importance_score', 0.5),
                        "scene_context": getattr(mem, 'scene_context', '')
                    }
                    for mem in memories[:3]
                ],
                "active_npcs": [
                    {
                        "name": getattr(npc, 'name', 'Unknown NPC'),
                        "personality": getattr(npc, 'personality_summary', 'Mysterious'),
                        "relationship": getattr(npc, 'relationship_with_party', 'Unknown'),
                        "location": getattr(npc, 'current_location', 'Unknown'),
                        "status": getattr(npc, 'status', 'Active')
                    }
                    for npc in npcs[:3]
                ],
                "recent_events": []
            }
            
            # Add recent session history
            recent_history = self.campaign_context.get("session_history", [])[-3:]
            memory_context["recent_events"] = [
                f"{entry.get('player', 'Unknown')}: {entry.get('action', '')}"
                for entry in recent_history
            ]
            
            print(f"🧠 Retrieved {len(memories)} memories and {len(npcs)} NPCs")
            
        except Exception as e:
            print(f"⚠️ Memory retrieval error: {e}")
            # Fallback to basic context
            memory_context = {
                "relevant_memories": [],
                "active_npcs": [],
                "recent_events": []
            }
        
        # Build enhanced prompt with memory
        prompt = self._build_enhanced_memory_prompt(
            character_name, player_input, memory_context
        )
        
        # Generate response with Claude
        response = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: self.claude_client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=min(300, self.max_response_length // 3),
                temperature=0.8,
                messages=[{"role": "user", "content": prompt}]
            )
        )
        
        # Extract and process response
        if hasattr(response.content[0], 'text'):
            dm_response = response.content[0].text.strip()
        else:
            dm_response = str(response.content[0]).strip()
        
        # Ensure response is under limit
        if len(dm_response) > self.max_response_length:
            dm_response = dm_response[:self.max_response_length-3] + "..."
        
        # Update session history with memory context
        self._update_session_history(user_id, player_input, dm_response, "enhanced_memory")
        
        return dm_response
    
    async def _generate_streamlined_response(self, user_id: str, player_input: str, 
                                           character_name: str) -> str:
        """Generate streamlined response without memory features"""
        
        # Get character and party info
        player_data = self.campaign_context["players"][user_id]
        char_data = player_data["character_data"]
        player_name = player_data["player_name"]
        
        # Format party information concisely
        party_info = []
        for uid, p_data in self.campaign_context["players"].items():
            c_data = p_data["character_data"]
            party_info.append(f"{c_data['name']} (Lvl {c_data['level']} {c_data['race']} {c_data['class']})")
        
        # Get recent context from session history
        recent_context = ""
        recent_history = self.campaign_context.get("session_history", [])[-2:]
        if recent_history:
            recent_context = "\n".join([
                f"Recent: {entry.get('player', 'Unknown')}: {entry.get('action', '')[:50]}..."
                for entry in recent_history
            ])
        
        # Build streamlined prompt (fix f-string backslash issue)
        recent_context_section = f"**RECENT CONTEXT**:\n{recent_context}" if recent_context else ""

        prompt = f"""You are AlphaDonnie, experienced DM for Storm King's Thunder D&D 5e 2024.

**SETTING**: {self.campaign_prompts['setting_context']}

**CURRENT SCENE**: {self.campaign_context.get('current_scene', 'Adventure continues')[:500]}

**PARTY**: {', '.join(party_info)}

**THREAT LEVEL**: {self.campaign_prompts['threat_level']}

{recent_context_section}

**DM GUIDELINES**:
- Follow D&D 5th Edition 2024 rules precisely
- Use current scene as starting point
- Progress story naturally when players move or investigate
- Ask for dice rolls when rules require them
- Make consequences meaningful in this giant-threatened world
- Keep responses under {self.max_response_length} characters
- Create immersive, dramatic moments
- Be fair and consistent with rules and ensure players follow the 2024 ruleset
- NPCs should have distinct personalities and relationships shaped by the giant crisis
- Combat should be well defined, with clear turn order and actions. 
- Combat should be difficult but fair.

**PLAYER ACTION**: {character_name}: {player_input}

**DM RESPONSE** (under {self.max_response_length} chars, maintain epic tone):
"""
        
        # Single Claude API call
        response = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: self.claude_client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=min(550, self.max_response_length // 3),
                temperature=0.8,  # Slightly more creative for streamlined
                messages=[{"role": "user", "content": prompt}]
            )
        )
        
        # Extract and process response
        if hasattr(response.content[0], 'text'):
            dm_response = response.content[0].text.strip()
        else:
            dm_response = str(response.content[0]).strip()
        
        # Ensure response is under limit
        if len(dm_response) > self.max_response_length:
            dm_response = dm_response[:self.max_response_length-3] + "..."
        
        # Update session history
        self._update_session_history(user_id, player_input, dm_response, "streamlined")
        
        return dm_response
    
    async def _generate_enhanced_memory_response_v2(self, user_id: str, player_input: str, 
                                                  guild_id: str, episode_id: int, 
                                                  character_name: str, channel_id: Optional[int] = None) -> str:
        """Enhanced memory response with structured context - SAFE VERSION"""
        
        # SAFE: Fall back to original method if structured memory unavailable
        if not self.structured_memory:
            print("⚠️ Structured memory unavailable, using original method")
            return await self._generate_enhanced_memory_response(
                user_id, player_input, guild_id, episode_id, character_name
            )
        
        # SAFE: Try structured approach with fallback
        try:
            memory_context = await self.structured_memory.build_reliable_context(
                guild_id=guild_id,
                player_input=player_input,
                character_name=character_name,
                channel_id=channel_id
            )
            
            prompt = self._build_campaign_memory_prompt(character_name, player_input, memory_context)
            
            response = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.claude_client.messages.create(
                    model="claude-sonnet-4-20250514",
                    max_tokens=min(300, self.max_response_length // 3),
                    temperature=0.7,
                    messages=[{"role": "user", "content": prompt}]
                )
            )
            
            dm_response = response.content[0].text.strip()
            if len(dm_response) > self.max_response_length:
                dm_response = dm_response[:self.max_response_length-3] + "..."
            
            self._update_session_history(user_id, player_input, dm_response, "enhanced_memory_v2")
            return dm_response
            
        except Exception as e:
            print(f"⚠️ Structured memory failed, falling back: {e}")
            return await self._generate_enhanced_memory_response(
                user_id, player_input, guild_id, episode_id, character_name
            )

    def _build_campaign_memory_prompt(self, character_name: str, player_input: str, 
                                    memory_context: Dict[str, Any]) -> str:
        """Build prompt that prevents false campaign memories while allowing D&D content"""
        
        party_status = memory_context.get('party_status', 'No party registered')
        
        prompt = f"""You are Donnie, DM for Storm King's Thunder D&D 5e 2024.

**VERIFIED CAMPAIGN HISTORY** (ONLY reference these when discussing past sessions):
{chr(10).join(memory_context.get('recent_events', ['No recent campaign events']))}

**VERIFIED CAMPAIGN MEMORIES** (Past events in THIS specific campaign):
{chr(10).join(memory_context.get('character_memories', ['No campaign memories available']))}

**CURRENT GAME STATE**:
- Scene: {memory_context.get('current_scene', 'Adventure continues')}
- Combat: {memory_context.get('combat_state', 'No active combat')}
- Party: {party_status}

**YOUR DM AUTHORITY** - You may freely use:
✅ All D&D 5e 2024 rules, spells, monsters, mechanics
✅ Storm King's Thunder content (Nightstone, Zephyros, giant lords, etc.)
✅ Create new NPCs, encounters, locations as the story requires
✅ Make rulings and progress the narrative naturally

**CAMPAIGN MEMORY RESTRICTION** - Never reference:
❌ Past campaign events NOT listed in "VERIFIED CAMPAIGN HISTORY"
❌ Previous player actions NOT in "VERIFIED CAMPAIGN MEMORIES" 
❌ Made-up events like "Remember when you fought X last week"

**CURRENT PLAYER ACTION**: {character_name}: {player_input}

**DM RESPONSE** (use D&D/SKT freely, only verified campaign history, under {self.max_response_length} chars):"""
        
        return prompt

    def _build_enhanced_memory_prompt(self, character_name: str, player_input: str, 
                                    memory_context: Dict[str, Any]) -> str:
        """Build enhanced prompt with memory context"""
        
        # Base context
        base_context = f"""You are Donnie, DM for Storm King's Thunder D&D 5e 2024.

**SETTING**: {self.campaign_prompts['setting_context']}
**CURRENT SCENE**: {self.campaign_context.get('current_scene', 'Adventure continues')[:500]}
**THREAT LEVEL**: {self.campaign_prompts['threat_level']}"""
        
        # Add party information
        party_info = []
        for user_id, player_data in self.campaign_context.get("players", {}).items():
            char_data = player_data["character_data"]
            party_info.append(f"{char_data['name']} (Lvl {char_data['level']} {char_data['race']} {char_data['class']})")
        
        if party_info:
            base_context += f"\n**PARTY**: {', '.join(party_info)}"
        
        # Add memory context
        memory_section = ""
        
        # Recent events
        recent_events = memory_context.get("recent_events", [])
        if recent_events:
            memory_section += f"\n\n**RECENT EVENTS**:\n" + "\n".join(recent_events)
        
        # Relevant memories
        relevant_memories = memory_context.get("relevant_memories", [])
        if relevant_memories:
            memory_section += f"\n\n**RELEVANT PAST EVENTS**:"
            for memory in relevant_memories:
                importance = memory.get('importance', 0.5)
                memory_section += f"\n• {memory['character']}: {memory['summary']} (Importance: {importance:.1f})"
        
        # Active NPCs
        active_npcs = memory_context.get("active_npcs", [])
        if active_npcs:
            memory_section += f"\n\n**KNOWN NPCs**:"
            for npc in active_npcs:
                npc_desc = f"\n• {npc['name']}: {npc['personality']}"
                if npc.get('relationship'):
                    npc_desc += f" (Relationship: {npc['relationship']})"
                memory_section += npc_desc
        
        # Build final prompt
        enhanced_prompt = f"""{base_context}{memory_section}

**ENHANCED MEMORY GUIDELINES**:
- Reference relevant past events naturally when appropriate
- Maintain NPC personality consistency based on their known traits
- Build on previous player choices and their consequences
- React to the current action while maintaining campaign continuity
- Create dramatic, memorable moments worthy of the giant crisis
- Keep responses under {self.max_response_length} characters

**CURRENT PLAYER ACTION**: {character_name}: {player_input}

**DONNIE'S MEMORY-ENHANCED RESPONSE** (under {self.max_response_length} chars):"""
        
        return enhanced_prompt
    
    def _get_basic_fallback_response(self, player_input: str, character_name: str = "adventurer") -> str:
        """Generate basic fallback response without API calls"""
        
        input_lower = player_input.lower()
        
        # Context-aware responses based on Storm King's Thunder
        if any(word in input_lower for word in ["look", "see", "observe", "examine"]):
            fallback_responses = [
                f"Donnie describes the scene before {character_name}, noting the telltale signs of giant activity - massive footprints, toppled trees, and the eerie silence that follows in their wake.",
                f"The landscape bears the scars of the giant crisis as Donnie paints a vivid picture of destruction and opportunity for {character_name}.",
                f"Donnie's keen eye for detail reveals both the beauty of the Sword Coast and the ominous threat that giants pose to all who call it home."
            ]
        
        elif any(word in input_lower for word in ["attack", "fight", "combat", "strike"]):
            fallback_responses = [
                f"Donnie calls for initiative as {character_name} enters combat! The sound of battle echoes across the giant-scarred landscape.",
                f"Steel rings against steel as {character_name} joins the fray! Donnie tracks each blow in this deadly dance against the giant threat.",
                f"Combat erupts around {character_name}! Donnie narrates the chaos of battle in a world where giants have upset the natural order."
            ]
        
        elif any(word in input_lower for word in ["talk", "speak", "say", "ask"]):
            fallback_responses = [
                f"Donnie voices the NPC's response to {character_name}, bringing the character to life with distinct personality shaped by the giant crisis.",
                f"The conversation unfolds as Donnie roleplays the NPC's reaction to {character_name}, adding depth to this troubled world.",
                f"Donnie speaks for the locals, their voices tinged with fear and hope as they interact with {character_name} in these dark times."
            ]
        
        elif any(word in input_lower for word in ["move", "go", "walk", "travel"]):
            fallback_responses = [
                f"Donnie describes {character_name}'s journey through the giant-threatened landscape, where danger and adventure await around every bend.",
                f"The path ahead unfolds before {character_name} as Donnie narrates their movement through the chaos-torn Sword Coast.",
                f"Donnie guides {character_name} through terrain marked by giant raids, where every step could lead to discovery or danger."
            ]
        
        elif any(word in input_lower for word in ["search", "investigate", "check"]):
            fallback_responses = [
                f"Donnie calls for an investigation roll as {character_name} searches for clues about the giant crisis and its far-reaching effects.",
                f"The search reveals secrets as Donnie guides {character_name} through their investigation of this giant-scarred world.",
                f"Donnie describes what {character_name} discovers, weaving their findings into the larger tapestry of the giant threat."
            ]
        
        elif any(word in input_lower for word in ["cast", "spell", "magic"]):
            fallback_responses = [
                f"Magical energies crackle around {character_name} as Donnie narrates the spell's effects in this world where even magic feels the giant crisis.",
                f"Donnie describes the arcane forces at {character_name}'s command, their power a beacon of hope against the giant menace.",
                f"The weave responds to {character_name}'s will as Donnie brings their magical action to vivid life."
            ]
        
        elif "continue" in input_lower:
            fallback_responses = [
                f"The story unfolds further as Donnie continues the epic tale of {character_name}'s adventures in the giant-threatened realm.",
                f"Donnie picks up the narrative thread, weaving {character_name}'s story deeper into the Storm King's Thunder campaign.",
                f"The adventure progresses as Donnie reveals what happens next in {character_name}'s journey through this chaotic time."
            ]
        
        else:
            # Generic epic responses
            fallback_responses = [
                f"Donnie responds with dramatic flair, showing how {character_name}'s actions ripple through the giant-threatened world of the Sword Coast.",
                f"The consequences of {character_name}'s choice unfold as Donnie masterfully weaves their action into the ongoing crisis.",
                f"Donnie brings the scene to life, demonstrating how {character_name}'s decision shapes their destiny in this time of giants.",
                f"The epic tale continues as Donnie shows how {character_name}'s bravery stands against the chaos of the collapsed ordning.",
                f"Donnie crafts a memorable moment for {character_name}, their action becoming part of the legend in this giant-scarred age."
            ]
        
        return random.choice(fallback_responses)
    
    def _get_emergency_fallback_response(self, player_input: str) -> str:
        """Emergency fallback when everything else fails"""
        return "Donnie pauses momentarily, gathering his thoughts about the giant crisis unfolding across the Sword Coast, then continues the epic adventure..."
    
    def _update_session_history(self, user_id: str, player_input: str, 
                               dm_response: str, mode: str):
        """Update session history with the interaction"""
        
        try:
            player_data = self.campaign_context["players"][user_id]
            char_data = player_data["character_data"]
            character_name = char_data["name"]
            player_name = player_data["player_name"]
            
            # Add to session history
            self.campaign_context["session_history"].append({
                "player": f"{character_name} ({player_name})",
                "action": player_input,
                "dm_response": dm_response,
                "mode": mode,
                "timestamp": datetime.now().isoformat()
            })
            
            # Keep only last 10 entries for performance
            if len(self.campaign_context["session_history"]) > 10:
                self.campaign_context["session_history"] = self.campaign_context["session_history"][-10:]
                
        except Exception as e:
            print(f"⚠️ Error updating session history: {e}")
    
    def _validate_inputs(self, user_id: str, player_input: str, guild_id: str) -> bool:
        """Validate inputs for response generation"""
        
        if not user_id or not player_input or not guild_id:
            print("❌ Missing required parameters for response generation")
            return False
        
        if user_id not in self.campaign_context.get("players", {}):
            print(f"❌ User {user_id} not found in campaign context")
            return False
        
        if not self.campaign_context.get("session_started", False) and not self.campaign_context.get("episode_active", False):
            print("❌ No active session or episode")
            return False
        
        return True
    
    async def store_interaction_memory(self, guild_id: str, episode_id: int, 
                                     user_id: str, player_input: str, 
                                     dm_response: str) -> bool:
        """Store interaction in memory system using REAL operations"""
        
        if not self.persistent_memory_available or not self.memory_ops:
            return False
        
        try:
            # Get character info
            if user_id not in self.campaign_context.get("players", {}):
                print(f"❌ User {user_id} not in campaign context")
                return False
            
            player_data = self.campaign_context["players"][user_id]
            char_data = player_data["character_data"]
            character_name = char_data["name"]
            
            # Store using REAL memory operations
            result = await self.memory_ops.store_conversation_memory(
                campaign_id=str(guild_id),
                episode_id=episode_id,
                user_id=user_id,
                character_name=character_name,
                player_input=player_input,
                dm_response=dm_response
            )
            
            if result:
                print(f"✅ Stored memory for {character_name}")
            else:
                print(f"⚠️ Failed to store memory for {character_name}")
            
            return bool(result)
            
        except Exception as e:
            print(f"❌ Memory storage error: {e}")
            return False
    
    def get_system_status(self) -> Dict[str, str]:
        """Get comprehensive status of all response generation systems"""
        
        # Calculate success rates
        total = self.total_requests
        if total > 0:
            enhanced_rate = (self.response_count["enhanced_memory"] / total) * 100
            streamlined_rate = (self.response_count["streamlined"] / total) * 100
            fallback_rate = (self.response_count["basic_fallback"] / total) * 100
            emergency_rate = (self.response_count["emergency_fallback"] / total) * 100
        else:
            enhanced_rate = streamlined_rate = fallback_rate = emergency_rate = 0
        
        status = {
            "enhanced_memory": f"{'✅ Available' if (self.persistent_memory_available and self.memory_ops) else '❌ Not Available'} ({enhanced_rate:.1f}%)",
            "streamlined": f"✅ Available ({streamlined_rate:.1f}%)",
            "basic_fallback": f"✅ Available ({fallback_rate:.1f}%)",
            "emergency_fallback": f"✅ Available ({emergency_rate:.1f}%)",
            "total_requests": str(total),
            "max_response_length": f"{self.max_response_length} chars",
            "response_timeout": f"{self.response_timeout}s",
            "claude_model": "claude-sonnet-4-20250514"
        }
        
        return status
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get detailed performance metrics"""
        
        return {
            "response_counts": self.response_count.copy(),
            "total_requests": self.total_requests,
            "success_rate": ((self.total_requests - self.response_count["emergency_fallback"]) / max(self.total_requests, 1)) * 100,
            "enhanced_memory_rate": (self.response_count["enhanced_memory"] / max(self.total_requests, 1)) * 100,
            "system_health": "Excellent" if self.response_count["emergency_fallback"] == 0 else "Good" if self.response_count["emergency_fallback"] < (self.total_requests * 0.1) else "Needs Attention"
        }

# ===== GLOBAL INSTANCE AND CONVENIENCE FUNCTIONS =====

# Global unified response system instance
unified_response_system = None

def initialize_unified_response_system(claude_client, campaign_context: Dict,
                                     persistent_memory_available: bool = False,
                                     database_operations=None,
                                     max_response_length: int = 450,
                                     response_timeout: float = 8.0) -> UnifiedDMResponseSystem:
    """
    Initialize the unified response system (call this in main.py startup)
    
    Args:
        claude_client: Anthropic Claude client
        campaign_context: Main campaign context dictionary
        persistent_memory_available: Whether enhanced memory is available
        database_operations: Database operations for memory system
        max_response_length: Maximum response length in characters
        response_timeout: Timeout for response generation in seconds
        
    Returns:
        Initialized UnifiedDMResponseSystem instance
    """
    
    global unified_response_system
    
    unified_response_system = UnifiedDMResponseSystem(
        claude_client=claude_client,
        campaign_context=campaign_context,
        persistent_memory_available=persistent_memory_available,
        database_operations=database_operations,
        max_response_length=max_response_length,
        response_timeout=response_timeout
    )
    
    print("✅ Unified DM Response System initialized successfully")
    return unified_response_system

async def generate_dm_response(user_id: str, player_input: str, 
                             guild_id: str, episode_id: int) -> Tuple[str, str]:
    """
    MAIN INTERFACE: Generate DM response using unified system
    
    Args:
        user_id: Discord user ID
        player_input: What the player wants to do
        guild_id: Discord guild ID
        episode_id: Current episode ID
        
    Returns:
        Tuple of (response_text, mode_used_string)
    """
    
    if not unified_response_system:
        raise RuntimeError("Unified response system not initialized! Call initialize_unified_response_system() first.")
    
    response, mode = await unified_response_system.generate_dm_response(
        user_id=user_id,
        player_input=player_input,
        guild_id=guild_id,
        episode_id=episode_id
    )
    
    return response, mode.value

async def store_interaction_background(guild_id: str, episode_id: int, 
                                     user_id: str, player_input: str, 
                                     dm_response: str) -> bool:
    """Store interaction in background (if enhanced memory available)"""
    
    if not unified_response_system:
        return False
    
    return await unified_response_system.store_interaction_memory(
        guild_id=guild_id,
        episode_id=episode_id,
        user_id=user_id,
        player_input=player_input,
        dm_response=dm_response
    )

def get_response_system_status() -> Dict[str, str]:
    """Get status of response generation systems"""
    
    if not unified_response_system:
        return {"status": "❌ Not Initialized"}
    
    return unified_response_system.get_system_status()

def get_performance_metrics() -> Dict[str, Any]:
    """Get detailed performance metrics"""
    
    if not unified_response_system:
        return {"error": "System not initialized"}
    
    return unified_response_system.get_performance_metrics()

# ===== UTILITY FUNCTIONS =====

def reset_performance_metrics():
    """Reset performance tracking metrics"""
    
    if unified_response_system:
        unified_response_system.response_count = {"enhanced_memory": 0, "streamlined": 0, "basic_fallback": 0, "emergency_fallback": 0}
        unified_response_system.total_requests = 0
        print("✅ Performance metrics reset")

def is_system_healthy() -> bool:
    """Check if the response system is healthy"""
    
    if not unified_response_system:
        return False
    
    metrics = unified_response_system.get_performance_metrics()
    return metrics["success_rate"] > 90.0