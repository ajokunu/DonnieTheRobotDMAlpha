# database/database.py
import sqlite3
import threading
from pathlib import Path
from datetime import datetime
import json
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Thread-local storage for database connections
_local = threading.local()

def get_db_connection():
    """Get thread-local database connection"""
    if not hasattr(_local, 'connection'):
        db_path = Path("storm_kings_thunder.db")
        _local.connection = sqlite3.connect(str(db_path), check_same_thread=False)
        _local.connection.row_factory = sqlite3.Row  # Enable dict-like access
    return _local.connection

def init_database():
    """Initialize the database with all required tables"""
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
        
        # Guild settings - Per-server configuration
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS guild_settings (
                guild_id TEXT PRIMARY KEY,
                current_episode INTEGER,
                voice_speed REAL DEFAULT 1.25,
                voice_quality TEXT DEFAULT 'smart',
                tts_enabled BOOLEAN DEFAULT FALSE,
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
        
        # Log table creation
        tables = ['episodes', 'character_snapshots', 'character_progression', 'story_notes', 'guild_settings']
        for table in tables:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            count = cursor.fetchone()[0]
            logger.info(f"📊 Table '{table}': {count} records")
        
    except sqlite3.Error as e:
        logger.error(f"❌ Database initialization error: {e}")
        raise
    except Exception as e:
        logger.error(f"❌ Unexpected error during database init: {e}")
        raise

def close_database():
    """Close the database connection"""
    if hasattr(_local, 'connection'):
        try:
            _local.connection.close()
            logger.info("🔒 Database connection closed")
        except Exception as e:
            logger.error(f"Error closing database: {e}")
        finally:
            if hasattr(_local, 'connection'):
                delattr(_local, 'connection')

def backup_database(backup_path: str = None):
    """Create a backup of the database"""
    try:
        if backup_path is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = f"storm_kings_thunder_backup_{timestamp}.db"
        
        conn = get_db_connection()
        backup_conn = sqlite3.connect(backup_path)
        conn.backup(backup_conn)
        backup_conn.close()
        
        logger.info(f"✅ Database backed up to: {backup_path}")
        return backup_path
    except Exception as e:
        logger.error(f"❌ Backup failed: {e}")
        raise

def get_database_stats():
    """Get database statistics for monitoring"""
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
        
        return stats
    except Exception as e:
        logger.error(f"Error getting database stats: {e}")
        return {}

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

# Database health check
def health_check():
    """Perform database health check"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Test basic connectivity
        cursor.execute("SELECT 1")
        result = cursor.fetchone()
        
        if result and result[0] == 1:
            logger.info("✅ Database health check passed")
            return True
        else:
            logger.error("❌ Database health check failed")
            return False
            
    except Exception as e:
        logger.error(f"❌ Database health check error: {e}")
        return False