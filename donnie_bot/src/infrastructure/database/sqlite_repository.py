"""
SQLite repository implementations
"""
import aiosqlite
import json
from typing import List, Optional, Dict, Any
from datetime import datetime
from pathlib import Path

from ...domain.entities import Character, Episode, Guild, Memory
from ...domain.interfaces.repositories import (
    CharacterRepositoryInterface,
    EpisodeRepositoryInterface, 
    GuildRepositoryInterface,
    MemoryRepositoryInterface
)


class SQLiteBaseRepository:
    """Base SQLite repository with common functionality"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._ensure_db_directory()
    
    def _ensure_db_directory(self):
        """Ensure database directory exists"""
        db_dir = Path(self.db_path).parent
        db_dir.mkdir(parents=True, exist_ok=True)
    
    async def get_connection(self) -> aiosqlite.Connection:
        """Get database connection"""
        return await aiosqlite.connect(self.db_path)
    
    async def execute_schema(self, schema_sql: str):
        """Execute schema SQL"""
        async with await self.get_connection() as db:
            await db.executescript(schema_sql)
            await db.commit()


class SQLiteCharacterRepository(SQLiteBaseRepository, CharacterRepositoryInterface):
    """SQLite implementation of character repository"""
    
    async def initialize(self):
        """Initialize character table"""
        schema = """
        CREATE TABLE IF NOT EXISTS characters (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            discord_user_id TEXT NOT NULL,
            guild_id TEXT NOT NULL,
            name TEXT NOT NULL,
            player_name TEXT NOT NULL,
            race TEXT NOT NULL,
            character_class TEXT NOT NULL,
            level INTEGER NOT NULL DEFAULT 1,
            background TEXT DEFAULT '',
            ability_scores TEXT NOT NULL,  -- JSON
            current_hp INTEGER,
            max_hp INTEGER,
            equipment TEXT DEFAULT '[]',  -- JSON array
            spells TEXT DEFAULT '[]',     -- JSON array
            affiliations TEXT DEFAULT '[]',  -- JSON array
            personality_traits TEXT DEFAULT '[]',  -- JSON array
            created_at TEXT,
            last_updated TEXT,
            UNIQUE(discord_user_id, guild_id)
        );
        
        CREATE INDEX IF NOT EXISTS idx_characters_guild 
        ON characters(guild_id);
        
        CREATE INDEX IF NOT EXISTS idx_characters_user_guild 
        ON characters(discord_user_id, guild_id);
        """
        
        await self.execute_schema(schema)
    
    async def get_character(self, user_id: str, guild_id: str) -> Optional[Character]:
        """Get character by user and guild ID"""
        async with await self.get_connection() as db:
            async with db.execute(
                "SELECT * FROM characters WHERE discord_user_id = ? AND guild_id = ?",
                (user_id, guild_id)
            ) as cursor:
                row = await cursor.fetchone()
                
                if not row:
                    return None
                
                return self._row_to_character(row)
    
    async def save_character(self, character: Character) -> None:
        """Save or update a character"""
        character.last_updated = datetime.now().isoformat()
        
        async with await self.get_connection() as db:
            # Check if character exists
            existing = await self.get_character(character.discord_user_id, character.guild_id)
            
            if existing:
                # Update existing
                await db.execute("""
                    UPDATE characters SET
                        name = ?, player_name = ?, race = ?, character_class = ?,
                        level = ?, background = ?, ability_scores = ?,
                        current_hp = ?, max_hp = ?, equipment = ?, spells = ?,
                        affiliations = ?, personality_traits = ?, last_updated = ?
                    WHERE discord_user_id = ? AND guild_id = ?
                """, (
                    character.name, character.player_name, character.race.value,
                    character.character_class.value, character.level, character.background,
                    json.dumps(character.ability_scores.__dict__), character.current_hp,
                    character.max_hp, json.dumps(character.equipment),
                    json.dumps(character.spells), json.dumps(character.affiliations),
                    json.dumps(character.personality_traits), character.last_updated,
                    character.discord_user_id, character.guild_id
                ))
            else:
                # Insert new
                await db.execute("""
                    INSERT INTO characters (
                        discord_user_id, guild_id, name, player_name, race, character_class,
                        level, background, ability_scores, current_hp, max_hp,
                        equipment, spells, affiliations, personality_traits,
                        created_at, last_updated
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    character.discord_user_id, character.guild_id, character.name,
                    character.player_name, character.race.value, character.character_class.value,
                    character.level, character.background, json.dumps(character.ability_scores.__dict__),
                    character.current_hp, character.max_hp, json.dumps(character.equipment),
                    json.dumps(character.spells), json.dumps(character.affiliations),
                    json.dumps(character.personality_traits), character.created_at,
                    character.last_updated
                ))
            
            await db.commit()
    
    async def delete_character(self, user_id: str, guild_id: str) -> bool:
        """Delete a character"""
        async with await self.get_connection() as db:
            cursor = await db.execute(
                "DELETE FROM characters WHERE discord_user_id = ? AND guild_id = ?",
                (user_id, guild_id)
            )
            await db.commit()
            return cursor.rowcount > 0
    
    async def get_guild_characters(self, guild_id: str) -> List[Character]:
        """Get all characters in a guild"""
        async with await self.get_connection() as db:
            async with db.execute(
                "SELECT * FROM characters WHERE guild_id = ? ORDER BY name",
                (guild_id,)
            ) as cursor:
                rows = await cursor.fetchall()
                return [self._row_to_character(row) for row in rows]
    
    def _row_to_character(self, row) -> Character:
        """Convert database row to Character entity"""
        from ...domain.entities.character import Race, CharacterClass, AbilityScores
        
        # Get column names from cursor description would be better, but for simplicity:
        columns = [
            'id', 'discord_user_id', 'guild_id', 'name', 'player_name', 'race',
            'character_class', 'level', 'background', 'ability_scores', 'current_hp',
            'max_hp', 'equipment', 'spells', 'affiliations', 'personality_traits',
            'created_at', 'last_updated'
        ]
        
        data = dict(zip(columns, row))
        
        # Parse JSON fields
        ability_scores_data = json.loads(data['ability_scores'])
        ability_scores = AbilityScores(**ability_scores_data)
        
        return Character(
            name=data['name'],
            player_name=data['player_name'],
            discord_user_id=data['discord_user_id'],
            race=Race(data['race']),
            character_class=CharacterClass(data['character_class']),
            level=data['level'],
            background=data['background'],
            ability_scores=ability_scores,
            current_hp=data['current_hp'],
            max_hp=data['max_hp'],
            equipment=json.loads(data['equipment']),
            spells=json.loads(data['spells']),
            affiliations=json.loads(data['affiliations']),
            personality_traits=json.loads(data['personality_traits']),
            created_at=data['created_at'],
            last_updated=data['last_updated']
        )


