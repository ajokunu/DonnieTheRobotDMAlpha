# donnie_bot/database/memory_operations.py
"""
Advanced Memory Operations for Persistent DM Memory System
Handles conversation memory, NPC tracking, world state, and intelligent retrieval
"""

import sqlite3
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any, Tuple
import json
import re
from dataclasses import dataclass, asdict
import asyncio

@dataclass
class ConversationMemory:
    """Data structure for conversation memories"""
    memory_id: Optional[int] = None
    campaign_id: str = ""
    episode_id: Optional[int] = None
    user_id: str = ""
    character_name: str = ""
    player_input: str = ""
    dm_response: str = ""
    summary: str = ""
    entities: List[str] = None
    importance_score: float = 0.5
    emotional_context: str = ""
    timestamp: Optional[datetime] = None
    scene_context: str = ""
    combat_context: str = ""
    
    def __post_init__(self):
        if self.entities is None:
            self.entities = []
        if self.timestamp is None:
            self.timestamp = datetime.now()

@dataclass 
class NPCMemory:
    """Data structure for NPC memories"""
    npc_id: Optional[int] = None
    campaign_id: str = ""
    name: str = ""
    description: str = ""
    personality_summary: str = ""
    first_encountered_episode: Optional[int] = None
    last_seen_episode: Optional[int] = None
    relationship_with_party: str = ""
    current_location: str = ""
    faction_affiliation: str = ""
    knowledge_base: Dict[str, Any] = None
    secrets: List[str] = None
    goals: List[str] = None
    mannerisms: str = ""
    voice_description: str = ""
    importance_level: str = "minor"
    status: str = "alive"
    notes: str = ""
    last_updated: Optional[datetime] = None
    
    def __post_init__(self):
        if self.knowledge_base is None:
            self.knowledge_base = {}
        if self.secrets is None:
            self.secrets = []
        if self.goals is None:
            self.goals = []
        if self.last_updated is None:
            self.last_updated = datetime.now()

