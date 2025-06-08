# database/database.py - UPDATED VERSION WITH current_scene COLUMN
import sqlite3
import threading
from pathlib import Path
from datetime import datetime
import json
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Database file path
DB_PATH = Path("storm_kings_thunder.db")

def get_db_connection():
    """Get a fresh database connection - FIXED to avoid stale connections"""
    try:
        # ✅ FIXED: Always create a fresh connection instead of reusing
        conn = sqlite3.connect(str(DB_PATH), check_same_thread=False, timeout=30.0)
        conn.row_factory = sqlite3.Row  # Enable dict-like access
        
        # Configure SQLite for better performance and reliability
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA journal_mode = WAL")  # Better for concurrent access
        conn.execute("PRAGMA busy_timeout = 30000")  # 30 second timeout
        
        return conn
    except Exception as e:
        logger.error(f"❌ Failed to create database connection: {e}")
        raise

def test_connection():
    """Test if database connection works - UTILITY FUNCTION"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        result = cursor.fetchone()
        conn.close()
        return result is not None
    except Exception as e:
        logger.error(f"❌ Database connection test failed: {e}")
        return False

def migrate_guild_settings_add_current_scene():
    """Migration: Add current_scene column to guild_settings if it doesn't exist"""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        logger.info("🔄 Checking if current_scene column exists in guild_settings...")
        
        # Check if column already exists
        cursor.execute("PRAGMA table_info(guild_settings)")
        columns = [row[1] for row in cursor.fetchall()]
        
        if 'current_scene' not in columns:
            logger.info("Adding current_scene column to guild_settings...")
            cursor.execute('ALTER TABLE guild_settings ADD COLUMN current_scene TEXT DEFAULT ""')
            conn.commit()
            logger.info("✅ Successfully added current_scene column to guild_settings")
        else:
            logger.info("✅ current_scene column already exists in guild_settings")
            
    except sqlite3.Error as e:
        logger.error(f"❌ Migration error: {e}")
        if conn:
            conn.rollback()
        raise
    except Exception as e:
        logger.error(f"❌ Unexpected migration error: {e}")
        raise
    finally:
        if conn:
            try:
                conn.close()
            except:
                pass