class SQLiteEpisodeRepository(SQLiteBaseRepository, EpisodeRepositoryInterface):
    """SQLite implementation of episode repository"""
    
    async def initialize(self):
        """Initialize episode tables"""
        schema = """
        CREATE TABLE IF NOT EXISTS episodes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            guild_id TEXT NOT NULL,
            episode_number INTEGER NOT NULL,
            name TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'planned',
            start_time TEXT,
            end_time TEXT,
            opening_scene TEXT DEFAULT '',
            closing_scene TEXT DEFAULT '',
            summary TEXT DEFAULT '',
            interactions TEXT DEFAULT '[]',  -- JSON array
            character_snapshots TEXT DEFAULT '{}',  -- JSON object
            created_at TEXT,
            updated_at TEXT,
            UNIQUE(guild_id, episode_number)
        );
        
        CREATE INDEX IF NOT EXISTS idx_episodes_guild 
        ON episodes(guild_id);
        
        CREATE INDEX IF NOT EXISTS idx_episodes_status 
        ON episodes(guild_id, status);
        """
        
        await self.execute_schema(schema)
    
    async def get_current_episode(self, guild_id: str) -> Optional[Episode]:
        """Get the currently active or most recent episode"""
        async with await self.get_connection() as db:
            # First try to get active episode
            async with db.execute(
                "SELECT * FROM episodes WHERE guild_id = ? AND status = 'active' ORDER BY episode_number DESC LIMIT 1",
                (guild_id,)
            ) as cursor:
                row = await cursor.fetchone()
                
                if row:
                    return self._row_to_episode(row)
            
            # If no active episode, get the most recent one
            async with db.execute(
                "SELECT * FROM episodes WHERE guild_id = ? ORDER BY episode_number DESC LIMIT 1",
                (guild_id,)
            ) as cursor:
                row = await cursor.fetchone()
                
                if row:
                    return self._row_to_episode(row)
                
                return None
    
    async def save_episode(self, episode: Episode) -> None:
        """Save or update an episode"""
        episode.updated_at = datetime.now()
        
        async with await self.get_connection() as db:
            # Check if episode exists
            async with db.execute(
                "SELECT id FROM episodes WHERE guild_id = ? AND episode_number = ?",
                (episode.guild_id, episode.episode_number)
            ) as cursor:
                existing = await cursor.fetchone()
            
            if existing:
                # Update existing
                await db.execute("""
                    UPDATE episodes SET
                        name = ?, status = ?, start_time = ?, end_time = ?,
                        opening_scene = ?, closing_scene = ?, summary = ?,
                        interactions = ?, character_snapshots = ?, updated_at = ?
                    WHERE guild_id = ? AND episode_number = ?
                """, (
                    episode.name, episode.status.value,
                    episode.start_time.isoformat() if episode.start_time else None,
                    episode.end_time.isoformat() if episode.end_time else None,
                    episode.opening_scene, episode.closing_scene, episode.summary,
                    json.dumps([interaction.to_dict() for interaction in episode.interactions]),
                    json.dumps(episode.character_snapshots),
                    episode.updated_at.isoformat(),
                    episode.guild_id, episode.episode_number
                ))
            else:
                # Insert new
                await db.execute("""
                    INSERT INTO episodes (
                        guild_id, episode_number, name, status, start_time, end_time,
                        opening_scene, closing_scene, summary, interactions,
                        character_snapshots, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    episode.guild_id, episode.episode_number, episode.name, episode.status.value,
                    episode.start_time.isoformat() if episode.start_time else None,
                    episode.end_time.isoformat() if episode.end_time else None,
                    episode.opening_scene, episode.closing_scene, episode.summary,
                    json.dumps([interaction.to_dict() for interaction in episode.interactions]),
                    json.dumps(episode.character_snapshots),
                    episode.created_at.isoformat() if episode.created_at else None,
                    episode.updated_at.isoformat()
                ))
            
            await db.commit()
    
    async def get_episode_history(self, guild_id: str, limit: int = 10) -> List[Episode]:
        """Get episode history for a guild"""
        async with await self.get_connection() as db:
            async with db.execute(
                "SELECT * FROM episodes WHERE guild_id = ? ORDER BY episode_number DESC LIMIT ?",
                (guild_id, limit)
            ) as cursor:
                rows = await cursor.fetchall()
                return [self._row_to_episode(row) for row in rows]
    
    async def end_episode(self, episode_id: str) -> None:
        """Mark an episode as ended - this is a convenience method"""
        # Note: episode_id would need to be tracked differently for this to work
        # For now, we'll implement it through the save_episode method
        pass
    
    def _row_to_episode(self, row) -> Episode:
        """Convert database row to Episode entity"""
        from ...domain.entities.episode import EpisodeStatus, SessionInteraction
        
        columns = [
            'id', 'guild_id', 'episode_number', 'name', 'status', 'start_time',
            'end_time', 'opening_scene', 'closing_scene', 'summary', 'interactions',
            'character_snapshots', 'created_at', 'updated_at'
        ]
        
        data = dict(zip(columns, row))
        
        # Parse JSON fields
        interactions_data = json.loads(data['interactions'])
        interactions = [SessionInteraction.from_dict(interaction_data) for interaction_data in interactions_data]
        
        character_snapshots = json.loads(data['character_snapshots'])
        
        return Episode(
            guild_id=data['guild_id'],
            episode_number=data['episode_number'],
            name=data['name'],
            status=EpisodeStatus(data['status']),
            start_time=datetime.fromisoformat(data['start_time']) if data['start_time'] else None,
            end_time=datetime.fromisoformat(data['end_time']) if data['end_time'] else None,
            opening_scene=data['opening_scene'],
            closing_scene=data['closing_scene'],
            summary=data['summary'],
            interactions=interactions,
            character_snapshots=character_snapshots,
            created_at=datetime.fromisoformat(data['created_at']) if data['created_at'] else None,
            updated_at=datetime.fromisoformat(data['updated_at']) if data['updated_at'] else None
        )


class SQLiteGuildRepository(SQLiteBaseRepository, GuildRepositoryInterface):
    """SQLite implementation of guild repository"""
    
    async def initialize(self):
        """Initialize guild table"""
        schema = """
        CREATE TABLE IF NOT EXISTS guilds (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            guild_id TEXT UNIQUE NOT NULL,
            name TEXT DEFAULT '',
            current_episode_number INTEGER DEFAULT 0,
            current_scene TEXT DEFAULT '',
            voice_settings TEXT DEFAULT '{}',  -- JSON
            created_at TEXT,
            updated_at TEXT
        );
        
        CREATE INDEX IF NOT EXISTS idx_guilds_id 
        ON guilds(guild_id);
        """
        
        await self.execute_schema(schema)
    
    async def get_guild_settings(self, guild_id: str) -> Optional[Guild]:
        """Get guild settings"""
        async with await self.get_connection() as db:
            async with db.execute(
                "SELECT * FROM guilds WHERE guild_id = ?",
                (guild_id,)
            ) as cursor:
                row = await cursor.fetchone()
                
                if not row:
                    return None
                
                return self._row_to_guild(row)
    
    async def save_guild_settings(self, guild: Guild) -> None:
        """Save or update guild settings"""
        guild.updated_at = datetime.now()
        
        async with await self.get_connection() as db:
            # Check if guild exists
            existing = await self.get_guild_settings(guild.guild_id)
            
            if existing:
                # Update existing
                await db.execute("""
                    UPDATE guilds SET
                        name = ?, current_episode_number = ?, current_scene = ?,
                        voice_settings = ?, updated_at = ?
                    WHERE guild_id = ?
                """, (
                    guild.name, guild.current_episode_number, guild.current_scene,
                    json.dumps(guild.voice_settings.to_dict()),
                    guild.updated_at.isoformat(), guild.guild_id
                ))
            else:
                # Insert new
                await db.execute("""
                    INSERT INTO guilds (
                        guild_id, name, current_episode_number, current_scene,
                        voice_settings, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    guild.guild_id, guild.name, guild.current_episode_number,
                    guild.current_scene, json.dumps(guild.voice_settings.to_dict()),
                    guild.created_at.isoformat() if guild.created_at else None,
                    guild.updated_at.isoformat()
                ))
            
            await db.commit()
    
    def _row_to_guild(self, row) -> Guild:
        """Convert database row to Guild entity"""
        from ...domain.entities.guild import VoiceSettings
        
        columns = [
            'id', 'guild_id', 'name', 'current_episode_number', 'current_scene',
            'voice_settings', 'created_at', 'updated_at'
        ]
        
        data = dict(zip(columns, row))
        
        # Parse JSON fields
        voice_settings_data = json.loads(data['voice_settings'])
        voice_settings = VoiceSettings.from_dict(voice_settings_data)
        
        return Guild(
            guild_id=data['guild_id'],
            name=data['name'],
            current_episode_number=data['current_episode_number'],
            current_scene=data['current_scene'],
            voice_settings=voice_settings,
            created_at=datetime.fromisoformat(data['created_at']) if data['created_at'] else None,
            updated_at=datetime.fromisoformat(data['updated_at']) if data['updated_at'] else None
        )


