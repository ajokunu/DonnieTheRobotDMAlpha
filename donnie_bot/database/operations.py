# database/operations.py
import sqlite3
import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from .database import get_db_connection, serialize_json, deserialize_json

logger = logging.getLogger(__name__)

@dataclass
class Episode:
    """Episode data class"""
    id: Optional[int] = None
    guild_id: str = ""
    episode_number: int = 0
    name: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    summary: Optional[str] = None
    scene_data: Optional[str] = None
    session_history: Optional[List[Dict]] = None
    created_at: Optional[datetime] = None

@dataclass
class CharacterSnapshot:
    """Character snapshot data class"""
    id: Optional[int] = None
    episode_id: Optional[int] = None
    user_id: str = ""
    character_name: str = ""
    character_data: Dict = None
    snapshot_type: str = ""
    notes: Optional[str] = None
    created_at: Optional[datetime] = None

@dataclass
class CharacterProgression:
    """Character progression data class"""
    id: Optional[int] = None
    user_id: str = ""
    character_name: str = ""
    episode_id: Optional[int] = None
    old_level: Optional[int] = None
    new_level: int = 1
    progression_type: str = ""
    reason: Optional[str] = None
    experience_gained: int = 0
    timestamp: Optional[datetime] = None

class DatabaseOperationError(Exception):
    """Custom exception for database operations"""
    pass