def init_database():
    """Initialize the database with all required tables"""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        logger.info("Initializing Storm King's Thunder database...")
        
        # Episodes table - Core episode management
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS episodes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id TEXT NOT NULL,
                episode_number INTEGER NOT NULL,
                name TEXT,
                start_time TIMESTAMP NOT NULL,
                end_time TIMESTAMP,
                summary TEXT,
                scene_data TEXT,
                session_history TEXT,  -- JSON array of session interactions
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(guild_id, episode_number)
            )
        ''')
        
        # Character snapshots - Track character state at different points
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS character_snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                episode_id INTEGER,
                user_id TEXT NOT NULL,
                character_name TEXT NOT NULL,
                character_data TEXT NOT NULL,  -- JSON character data
                snapshot_type TEXT NOT NULL,   -- 'episode_start', 'episode_end', 'level_up', 'manual'
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (episode_id) REFERENCES episodes (id) ON DELETE CASCADE
            )
        ''')
        
        # Character progression - Track level changes and major milestones
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS character_progression (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                character_name TEXT NOT NULL,
                episode_id INTEGER,
                old_level INTEGER,
                new_level INTEGER NOT NULL,
                progression_type TEXT NOT NULL,  -- 'level_up', 'milestone', 'reward'
                reason TEXT,
                experience_gained INTEGER DEFAULT 0,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (episode_id) REFERENCES episodes (id) ON DELETE SET NULL
            )
        ''')
        
        # Story notes - Player-added story elements (non-canonical)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS story_notes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                episode_id INTEGER,
                user_id TEXT NOT NULL,
                note_type TEXT NOT NULL,  -- 'player_note', 'dm_note', 'session_note'
                content TEXT NOT NULL,
                is_canonical BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (episode_id) REFERENCES episodes (id) ON DELETE CASCADE
            )
        ''')
        
        # Guild settings - Per-server configuration - ✅ FIXED: Added current_scene column
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS guild_settings (
                guild_id TEXT PRIMARY KEY,
                current_episode INTEGER,
                voice_speed REAL DEFAULT 1.25,
                voice_quality TEXT DEFAULT 'smart',
                tts_enabled BOOLEAN DEFAULT FALSE,
                current_scene TEXT DEFAULT '',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Create useful indexes for performance
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_episodes_guild ON episodes(guild_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_snapshots_episode ON character_snapshots(episode_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_snapshots_user ON character_snapshots(user_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_progression_user ON character_progression(user_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_progression_episode ON character_progression(episode_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_story_notes_episode ON story_notes(episode_id)')
        
        conn.commit()
        logger.info("✅ Database schema initialized successfully")
        
        # ✅ NEW: Run migration for existing databases
        logger.info("🔄 Running database migrations...")
        migrate_guild_settings_add_current_scene()
        
        # Log table creation
        tables = ['episodes', 'character_snapshots', 'character_progression', 'story_notes', 'guild_settings']
        for table in tables:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            count = cursor.fetchone()[0]
            logger.info(f"📊 Table '{table}': {count} records")
        
        # ✅ NEW: Verify current_scene column exists
        cursor.execute("PRAGMA table_info(guild_settings)")
        guild_columns = [row[1] for row in cursor.fetchall()]
        if 'current_scene' in guild_columns:
            logger.info("✅ current_scene column verified in guild_settings")
        else:
            logger.error("❌ current_scene column still missing from guild_settings!")
        
    except sqlite3.Error as e:
        logger.error(f"❌ Database initialization error: {e}")
        raise
    except Exception as e:
        logger.error(f"❌ Unexpected error during database init: {e}")
        raise
    finally:
        # ✅ FIXED: Always close the connection
        if conn:
            try:
                conn.close()
            except:
                pass

def close_database():
    """Close database connections - Updated for new connection model"""
    # ✅ FIXED: No more thread-local storage to clean up
    # Individual connections are closed when operations complete
    logger.info("🔒 Database cleanup completed")

def backup_database(backup_path: str = None):
    """Create a backup of the database"""
    conn = None
    backup_conn = None
    try:
        if backup_path is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = f"storm_kings_thunder_backup_{timestamp}.db"
        
        conn = get_db_connection()
        backup_conn = sqlite3.connect(backup_path)
        conn.backup(backup_conn)
        
        logger.info(f"✅ Database backed up to: {backup_path}")
        return backup_path
    except Exception as e:
        logger.error(f"❌ Backup failed: {e}")
        raise
    finally:
        # ✅ FIXED: Clean up connections
        if backup_conn:
            backup_conn.close()
        if conn:
            conn.close()

def get_database_stats():
    """Get database statistics for monitoring"""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        stats = {}
        
        # Table counts
        tables = ['episodes', 'character_snapshots', 'character_progression', 'story_notes', 'guild_settings']
        for table in tables:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            stats[f"{table}_count"] = cursor.fetchone()[0]
        
        # Active episodes
        cursor.execute("SELECT COUNT(*) FROM episodes WHERE end_time IS NULL")
        stats["active_episodes"] = cursor.fetchone()[0]
        
        # Unique characters
        cursor.execute("SELECT COUNT(DISTINCT user_id) FROM character_snapshots")
        stats["unique_characters"] = cursor.fetchone()[0]
        
        # Database size
        cursor.execute("SELECT page_count * page_size as size FROM pragma_page_count(), pragma_page_size()")
        result = cursor.fetchone()
        if result:
            stats["database_size_bytes"] = result[0]
        
        # ✅ NEW: Verify current_scene column
        cursor.execute("PRAGMA table_info(guild_settings)")
        guild_columns = [row[1] for row in cursor.fetchall()]
        stats["current_scene_column_exists"] = 'current_scene' in guild_columns
        
        return stats
    except Exception as e:
        logger.error(f"Error getting database stats: {e}")
        return {}
    finally:
        # ✅ FIXED: Close connection
        if conn:
            conn.close()

# Utility functions for JSON handling
def serialize_json(data):
    """Safely serialize data to JSON string"""
    if data is None:
        return None
    try:
        return json.dumps(data, default=str, ensure_ascii=False)
    except Exception as e:
        logger.error(f"JSON serialization error: {e}")
        return "{}"

def deserialize_json(json_str):
    """Safely deserialize JSON string to data"""
    if not json_str:
        return {}
    try:
        return json.loads(json_str)
    except Exception as e:
        logger.error(f"JSON deserialization error: {e}")
        return {}

# Database health check - COMPLETELY FIXED
def health_check():
    """Perform database health check with proper connection management"""
    conn = None
    try:
        # ✅ FIXED: Create fresh connection, use it, and close it
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Test basic connectivity
        cursor.execute("SELECT 1")
        result = cursor.fetchone()
        
        if result and result[0] == 1:
            # Test a real table query
            cursor.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table'")
            table_count = cursor.fetchone()[0]
            
            # ✅ NEW: Test current_scene column
            cursor.execute("PRAGMA table_info(guild_settings)")
            guild_columns = [row[1] for row in cursor.fetchall()]
            current_scene_exists = 'current_scene' in guild_columns
            
            logger.info(f"✅ Database health check passed ({table_count} tables found, current_scene: {'✅' if current_scene_exists else '❌'})")
            return True
        else:
            logger.error("❌ Database health check failed - unexpected result")
            return False
            
    except Exception as e:
        logger.error(f"❌ Database health check error: {e}")
        return False
    finally:
        # ✅ CRITICAL: Always close the connection
        if conn:
            try:
                conn.close()
            except Exception as close_error:
                logger.error(f"Error closing health check connection: {close_error}")

# ✅ NEW: Enhanced schema upgrade function for memory system
def upgrade_database_schema():
    """Upgrade database schema for enhanced memory system"""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        logger.info("🔄 Upgrading database schema for enhanced memory...")
        
        # Enhanced memory tables
        # Conversation memories - Store analyzed player interactions
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS conversation_memories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                campaign_id TEXT NOT NULL,
                episode_id INTEGER,
                user_id TEXT NOT NULL,
                character_name TEXT NOT NULL,
                player_input TEXT NOT NULL,
                dm_response TEXT NOT NULL,
                summary TEXT NOT NULL,
                importance_score REAL NOT NULL DEFAULT 0.5,
                entities TEXT,  -- JSON array of detected entities
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (episode_id) REFERENCES episodes (id) ON DELETE SET NULL
            )
        ''')
        
        # NPC memories - Track NPCs and their personalities
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS npc_memories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                campaign_id TEXT NOT NULL,
                name TEXT NOT NULL,
                description TEXT,
                personality_summary TEXT,
                relationships TEXT,  -- JSON object with character relationships
                current_location TEXT,
                faction_affiliation TEXT,
                importance_level TEXT DEFAULT 'minor',
                first_introduced_episode INTEGER,
                last_seen_episode INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(campaign_id, name)
            )
        ''')
        
        # World state - Track locations and faction status
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS world_state (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                campaign_id TEXT NOT NULL,
                location_name TEXT NOT NULL,
                state_type TEXT NOT NULL,  -- 'location', 'faction', 'event'
                current_state TEXT NOT NULL,
                last_changed_episode INTEGER,
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(campaign_id, location_name, state_type)
            )
        ''')
        
        # Plot threads - Track ongoing story elements
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS plot_threads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                campaign_id TEXT NOT NULL,
                thread_name TEXT NOT NULL,
                description TEXT NOT NULL,
                status TEXT DEFAULT 'active',  -- 'active', 'resolved', 'abandoned'
                importance TEXT DEFAULT 'medium',  -- 'low', 'medium', 'high', 'critical'
                introduced_episode INTEGER,
                resolved_episode INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Memory consolidation - Episode summaries and compressed memories
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS memory_consolidation (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                campaign_id TEXT NOT NULL,
                episode_id INTEGER NOT NULL,
                summary TEXT NOT NULL,
                key_events TEXT,  -- JSON array of key events
                character_developments TEXT,  -- JSON object with character changes
                npc_interactions TEXT,  -- JSON array of significant NPC interactions
                plot_progression TEXT,  -- JSON object with plot thread updates
                world_changes TEXT,  -- JSON object with world state changes
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (episode_id) REFERENCES episodes (id) ON DELETE CASCADE,
                UNIQUE(campaign_id, episode_id)
            )
        ''')
        
        # Campaign constants - Store campaign-specific data
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS campaign_constants (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                setting_name TEXT NOT NULL,
                constant_type TEXT NOT NULL,
                name TEXT NOT NULL,
                description TEXT,
                data TEXT,  -- JSON data
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(setting_name, constant_type, name)
            )
        ''')
        
        # Create indexes for memory system performance
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_conversation_campaign ON conversation_memories(campaign_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_conversation_episode ON conversation_memories(episode_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_conversation_importance ON conversation_memories(importance_score)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_conversation_timestamp ON conversation_memories(timestamp)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_npc_campaign ON npc_memories(campaign_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_world_campaign ON world_state(campaign_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_plot_campaign ON plot_threads(campaign_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_plot_status ON plot_threads(status)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_consolidation_campaign ON memory_consolidation(campaign_id)')
        
        # Insert Storm King's Thunder constants
        cursor.execute('''
            INSERT OR IGNORE INTO campaign_constants 
            (setting_name, constant_type, name, description, data) 
            VALUES (?, ?, ?, ?, ?)
        ''', (
            "Storm King's Thunder",
            "campaign_setting",
            "main_setting",
            "Core campaign information for Storm King's Thunder",
            serialize_json({
                "ordning_collapsed": True,
                "giant_types": ["cloud", "storm", "fire", "frost", "stone", "hill"],
                "main_locations": ["Nightstone", "Triboar", "Bryn Shander", "Waterdeep"],
                "key_npcs": ["Zephyros", "Harshnag", "Duke Zalto", "Princess Serissa"]
            })
        ))
        
        conn.commit()
        
        # Verify new tables
        new_tables = [
            'conversation_memories', 'npc_memories', 'world_state', 
            'plot_threads', 'memory_consolidation', 'campaign_constants'
        ]
        
        for table in new_tables:
            cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table}'")
            if cursor.fetchone():
                logger.info(f"✅ Table {table}: created")
            else:
                logger.error(f"❌ Table {table}: failed to create")
        
        logger.info("✅ Enhanced memory schema upgrade completed successfully")
        
    except Exception as e:
        logger.error(f"❌ Schema upgrade failed: {e}")
        raise
    finally:
        if conn:
            conn.close()