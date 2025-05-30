# database/__init__.py
"""
Storm King's Thunder Database Module
Provides database operations for episodes, characters, and campaign management
"""

from .database import (
    init_database,
    close_database,
    get_db_connection,
    backup_database,
    get_database_stats,
    health_check,
    serialize_json,
    deserialize_json
)

from .operations import (
    EpisodeOperations,
    CharacterOperations,
    StoryOperations,
    GuildOperations,
    Episode,
    CharacterSnapshot,
    CharacterProgression,
    DatabaseOperationError
)

__all__ = [
    # Database functions
    'init_database',
    'close_database',
    'get_db_connection',
    'backup_database',
    'get_database_stats',
    'health_check',
    'serialize_json',
    'deserialize_json',
    
    # Operations classes
    'EpisodeOperations',
    'CharacterOperations',
    'StoryOperations',
    'GuildOperations',
    
    # Data classes
    'Episode',
    'CharacterSnapshot',
    'CharacterProgression',
    
    # Exceptions
    'DatabaseOperationError'
]

# Version info
__version__ = "1.0.0"