class EpisodeOperations:
    """Handle all episode-related database operations"""
    
    @staticmethod
    def create_episode(guild_id: str, episode_number: int, name: str = None, 
                      scene_data: str = None) -> Episode:
        """Create a new episode"""
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            start_time = datetime.now()
            
            cursor.execute('''
                INSERT INTO episodes (guild_id, episode_number, name, start_time, scene_data, session_history)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (guild_id, episode_number, name, start_time, scene_data, serialize_json([])))
            
            episode_id = cursor.lastrowid
            conn.commit()
            
            logger.info(f"✅ Created episode {episode_number} for guild {guild_id}")
            
            return Episode(
                id=episode_id,
                guild_id=guild_id,
                episode_number=episode_number,
                name=name,
                start_time=start_time,
                scene_data=scene_data,
                session_history=[]
            )
            
        except sqlite3.IntegrityError as e:
            if "UNIQUE constraint failed" in str(e):
                raise DatabaseOperationError(f"Episode {episode_number} already exists for this server")
            raise DatabaseOperationError(f"Episode creation failed: {e}")
        except Exception as e:
            logger.error(f"❌ Error creating episode: {e}")
            raise DatabaseOperationError(f"Failed to create episode: {e}")
    
    @staticmethod
    def get_episode(episode_id: int) -> Optional[Episode]:
        """Get episode by ID"""
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            cursor.execute('SELECT * FROM episodes WHERE id = ?', (episode_id,))
            row = cursor.fetchone()
            
            if not row:
                return None
            
            return Episode(
                id=row['id'],
                guild_id=row['guild_id'],
                episode_number=row['episode_number'],
                name=row['name'],
                start_time=datetime.fromisoformat(row['start_time']) if row['start_time'] else None,
                end_time=datetime.fromisoformat(row['end_time']) if row['end_time'] else None,
                summary=row['summary'],
                scene_data=row['scene_data'],
                session_history=deserialize_json(row['session_history']),
                created_at=datetime.fromisoformat(row['created_at']) if row['created_at'] else None
            )
            
        except Exception as e:
            logger.error(f"❌ Error getting episode {episode_id}: {e}")
            raise DatabaseOperationError(f"Failed to get episode: {e}")
    
    @staticmethod
    def get_current_episode(guild_id: str) -> Optional[Episode]:
        """Get the current active episode for a guild"""
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT * FROM episodes 
                WHERE guild_id = ? AND end_time IS NULL 
                ORDER BY episode_number DESC 
                LIMIT 1
            ''', (guild_id,))
            
            row = cursor.fetchone()
            if not row:
                return None
            
            return Episode(
                id=row['id'],
                guild_id=row['guild_id'],
                episode_number=row['episode_number'],
                name=row['name'],
                start_time=datetime.fromisoformat(row['start_time']) if row['start_time'] else None,
                end_time=None,
                summary=row['summary'],
                scene_data=row['scene_data'],
                session_history=deserialize_json(row['session_history']),
                created_at=datetime.fromisoformat(row['created_at']) if row['created_at'] else None
            )
            
        except Exception as e:
            logger.error(f"❌ Error getting current episode for guild {guild_id}: {e}")
            raise DatabaseOperationError(f"Failed to get current episode: {e}")
    
    @staticmethod
    def end_episode(episode_id: int, summary: str = None) -> bool:
        """End an episode"""
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            end_time = datetime.now()
            
            cursor.execute('''
                UPDATE episodes 
                SET end_time = ?, summary = ? 
                WHERE id = ? AND end_time IS NULL
            ''', (end_time, summary, episode_id))
            
            if cursor.rowcount == 0:
                logger.warning(f"No active episode found with ID {episode_id}")
                return False
            
            conn.commit()
            logger.info(f"✅ Episode {episode_id} ended successfully")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error ending episode {episode_id}: {e}")
            raise DatabaseOperationError(f"Failed to end episode: {e}")
    
    @staticmethod
    def update_session_history(episode_id: int, session_history: List[Dict]) -> bool:
        """Update episode's session history"""
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                UPDATE episodes 
                SET session_history = ? 
                WHERE id = ?
            ''', (serialize_json(session_history), episode_id))
            
            conn.commit()
            return cursor.rowcount > 0
            
        except Exception as e:
            logger.error(f"❌ Error updating session history for episode {episode_id}: {e}")
            raise DatabaseOperationError(f"Failed to update session history: {e}")
    
    @staticmethod
    def get_episode_history(guild_id: str, limit: int = 10) -> List[Episode]:
        """Get episode history for a guild"""
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT * FROM episodes 
                WHERE guild_id = ? 
                ORDER BY episode_number DESC 
                LIMIT ?
            ''', (guild_id, limit))
            
            episodes = []
            for row in cursor.fetchall():
                episodes.append(Episode(
                    id=row['id'],
                    guild_id=row['guild_id'],
                    episode_number=row['episode_number'],
                    name=row['name'],
                    start_time=datetime.fromisoformat(row['start_time']) if row['start_time'] else None,
                    end_time=datetime.fromisoformat(row['end_time']) if row['end_time'] else None,
                    summary=row['summary'],
                    scene_data=row['scene_data'],
                    session_history=deserialize_json(row['session_history']),
                    created_at=datetime.fromisoformat(row['created_at']) if row['created_at'] else None
                ))
            
            return episodes
            
        except Exception as e:
            logger.error(f"❌ Error getting episode history for guild {guild_id}: {e}")
            raise DatabaseOperationError(f"Failed to get episode history: {e}")
    
    @staticmethod
    def get_last_completed_episode(guild_id: str) -> Optional[Episode]:
        """Get the most recently completed episode for a guild"""
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT * FROM episodes 
                WHERE guild_id = ? AND end_time IS NOT NULL
                ORDER BY end_time DESC 
                LIMIT 1
            ''', (guild_id,))
            
            row = cursor.fetchone()
            if not row:
                return None
            
            return Episode(
                id=row['id'],
                guild_id=row['guild_id'],
                episode_number=row['episode_number'],
                name=row['name'],
                start_time=datetime.fromisoformat(row['start_time']) if row['start_time'] else None,
                end_time=datetime.fromisoformat(row['end_time']) if row['end_time'] else None,
                summary=row['summary'],
                scene_data=row['scene_data'],
                session_history=deserialize_json(row['session_history']),
                created_at=datetime.fromisoformat(row['created_at']) if row['created_at'] else None
            )
            
        except Exception as e:
            logger.error(f"❌ Error getting last completed episode for guild {guild_id}: {e}")
            raise DatabaseOperationError(f"Failed to get last completed episode: {e}")
    
    @staticmethod
    def get_next_episode_number(guild_id: str) -> int:
        """Get the next episode number for a guild"""
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT MAX(episode_number) FROM episodes WHERE guild_id = ?
            ''', (guild_id,))
            
            result = cursor.fetchone()
            max_episode = result[0] if result[0] is not None else 0
            
            return max_episode + 1
            
        except Exception as e:
            logger.error(f"❌ Error getting next episode number for guild {guild_id}: {e}")
            raise DatabaseOperationError(f"Failed to get next episode number: {e}")