class AdvancedMemoryOperations:
    """Advanced memory operations for persistent DM memory"""
    
    def __init__(self, claude_client):
        self.claude_client = claude_client
        
    def get_db_connection(self):
        """Get database connection"""
        from .database import get_db_connection
        return get_db_connection()
    
    async def store_conversation_memory(self, campaign_id: str, episode_id: int, 
                                      user_id: str, character_name: str,
                                      player_input: str, dm_response: str) -> ConversationMemory:
        """Store a conversation memory with AI analysis"""
        
        # Analyze the conversation with Claude
        analysis = await self._analyze_conversation(player_input, dm_response, character_name)
        
        memory = ConversationMemory(
            campaign_id=campaign_id,
            episode_id=episode_id,
            user_id=user_id,
            character_name=character_name,
            player_input=player_input,
            dm_response=dm_response,
            summary=analysis.get('summary', ''),
            entities=analysis.get('entities', []),
            importance_score=analysis.get('importance_score', 0.5),
            emotional_context=analysis.get('emotional_context', ''),
            scene_context=analysis.get('scene_context', ''),
            combat_context=analysis.get('combat_context', '')
        )
        
        # Store in database
        conn = self.get_db_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT INTO conversation_memories 
                (campaign_id, episode_id, user_id, character_name, player_input, dm_response,
                 summary, entities, importance_score, emotional_context, scene_context, combat_context)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                memory.campaign_id, memory.episode_id, memory.user_id, memory.character_name,
                memory.player_input, memory.dm_response, memory.summary,
                json.dumps(memory.entities), memory.importance_score, memory.emotional_context,
                memory.scene_context, memory.combat_context
            ))
            
            memory.memory_id = cursor.lastrowid
            conn.commit()
            
            print(f"✅ Stored conversation memory {memory.memory_id} with importance {memory.importance_score:.2f}")
            
            # Check for new NPCs in the conversation
            await self._extract_and_update_npcs(campaign_id, episode_id, analysis)
            
            return memory
            
        except Exception as e:
            print(f"❌ Error storing conversation memory: {e}")
            conn.rollback()
            raise e
        finally:
            conn.close()
    
    async def retrieve_relevant_memories(self, campaign_id: str, query: str, 
                                       max_memories: int = 10, 
                                       min_importance: float = 0.3) -> List[ConversationMemory]:
        """Retrieve memories relevant to the current query"""
        
        conn = self.get_db_connection()
        cursor = conn.cursor()
        
        try:
            # Get recent high-importance memories first
            cursor.execute('''
                SELECT * FROM conversation_memories 
                WHERE campaign_id = ? AND importance_score >= ?
                ORDER BY importance_score DESC, timestamp DESC 
                LIMIT ?
            ''', (campaign_id, min_importance, max_memories))
            
            rows = cursor.fetchall()
            memories = []
            
            for row in rows:
                memory = ConversationMemory(
                    memory_id=row[0],
                    campaign_id=row[1],
                    episode_id=row[2],
                    user_id=row[3],
                    character_name=row[4],
                    player_input=row[5],
                    dm_response=row[6],
                    summary=row[7],
                    entities=json.loads(row[8]) if row[8] else [],
                    importance_score=row[9],
                    emotional_context=row[10],
                    timestamp=datetime.fromisoformat(row[11]) if row[11] else None,
                    scene_context=row[12],
                    combat_context=row[13]
                )
                
                # Check relevance to current query
                if self._is_memory_relevant(memory, query):
                    memories.append(memory)
            
            # Sort by relevance and importance combined
            memories.sort(key=lambda m: m.importance_score, reverse=True)
            
            return memories[:max_memories]
            
        except Exception as e:
            print(f"❌ Error retrieving memories: {e}")
            return []
        finally:
            conn.close()
    
    async def get_npc_memory(self, campaign_id: str, npc_name: str) -> Optional[NPCMemory]:
        """Get memory for a specific NPC"""
        
        conn = self.get_db_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                SELECT * FROM npc_memories 
                WHERE campaign_id = ? AND name = ?
            ''', (campaign_id, npc_name))
            
            row = cursor.fetchone()
            if not row:
                return None
            
            return NPCMemory(
                npc_id=row[0],
                campaign_id=row[1],
                name=row[2],
                description=row[3],
                personality_summary=row[4],
                first_encountered_episode=row[5],
                last_seen_episode=row[6],
                relationship_with_party=row[7],
                current_location=row[8],
                faction_affiliation=row[9],
                knowledge_base=json.loads(row[10]) if row[10] else {},
                secrets=json.loads(row[11]) if row[11] else [],
                goals=json.loads(row[12]) if row[12] else [],
                mannerisms=row[13],
                voice_description=row[14],
                importance_level=row[15],
                status=row[16],
                notes=row[17],
                last_updated=datetime.fromisoformat(row[18]) if row[18] else None
            )
            
        except Exception as e:
            print(f"❌ Error retrieving NPC memory: {e}")
            return None
        finally:
            conn.close()
    
    async def update_npc_memory(self, campaign_id: str, npc_name: str, episode_id: int,
                              updates: Dict[str, Any]) -> NPCMemory:
        """Update or create NPC memory"""
        
        # Get existing NPC or create new one
        existing_npc = await self.get_npc_memory(campaign_id, npc_name)
        
        if existing_npc:
            # Update existing NPC
            for key, value in updates.items():
                if hasattr(existing_npc, key):
                    setattr(existing_npc, key, value)
            existing_npc.last_seen_episode = episode_id
            existing_npc.last_updated = datetime.now()
            npc = existing_npc
        else:
            # Create new NPC
            npc = NPCMemory(
                campaign_id=campaign_id,
                name=npc_name,
                first_encountered_episode=episode_id,
                last_seen_episode=episode_id
            )
            # Apply updates
            for key, value in updates.items():
                if hasattr(npc, key):
                    setattr(npc, key, value)
        
        # Store in database
        conn = self.get_db_connection()
        cursor = conn.cursor()
        
        try:
            if existing_npc:
                # Update existing
                cursor.execute('''
                    UPDATE npc_memories SET
                        description = ?, personality_summary = ?, last_seen_episode = ?,
                        relationship_with_party = ?, current_location = ?, faction_affiliation = ?,
                        knowledge_base = ?, secrets = ?, goals = ?, mannerisms = ?,
                        voice_description = ?, importance_level = ?, status = ?, notes = ?,
                        last_updated = ?
                    WHERE npc_id = ?
                ''', (
                    npc.description, npc.personality_summary, npc.last_seen_episode,
                    npc.relationship_with_party, npc.current_location, npc.faction_affiliation,
                    json.dumps(npc.knowledge_base), json.dumps(npc.secrets), json.dumps(npc.goals),
                    npc.mannerisms, npc.voice_description, npc.importance_level, npc.status,
                    npc.notes, npc.last_updated.isoformat(), npc.npc_id
                ))
            else:
                # Insert new
                cursor.execute('''
                    INSERT INTO npc_memories (
                        campaign_id, name, description, personality_summary, first_encountered_episode,
                        last_seen_episode, relationship_with_party, current_location, faction_affiliation,
                        knowledge_base, secrets, goals, mannerisms, voice_description,
                        importance_level, status, notes
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    npc.campaign_id, npc.name, npc.description, npc.personality_summary,
                    npc.first_encountered_episode, npc.last_seen_episode, npc.relationship_with_party,
                    npc.current_location, npc.faction_affiliation, json.dumps(npc.knowledge_base),
                    json.dumps(npc.secrets), json.dumps(npc.goals), npc.mannerisms,
                    npc.voice_description, npc.importance_level, npc.status, npc.notes
                ))
                npc.npc_id = cursor.lastrowid
            
            conn.commit()
            print(f"✅ Updated NPC memory for {npc_name}")
            return npc
            
        except Exception as e:
            print(f"❌ Error updating NPC memory: {e}")
            conn.rollback()
            raise e
        finally:
            conn.close()
    
    async def get_campaign_npcs(self, campaign_id: str, importance_level: str = None) -> List[NPCMemory]:
        """Get all NPCs for a campaign"""
        
        conn = self.get_db_connection()
        cursor = conn.cursor()
        
        try:
            if importance_level:
                cursor.execute('''
                    SELECT * FROM npc_memories 
                    WHERE campaign_id = ? AND importance_level = ?
                    ORDER BY last_updated DESC
                ''', (campaign_id, importance_level))
            else:
                cursor.execute('''
                    SELECT * FROM npc_memories 
                    WHERE campaign_id = ?
                    ORDER BY importance_level DESC, last_updated DESC
                ''', (campaign_id,))
            
            rows = cursor.fetchall()
            npcs = []
            
            for row in rows:
                npc = NPCMemory(
                    npc_id=row[0],
                    campaign_id=row[1],
                    name=row[2],
                    description=row[3],
                    personality_summary=row[4],
                    first_encountered_episode=row[5],
                    last_seen_episode=row[6],
                    relationship_with_party=row[7],
                    current_location=row[8],
                    faction_affiliation=row[9],
                    knowledge_base=json.loads(row[10]) if row[10] else {},
                    secrets=json.loads(row[11]) if row[11] else [],
                    goals=json.loads(row[12]) if row[12] else [],
                    mannerisms=row[13],
                    voice_description=row[14],
                    importance_level=row[15],
                    status=row[16],
                    notes=row[17],
                    last_updated=datetime.fromisoformat(row[18]) if row[18] else None
                )
                npcs.append(npc)
            
            return npcs
            
        except Exception as e:
            print(f"❌ Error retrieving campaign NPCs: {e}")
            return []
        finally:
            conn.close()
    
    async def consolidate_episode_memories(self, campaign_id: str, episode_id: int) -> Dict[str, Any]:
        """Consolidate memories from an episode"""
        
        # Get all memories from this episode
        conn = self.get_db_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                SELECT * FROM conversation_memories 
                WHERE campaign_id = ? AND episode_id = ?
                ORDER BY timestamp ASC
            ''', (campaign_id, episode_id))
            
            rows = cursor.fetchall()
            if not rows:
                return {}
            
            # Convert to memory objects
            memories = []
            for row in rows:
                memory = ConversationMemory(
                    memory_id=row[0],
                    campaign_id=row[1],
                    episode_id=row[2],
                    user_id=row[3],
                    character_name=row[4],
                    player_input=row[5],
                    dm_response=row[6],
                    summary=row[7],
                    entities=json.loads(row[8]) if row[8] else [],
                    importance_score=row[9],
                    emotional_context=row[10],
                    timestamp=datetime.fromisoformat(row[11]) if row[11] else None,
                    scene_context=row[12],
                    combat_context=row[13]
                )
                memories.append(memory)
            
            # Create episode consolidation with Claude
            consolidation = await self._create_episode_consolidation(memories)
            
            # Store consolidation
            cursor.execute('''
                INSERT OR REPLACE INTO memory_consolidation (
                    campaign_id, episode_id, episode_summary, key_events,
                    character_developments, npc_interactions, world_changes,
                    new_plot_threads, resolved_plot_threads, player_choices,
                    emotional_moments
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                campaign_id, episode_id,
                consolidation.get('episode_summary', ''),
                json.dumps(consolidation.get('key_events', [])),
                json.dumps(consolidation.get('character_developments', [])),
                json.dumps(consolidation.get('npc_interactions', [])),
                json.dumps(consolidation.get('world_changes', [])),
                json.dumps(consolidation.get('new_plot_threads', [])),
                json.dumps(consolidation.get('resolved_plot_threads', [])),
                json.dumps(consolidation.get('player_choices', [])),
                json.dumps(consolidation.get('emotional_moments', []))
            ))
            
            conn.commit()
            print(f"✅ Consolidated memories for episode {episode_id}")
            return consolidation
            
        except Exception as e:
            print(f"❌ Error consolidating episode memories: {e}")
            return {}
        finally:
            conn.close()
    
    # Private helper methods
    
    async def _analyze_conversation(self, player_input: str, dm_response: str, character_name: str) -> Dict[str, Any]:
        """Analyze conversation with Claude for memory extraction"""
        
        analysis_prompt = f"""
Analyze this D&D conversation for memory storage:

PLAYER ({character_name}): {player_input}
DM: {dm_response}

Extract the following information and respond with JSON:

{{
    "summary": "Brief 1-sentence summary of what happened",
    "entities": ["list", "of", "important", "names", "places", "items"],
    "importance_score": 0.0-1.0 (how important is this moment?),
    "emotional_context": "emotional tone/stakes",
    "scene_context": "location/environment described",
    "combat_context": "combat state if any",
    "new_npcs": ["any", "newly", "introduced", "characters"],
    "npc_interactions": [
        {{"name": "NPC Name", "interaction": "what happened", "relationship_change": "how relationship changed"}}
    ]
}}

Importance scoring:
- 0.1-0.3: Routine actions, basic interactions
- 0.4-0.6: Notable events, meaningful interactions  
- 0.7-0.9: Major plot points, character development
- 0.9-1.0: Critical moments, campaign-changing events

Be concise but capture key details for future reference.
"""
        
        try:
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self.claude_client.messages.create(
                    model="claude-sonnet-4-20250514",
                    max_tokens=500,
                    messages=[{"role": "user", "content": analysis_prompt}]
                )
            )
            
            # Extract JSON from response
            response_text = response.content[0].text.strip()
            
            # Try to extract JSON from the response
            json_start = response_text.find('{')
            json_end = response_text.rfind('}') + 1
            
            if json_start >= 0 and json_end > json_start:
                json_text = response_text[json_start:json_end]
                analysis = json.loads(json_text)
                
                # Validate importance score
                if 'importance_score' not in analysis or not isinstance(analysis['importance_score'], (int, float)):
                    analysis['importance_score'] = 0.5
                else:
                    analysis['importance_score'] = max(0.0, min(1.0, float(analysis['importance_score'])))
                
                return analysis
            else:
                # Fallback parsing
                return self._fallback_analysis(player_input, dm_response)
                
        except Exception as e:
            print(f"❌ Claude analysis error: {e}")
            return self._fallback_analysis(player_input, dm_response)
    
    def _fallback_analysis(self, player_input: str, dm_response: str) -> Dict[str, Any]:
        """Fallback analysis when Claude fails"""
        
        # Simple keyword-based analysis
        combat_keywords = ['attack', 'damage', 'hit', 'miss', 'combat', 'fight', 'initiative']
        important_keywords = ['critical', 'natural 20', 'natural 1', 'death', 'level up', 'treasure']
        
        is_combat = any(keyword in (player_input + " " + dm_response).lower() for keyword in combat_keywords)
        is_important = any(keyword in (player_input + " " + dm_response).lower() for keyword in important_keywords)
        
        # Extract potential entity names (capitalized words)
        entities = list(set(re.findall(r'\b[A-Z][a-z]+\b', player_input + " " + dm_response)))
        
        importance_score = 0.7 if is_important else (0.5 if is_combat else 0.3)
        
        return {
            "summary": f"Player action: {player_input[:50]}...",
            "entities": entities,
            "importance_score": importance_score,
            "emotional_context": "combat" if is_combat else "exploration",
            "scene_context": "",
            "combat_context": "active" if is_combat else "",
            "new_npcs": [],
            "npc_interactions": []
        }
    
    def _is_memory_relevant(self, memory: ConversationMemory, query: str) -> bool:
        """Check if a memory is relevant to the current query"""
        
        query_lower = query.lower()
        
        # Check entities
        for entity in memory.entities:
            if entity.lower() in query_lower:
                return True
        
        # Check summary
        if any(word in memory.summary.lower() for word in query_lower.split()):
            return True
        
        # Check character name
        if memory.character_name.lower() in query_lower:
            return True
        
        return False
    
    async def _extract_and_update_npcs(self, campaign_id: str, episode_id: int, analysis: Dict[str, Any]):
        """Extract and update NPC information from conversation analysis"""
        
        try:
            # Handle new NPCs
            new_npcs = analysis.get('new_npcs', [])
            for npc_name in new_npcs:
                if npc_name and len(npc_name.strip()) > 1:
                    await self.update_npc_memory(
                        campaign_id, npc_name, episode_id,
                        {"importance_level": "notable", "description": "Recently introduced NPC"}
                    )
            
            # Handle NPC interactions
            npc_interactions = analysis.get('npc_interactions', [])
            for interaction in npc_interactions:
                if isinstance(interaction, dict) and 'name' in interaction:
                    npc_name = interaction['name']
                    relationship_change = interaction.get('relationship_change', '')
                    interaction_desc = interaction.get('interaction', '')
                    
                    updates = {}
                    if relationship_change:
                        updates['relationship_with_party'] = relationship_change
                    if interaction_desc:
                        updates['notes'] = interaction_desc
                    
                    if updates:
                        await self.update_npc_memory(campaign_id, npc_name, episode_id, updates)
        
        except Exception as e:
            print(f"⚠️ Error updating NPCs from analysis: {e}")
    
    async def _create_episode_consolidation(self, memories: List[ConversationMemory]) -> Dict[str, Any]:
        """Create episode consolidation using Claude"""
        
        if not memories:
            return {}
        
        # Create summary of all interactions
        interactions_summary = []
        for memory in memories:
            interactions_summary.append(f"{memory.character_name}: {memory.player_input}")
            interactions_summary.append(f"DM: {memory.dm_response}")
        
        interactions_text = "\n".join(interactions_summary)
        
        consolidation_prompt = f"""
Analyze this D&D episode and create a consolidation summary. Here are all the interactions:

{interactions_text}

Create a JSON response with episode consolidation:

{{
    "episode_summary": "2-3 sentence summary of the entire episode",
    "key_events": ["Important events that happened", "Major discoveries", "Significant plot developments"],
    "character_developments": ["Character growth moments", "New abilities or items gained", "Personal revelations"],
    "npc_interactions": ["Important NPCs met", "Relationship changes", "NPC plot developments"],
    "world_changes": ["Changes to locations", "Political developments", "Environmental changes"],
    "new_plot_threads": ["New mysteries introduced", "New goals established", "Unresolved questions"],
    "resolved_plot_threads": ["Mysteries solved", "Goals completed", "Questions answered"],
    "player_choices": ["Major decisions made", "Important player choices", "Tactical decisions"],
    "emotional_moments": ["High-stakes moments", "Character emotional beats", "Memorable scenes"]
}}

Focus on information that will be useful for future episodes. Be concise but comprehensive.
"""
        
        try:
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self.claude_client.messages.create(
                    model="claude-sonnet-4-20250514",
                    max_tokens=800,
                    messages=[{"role": "user", "content": consolidation_prompt}]
                )
            )
            
            response_text = response.content[0].text.strip()
            
            # Extract JSON
            json_start = response_text.find('{')
            json_end = response_text.rfind('}') + 1
            
            if json_start >= 0 and json_end > json_start:
                json_text = response_text[json_start:json_end]
                return json.loads(json_text)
            else:
                return self._fallback_consolidation(memories)
                
        except Exception as e:
            print(f"❌ Episode consolidation error: {e}")
            return self._fallback_consolidation(memories)
    
    def _fallback_consolidation(self, memories: List[ConversationMemory]) -> Dict[str, Any]:
        """Fallback consolidation when Claude fails"""
        
        # Simple extraction
        all_entities = []
        high_importance_events = []
        
        for memory in memories:
            all_entities.extend(memory.entities)
            if memory.importance_score >= 0.7:
                high_importance_events.append(memory.summary)
        
        # Remove duplicates
        unique_entities = list(set(all_entities))
        
        return {
            "episode_summary": f"Episode with {len(memories)} interactions involving {', '.join(unique_entities[:5])}",
            "key_events": high_importance_events[:5],
            "character_developments": [],
            "npc_interactions": unique_entities[:10],
            "world_changes": [],
            "new_plot_threads": [],
            "resolved_plot_threads": [],
            "player_choices": [memory.summary for memory in memories if memory.importance_score >= 0.6][:3],
            "emotional_moments": [memory.summary for memory in memories if 'critical' in memory.summary.lower()][:3]
        }