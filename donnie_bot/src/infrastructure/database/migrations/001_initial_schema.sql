-- Initial database schema for Donnie the DM

-- Characters table
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

-- Episodes table
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

-- Guilds table  
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

-- Memories table
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

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_characters_guild ON characters(guild_id);
CREATE INDEX IF NOT EXISTS idx_characters_user_guild ON characters(discord_user_id, guild_id);
CREATE INDEX IF NOT EXISTS idx_episodes_guild ON episodes(guild_id);
CREATE INDEX IF NOT EXISTS idx_episodes_status ON episodes(guild_id, status);
CREATE INDEX IF NOT EXISTS idx_guilds_id ON guilds(guild_id);
CREATE INDEX IF NOT EXISTS idx_memories_guild ON memories(guild_id);
CREATE INDEX IF NOT EXISTS idx_memories_episode ON memories(guild_id, episode_number);
CREATE INDEX IF NOT EXISTS idx_memories_character ON memories(guild_id, character_name);
CREATE INDEX IF NOT EXISTS idx_memories_timestamp ON memories(guild_id, timestamp DESC);

-- Full-text search for memories
CREATE VIRTUAL TABLE IF NOT EXISTS memories_fts USING fts5(
    content, 
    content='memories',
    content_rowid='id'
);

-- Triggers to keep FTS in sync
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