class CharacterOperations:
    """Handle all character-related database operations"""
    
    @staticmethod
    def create_character_snapshot(episode_id: int, user_id: str, character_name: str,
                                character_data: Dict, snapshot_type: str,
                                notes: str = None) -> CharacterSnapshot:
        """Create a character snapshot"""
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            created_at = datetime.now()
            
            cursor.execute('''
                INSERT INTO character_snapshots 
                (episode_id, user_id, character_name, character_data, snapshot_type, notes, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (episode_id, user_id, character_name, serialize_json(character_data),
                  snapshot_type, notes, created_at))
            
            snapshot_id = cursor.lastrowid
            conn.commit()
            
            logger.info(f"✅ Created {snapshot_type} snapshot for {character_name}")
            
            return CharacterSnapshot(
                id=snapshot_id,
                episode_id=episode_id,
                user_id=user_id,
                character_name=character_name,
                character_data=character_data,
                snapshot_type=snapshot_type,
                notes=notes,
                created_at=created_at
            )
            
        except Exception as e:
            logger.error(f"❌ Error creating character snapshot: {e}")
            raise DatabaseOperationError(f"Failed to create character snapshot: {e}")
    
    @staticmethod
    def get_character_snapshots(user_id: str, episode_id: int = None) -> List[CharacterSnapshot]:
        """Get character snapshots for a user"""
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            if episode_id:
                cursor.execute('''
                    SELECT * FROM character_snapshots 
                    WHERE user_id = ? AND episode_id = ?
                    ORDER BY created_at DESC
                ''', (user_id, episode_id))
            else:
                cursor.execute('''
                    SELECT * FROM character_snapshots 
                    WHERE user_id = ?
                    ORDER BY created_at DESC
                ''', (user_id,))
            
            snapshots = []
            for row in cursor.fetchall():
                snapshots.append(CharacterSnapshot(
                    id=row['id'],
                    episode_id=row['episode_id'],
                    user_id=row['user_id'],
                    character_name=row['character_name'],
                    character_data=deserialize_json(row['character_data']),
                    snapshot_type=row['snapshot_type'],
                    notes=row['notes'],
                    created_at=datetime.fromisoformat(row['created_at']) if row['created_at'] else None
                ))
            
            return snapshots
            
        except Exception as e:
            logger.error(f"❌ Error getting character snapshots for {user_id}: {e}")
            raise DatabaseOperationError(f"Failed to get character snapshots: {e}")
    
    @staticmethod
    def get_latest_character_snapshot(user_id: str) -> Optional[CharacterSnapshot]:
        """Get the most recent character snapshot for a user"""
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT * FROM character_snapshots 
                WHERE user_id = ?
                ORDER BY created_at DESC
                LIMIT 1
            ''', (user_id,))
            
            row = cursor.fetchone()
            if not row:
                return None
            
            return CharacterSnapshot(
                id=row['id'],
                episode_id=row['episode_id'],
                user_id=row['user_id'],
                character_name=row['character_name'],
                character_data=deserialize_json(row['character_data']),
                snapshot_type=row['snapshot_type'],
                notes=row['notes'],
                created_at=datetime.fromisoformat(row['created_at']) if row['created_at'] else None
            )
            
        except Exception as e:
            logger.error(f"❌ Error getting latest character snapshot for {user_id}: {e}")
            raise DatabaseOperationError(f"Failed to get latest character snapshot: {e}")
    
    @staticmethod
    def record_character_progression(user_id: str, character_name: str, new_level: int,
                                   progression_type: str, reason: str = None,
                                   old_level: int = None, episode_id: int = None,
                                   experience_gained: int = 0) -> CharacterProgression:
        """Record character progression"""
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            timestamp = datetime.now()
            
            cursor.execute('''
                INSERT INTO character_progression 
                (user_id, character_name, episode_id, old_level, new_level, 
                 progression_type, reason, experience_gained, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (user_id, character_name, episode_id, old_level, new_level,
                  progression_type, reason, experience_gained, timestamp))
            
            progression_id = cursor.lastrowid
            conn.commit()
            
            logger.info(f"✅ Recorded {progression_type} for {character_name}: Level {old_level} → {new_level}")
            
            return CharacterProgression(
                id=progression_id,
                user_id=user_id,
                character_name=character_name,
                episode_id=episode_id,
                old_level=old_level,
                new_level=new_level,
                progression_type=progression_type,
                reason=reason,
                experience_gained=experience_gained,
                timestamp=timestamp
            )
            
        except Exception as e:
            logger.error(f"❌ Error recording character progression: {e}")
            raise DatabaseOperationError(f"Failed to record character progression: {e}")
    
    @staticmethod
    def get_character_progression_history(user_id: str) -> List[CharacterProgression]:
        """Get character progression history for a user"""
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT cp.*, e.episode_number, e.name as episode_name
                FROM character_progression cp
                LEFT JOIN episodes e ON cp.episode_id = e.id
                WHERE cp.user_id = ?
                ORDER BY cp.timestamp DESC
            ''', (user_id,))
            
            progressions = []
            for row in cursor.fetchall():
                progressions.append(CharacterProgression(
                    id=row['id'],
                    user_id=row['user_id'],
                    character_name=row['character_name'],
                    episode_id=row['episode_id'],
                    old_level=row['old_level'],
                    new_level=row['new_level'],
                    progression_type=row['progression_type'],
                    reason=row['reason'],
                    experience_gained=row['experience_gained'],
                    timestamp=datetime.fromisoformat(row['timestamp']) if row['timestamp'] else None
                ))
            
            return progressions
            
        except Exception as e:
            logger.error(f"❌ Error getting character progression history for {user_id}: {e}")
            raise DatabaseOperationError(f"Failed to get character progression history: {e}")
    
    @staticmethod
    def get_party_progression(episode_id: int) -> List[CharacterProgression]:
        """Get all character progressions for an episode"""
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT * FROM character_progression 
                WHERE episode_id = ?
                ORDER BY timestamp DESC
            ''', (episode_id,))
            
            progressions = []
            for row in cursor.fetchall():
                progressions.append(CharacterProgression(
                    id=row['id'],
                    user_id=row['user_id'],
                    character_name=row['character_name'],
                    episode_id=row['episode_id'],
                    old_level=row['old_level'],
                    new_level=row['new_level'],
                    progression_type=row['progression_type'],
                    reason=row['reason'],
                    experience_gained=row['experience_gained'],
                    timestamp=datetime.fromisoformat(row['timestamp']) if row['timestamp'] else None
                ))
            
            return progressions
            
        except Exception as e:
            logger.error(f"❌ Error getting party progression for episode {episode_id}: {e}")
            raise DatabaseOperationError(f"Failed to get party progression: {e}")

class StoryOperations:
    """Handle story notes and additional content"""
    
    @staticmethod
    def add_story_note(episode_id: int, user_id: str, content: str, 
                      note_type: str = "player_note", is_canonical: bool = False) -> int:
        """Add a story note"""
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO story_notes (episode_id, user_id, note_type, content, is_canonical)
                VALUES (?, ?, ?, ?, ?)
            ''', (episode_id, user_id, note_type, content, is_canonical))
            
            note_id = cursor.lastrowid
            conn.commit()
            
            logger.info(f"✅ Added {note_type} to episode {episode_id}")
            return note_id
            
        except Exception as e:
            logger.error(f"❌ Error adding story note: {e}")
            raise DatabaseOperationError(f"Failed to add story note: {e}")
    
    @staticmethod
    def get_episode_story_notes(episode_id: int) -> List[Dict]:
        """Get all story notes for an episode"""
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT * FROM story_notes 
                WHERE episode_id = ?
                ORDER BY created_at ASC
            ''', (episode_id,))
            
            notes = []
            for row in cursor.fetchall():
                notes.append({
                    'id': row['id'],
                    'episode_id': row['episode_id'],
                    'user_id': row['user_id'],
                    'note_type': row['note_type'],
                    'content': row['content'],
                    'is_canonical': bool(row['is_canonical']),
                    'created_at': row['created_at']
                })
            
            return notes
            
        except Exception as e:
            logger.error(f"❌ Error getting story notes for episode {episode_id}: {e}")
            raise DatabaseOperationError(f"Failed to get story notes: {e}")

class GuildOperations:
    """Handle guild-specific settings - FIXED sqlite3.Row compatibility"""
    
    @staticmethod
    def update_guild_settings(guild_id: str, **settings) -> bool:
        """Update guild settings - ✅ FIXED: Now supports current_scene"""
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Check if guild exists
            cursor.execute('SELECT guild_id FROM guild_settings WHERE guild_id = ?', (guild_id,))
            exists = cursor.fetchone()
            
            if exists:
                # Update existing - ✅ FIXED: Handle current_scene in updates
                set_clauses = []
                values = []
                
                # Handle all possible settings including current_scene
                allowed_settings = ['current_episode', 'voice_speed', 'voice_quality', 'tts_enabled', 'current_scene']
                
                for key, value in settings.items():
                    if key in allowed_settings:
                        set_clauses.append(f"{key} = ?")
                        values.append(value)
                
                if set_clauses:
                    set_clauses.append("updated_at = ?")
                    values.append(datetime.now())
                    values.append(guild_id)
                    
                    query = f"UPDATE guild_settings SET {', '.join(set_clauses)} WHERE guild_id = ?"
                    cursor.execute(query, values)
                    logger.info(f"✅ Updated guild settings for {guild_id}: {list(settings.keys())}")
            else:
                # Insert new - ✅ FIXED: Include current_scene in initial insert
                cursor.execute('''
                    INSERT INTO guild_settings (guild_id, current_episode, voice_speed, voice_quality, tts_enabled, current_scene)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (guild_id, 
                      settings.get('current_episode', 0),
                      settings.get('voice_speed', 1.25),
                      settings.get('voice_quality', 'smart'),
                      settings.get('tts_enabled', False),
                      settings.get('current_scene', '')))  # ✅ NEW: Include current_scene
                logger.info(f"✅ Created new guild settings for {guild_id}")
            
            conn.commit()
            return True
            
        except Exception as e:
            logger.error(f"❌ Error updating guild settings: {e}")
            raise DatabaseOperationError(f"Failed to update guild settings: {e}")
        finally:
            if conn:
                conn.close()
    
    @staticmethod
    def get_guild_settings(guild_id: str) -> Dict:
        """Get guild settings - ✅ FIXED: Proper sqlite3.Row handling"""
        conn = None
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            cursor.execute('SELECT * FROM guild_settings WHERE guild_id = ?', (guild_id,))
            row = cursor.fetchone()
            
            if not row:
                # Return defaults including current_scene
                return {
                    'current_episode': 0,
                    'voice_speed': 1.25,
                    'voice_quality': 'smart',
                    'tts_enabled': False,
                    'current_scene': ''  # ✅ NEW: Include in defaults
                }
            
            # ✅ FIXED: Handle sqlite3.Row properly - no .get() method available
            # Use try/except for accessing columns that might not exist
            try:
                current_scene = row['current_scene'] if 'current_scene' in row.keys() else ''
            except (KeyError, IndexError):
                current_scene = ''
            
            return {
                'guild_id': row['guild_id'],
                'current_episode': row['current_episode'],
                'voice_speed': row['voice_speed'],
                'voice_quality': row['voice_quality'],
                'tts_enabled': bool(row['tts_enabled']),
                'current_scene': current_scene,  # ✅ FIXED: Use safe access
                'created_at': row['created_at'],
                'updated_at': row['updated_at']
            }
            
        except Exception as e:
            logger.error(f"❌ Error getting guild settings: {e}")
            raise DatabaseOperationError(f"Failed to get guild settings: {e}")
        finally:
            if conn:
                conn.close()

    @staticmethod
    def get_guild_scene(guild_id: str) -> str:
        """Get just the current scene for a guild - ✅ NEW: Convenience method"""
        try:
            settings = GuildOperations.get_guild_settings(guild_id)
            return settings.get('current_scene', '')
        except Exception as e:
            logger.error(f"❌ Error getting guild scene: {e}")
            return ''
    
    @staticmethod
    def update_guild_scene(guild_id: str, scene: str) -> bool:
        """Update just the current scene for a guild - ✅ NEW: Convenience method"""
        try:
            return GuildOperations.update_guild_settings(guild_id, current_scene=scene)
        except Exception as e:
            logger.error(f"❌ Error updating guild scene: {e}")
            return False