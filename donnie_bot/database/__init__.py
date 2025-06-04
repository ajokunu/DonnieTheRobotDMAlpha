# donnie_bot/database/__init__.py
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

# Enhanced memory system imports
try:
    from .enhanced_schema import upgrade_database_schema
    ENHANCED_SCHEMA_AVAILABLE = True
except ImportError:
    ENHANCED_SCHEMA_AVAILABLE = False
    def upgrade_database_schema():
        print("⚠️ Enhanced schema not available")

try:
    from .memory_operations import (
        AdvancedMemoryOperations, 
        ConversationMemory, 
        NPCMemory
    )
    MEMORY_OPERATIONS_AVAILABLE = True
except ImportError:
    MEMORY_OPERATIONS_AVAILABLE = False
    # Create fallback classes
    class AdvancedMemoryOperations:
        def __init__(self, claude_client):
            pass
    class ConversationMemory:
        pass
    class NPCMemory:
        pass

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
    
    # Enhanced memory classes
    'AdvancedMemoryOperations',
    'ConversationMemory', 
    'NPCMemory',
    'upgrade_database_schema',
    
    # Exceptions
    'DatabaseOperationError'
]

# Enhanced init_database function
def init_database():
    """Initialize database with enhanced memory schema"""
    # Import the original init_database function
    from .database import init_database as _original_init_database
    
    # Call original initialization
    _original_init_database()
    
    # Add enhanced memory schema
    if ENHANCED_SCHEMA_AVAILABLE:
        try:
            upgrade_database_schema()
            print("✅ Enhanced memory schema initialized")
        except Exception as e:
            print(f"⚠️ Enhanced schema failed: {e}")
    else:
        print("⚠️ Enhanced memory schema not available")

# Version info
__version__ = "1.1.0"