class SQLiteMemoryRepository(SQLiteBaseRepository, MemoryRepositoryInterface):
    """SQLite implementation of memory repository"""
    
    async def initialize(self):
        """Initialize memory table"""
        schema = """
        CREATE TABLE IF NOT EXISTS memories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            guild_id TEXT NOT NULL,
            episode_number INTEGER NOT NULL,
            character_name TEXT,
            content TEXT NOT NULL,
            memory_type TEXT DEFAULT 'general',
            importance INTEGER DEFAULT 1,
            metadata TEXT DEFAULT '{}',  -- JSON
            timestamp TEXT NOT NULL
        );
        
        CREATE INDEX IF NOT EXISTS idx_memories_guild 
        ON memories(guild_id);
        
        CREATE INDEX IF NOT EXISTS idx_memories_episode 
        ON memories(guild_id, episode_number);
        
        CREATE INDEX IF NOT EXISTS idx_memories_character 
        ON memories(guild_id, character_name);
        
        CREATE INDEX IF NOT EXISTS idx_memories_timestamp 
        ON memories(guild_id, timestamp DESC);
        
        -- Full-text search index for content
        CREATE VIRTUAL TABLE IF NOT EXISTS memories_fts USING fts5(
            content, 
            content='memories',
            content_rowid='id'
        );
        
        -- Trigger to keep FTS in sync
        CREATE TRIGGER IF NOT EXISTS memories_fts_insert AFTER INSERT ON memories BEGIN
            INSERT INTO memories_fts(rowid, content) VALUES (new.id, new.content);
        END;
        
        CREATE TRIGGER IF NOT EXISTS memories_fts_delete AFTER DELETE ON memories BEGIN
            INSERT INTO memories_fts(memories_fts, rowid, content) VALUES ('delete', old.id, old.content);
        END;
        
        CREATE TRIGGER IF NOT EXISTS memories_fts_update AFTER UPDATE ON memories BEGIN
            INSERT INTO memories_fts(memories_fts, rowid, content) VALUES ('delete', old.id, old.content);
            INSERT INTO memories_fts(rowid, content) VALUES (new.id, new.content);
        END;
        """
        
        await self.execute_schema(schema)
    
    async def save_memory(self, memory: Memory) -> None:
        """Save a memory entry"""
        async with await self.get_connection() as db:
            await db.execute("""
                INSERT INTO memories (
                    guild_id, episode_number, character_name, content,
                    memory_type, importance, metadata, timestamp
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                memory.guild_id, memory.episode_number, memory.character_name,
                memory.content, memory.memory_type, memory.importance,
                json.dumps(memory.metadata), memory.timestamp.isoformat()
            ))
            await db.commit()
    
    async def get_recent_memories(self, guild_id: str, limit: int = 50) -> List[Memory]:
        """Get recent memories for context"""
        async with await self.get_connection() as db:
            async with db.execute("""
                SELECT * FROM memories 
                WHERE guild_id = ? 
                ORDER BY timestamp DESC 
                LIMIT ?
            """, (guild_id, limit)) as cursor:
                rows = await cursor.fetchall()
                return [self._row_to_memory(row) for row in rows]
    
    async def search_memories(self, guild_id: str, query: str, limit: int = 10) -> List[Memory]:
        """Search memories by content using FTS"""
        async with await self.get_connection() as db:
            async with db.execute("""
                SELECT m.* FROM memories m
                JOIN memories_fts fts ON m.id = fts.rowid
                WHERE m.guild_id = ? AND memories_fts MATCH ?
                ORDER BY rank
                LIMIT ?
            """, (guild_id, query, limit)) as cursor:
                rows = await cursor.fetchall()
                return [self._row_to_memory(row) for row in rows]
    
    async def clear_old_memories(self, guild_id: str, older_than: datetime) -> int:
        """Clear memories older than specified date"""
        async with await self.get_connection() as db:
            cursor = await db.execute("""
                DELETE FROM memories 
                WHERE guild_id = ? AND timestamp < ?
            """, (guild_id, older_than.isoformat()))
            await db.commit()
            return cursor.rowcount
    
    def _row_to_memory(self, row) -> Memory:
        """Convert database row to Memory entity"""
        columns = [
            'id', 'guild_id', 'episode_number', 'character_name', 'content',
            'memory_type', 'importance', 'metadata', 'timestamp'
        ]
        
        data = dict(zip(columns, row))
        
        # Parse JSON metadata
        metadata = json.loads(data['metadata'])
        
        return Memory(
            guild_id=data['guild_id'],
            episode_number=data['episode_number'],
            character_name=data['character_name'],
            content=data['content'],
            memory_type=data['memory_type'],
            importance=data['importance'],
            metadata=metadata,
            timestamp=datetime.fromisoformat(data['timestamp'])
        )


# Repository factory for dependency injection
class SQLiteRepositoryFactory:
    """Factory for creating SQLite repositories"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
    
    async def create_character_repository(self) -> SQLiteCharacterRepository:
        """Create and initialize character repository"""
        repo = SQLiteCharacterRepository(self.db_path)
        await repo.initialize()
        return repo
    
    async def create_episode_repository(self) -> SQLiteEpisodeRepository:
        """Create and initialize episode repository"""
        repo = SQLiteEpisodeRepository(self.db_path)
        await repo.initialize()
        return repo
    
    async def create_guild_repository(self) -> SQLiteGuildRepository:
        """Create and initialize guild repository"""
        repo = SQLiteGuildRepository(self.db_path)
        await repo.initialize()
        return repo
    
    async def create_memory_repository(self) -> SQLiteMemoryRepository:
        """Create and initialize memory repository"""
        repo = SQLiteMemoryRepository(self.db_path)
        await repo.initialize()
        return repo