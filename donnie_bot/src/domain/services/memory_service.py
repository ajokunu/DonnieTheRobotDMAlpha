"""
Memory Service - Conversation context and memory management
"""
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta

from ..entities.memory import Memory
from ..entities.episode import Episode
from ..interfaces.repositories import MemoryRepositoryInterface
from ..interfaces.ai_service import AIServiceInterface


class MemoryService:
    """Service for managing conversation memory and context"""
    
    def __init__(self,
                 memory_repo: MemoryRepositoryInterface,
                 ai_service: Optional[AIServiceInterface] = None):
        self.memory_repo = memory_repo
        self.ai_service = ai_service
    
    async def save_interaction_memory(self,
                                    guild_id: str,
                                    episode_number: int,
                                    character_name: str,
                                    player_action: str,
                                    dm_response: str) -> Memory:
        """Save a player interaction as memory"""
        
        content = f"{character_name}: {player_action}\nDM: {dm_response}"
        
        memory = Memory(
            guild_id=guild_id,
            episode_number=episode_number,
            character_name=character_name,
            content=content,
            memory_type="interaction",
            timestamp=datetime.now()
        )
        
        await self.memory_repo.save_memory(memory)
        return memory
    
    async def save_event_memory(self,
                              guild_id: str,
                              episode_number: int,
                              event_description: str,
                              memory_type: str = "event") -> Memory:
        """Save a significant event as memory"""
        
        memory = Memory(
            guild_id=guild_id,
            episode_number=episode_number,
            content=event_description,
            memory_type=memory_type,
            timestamp=datetime.now()
        )
        
        await self.memory_repo.save_memory(memory)
        return memory
    
    async def get_recent_context(self, 
                               guild_id: str,
                               limit: int = 20) -> List[Memory]:
        """Get recent memories for context"""
        return await self.memory_repo.get_recent_memories(guild_id, limit)
    
    async def search_memories(self,
                            guild_id: str,
                            query: str,
                            limit: int = 10) -> List[Memory]:
        """Search memories by content"""
        return await self.memory_repo.search_memories(guild_id, query, limit)
    
    async def get_character_memories(self,
                                   guild_id: str,
                                   character_name: str,
                                   limit: int = 50) -> List[Memory]:
        """Get memories involving a specific character"""
        all_memories = await self.memory_repo.get_recent_memories(guild_id, limit * 2)
        
        # Filter for character-specific memories
        character_memories = [
            memory for memory in all_memories
            if memory.character_name == character_name or character_name.lower() in memory.content.lower()
        ]
        
        return character_memories[:limit]
    
    async def get_episode_memories(self,
                                 guild_id: str,
                                 episode_number: int) -> List[Memory]:
        """Get all memories from a specific episode"""
        all_memories = await self.memory_repo.get_recent_memories(guild_id, limit=1000)
        
        episode_memories = [
            memory for memory in all_memories
            if memory.episode_number == episode_number
        ]
        
        return sorted(episode_memories, key=lambda m: m.timestamp)
    
    async def summarize_recent_events(self,
                                    guild_id: str,
                                    lookback_hours: int = 24) -> Optional[str]:
        """Summarize recent events using AI"""
        if not self.ai_service:
            return None
        
        # Get recent memories
        memories = await self.memory_repo.get_recent_memories(guild_id, limit=100)
        
        # Filter to recent timeframe
        cutoff_time = datetime.now() - timedelta(hours=lookback_hours)
        recent_memories = [
            memory for memory in memories
            if memory.timestamp >= cutoff_time
        ]
        
        if not recent_memories:
            return "No recent activity to summarize."
        
        # Create fake episode for summarization
        temp_episode = Episode(
            guild_id=guild_id,
            episode_number=0,
            name="Recent Events Summary"
        )
        
        return await self.ai_service.summarize_episode(temp_episode, recent_memories)
    
    async def clean_old_memories(self,
                               guild_id: str,
                               days_to_keep: int = 30) -> int:
        """Clean up old memories beyond retention period"""
        cutoff_date = datetime.now() - timedelta(days=days_to_keep)
        return await self.memory_repo.clear_old_memories(guild_id, cutoff_date)
    
    def build_context_summary(self, memories: List[Memory]) -> Dict[str, Any]:
        """Build a structured summary of memories for context"""
        if not memories:
            return {
                "total_memories": 0,
                "characters_involved": [],
                "recent_events": [],
                "summary": "No recent context available."
            }
        
        # Extract characters
        characters = set()
        events = []
        
        for memory in memories:
            if memory.character_name:
                characters.add(memory.character_name)
            
            if memory.memory_type in ["event", "combat", "important"]:
                events.append({
                    "type": memory.memory_type,
                    "content": memory.content[:100] + "..." if len(memory.content) > 100 else memory.content,
                    "timestamp": memory.timestamp.isoformat()
                })
        
        # Build summary
        summary_parts = []
        if characters:
            summary_parts.append(f"Active characters: {', '.join(sorted(characters))}")
        
        if events:
            summary_parts.append(f"Recent events: {len(events)} significant occurrences")
        
        recent_content = [m.content for m in memories[-5:]]  # Last 5 memories
        
        return {
            "total_memories": len(memories),
            "characters_involved": list(sorted(characters)),
            "recent_events": events[-10:],  # Last 10 events
            "recent_interactions": recent_content,
            "summary": "; ".join(summary_parts) if summary_parts else "Recent activity recorded."
        }
    
    def extract_important_entities(self, content: str) -> Dict[str, List[str]]:
        """Extract important entities from memory content (basic implementation)"""
        # Simple keyword extraction - could be enhanced with NLP
        
        # Common D&D locations
        locations = []
        location_keywords = ["tavern", "dungeon", "castle", "forest", "cave", "town", "city", "temple", "tower"]
        for keyword in location_keywords:
            if keyword in content.lower():
                locations.append(keyword.title())
        
        # Common D&D NPCs/creatures  
        creatures = []
        creature_keywords = ["dragon", "goblin", "orc", "wizard", "knight", "merchant", "guard", "priest"]
        for keyword in creature_keywords:
            if keyword in content.lower():
                creatures.append(keyword.title())
        
        # Common items
        items = []
        item_keywords = ["sword", "shield", "potion", "scroll", "gold", "treasure", "gem", "armor"]
        for keyword in item_keywords:
            if keyword in content.lower():
                items.append(keyword.title())
        
        return {
            "locations": locations,
            "creatures": creatures, 
            "items": items
        }
    
    async def create_memory_with_metadata(self,
                                        guild_id: str,
                                        episode_number: int,
                                        content: str,
                                        memory_type: str = "general",
                                        character_name: Optional[str] = None,
                                        importance: int = 1) -> Memory:
        """Create memory with extracted metadata"""
        
        # Extract entities
        entities = self.extract_important_entities(content)
        
        # Create memory with metadata
        memory = Memory(
            guild_id=guild_id,
            episode_number=episode_number,
            character_name=character_name,
            content=content,
            memory_type=memory_type,
            importance=importance,
            metadata=entities,
            timestamp=datetime.now()
        )
        
        await self.memory_repo.save_memory(memory)
        return memory