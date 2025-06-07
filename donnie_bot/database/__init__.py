
"""
Storm King's Thunder Database Module - STREAMLINED VERSION
Provides database operations for episodes, characters, and campaign management
"""

import logging

# Set up logging for database operations
logger = logging.getLogger(__name__)

# ====== CORE DATABASE FUNCTIONS ======
def safe_import_database_core():
    """Safely import core database functions"""
    try:
        from .database import (
            init_database as _core_init_database,
            close_database,
            get_db_connection,
            backup_database,
            get_database_stats,
            health_check,
            serialize_json,
            deserialize_json
        )
        return True, (_core_init_database, close_database, get_db_connection, backup_database,
                     get_database_stats, health_check, serialize_json, deserialize_json)
    except ImportError as e:
        logger.error(f"Failed to import core database functions: {e}")
        return False, (None, None, None, None, None, None, None, None)

def safe_import_database_operations():
    """Safely import database operations"""
    try:
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
        return True, (EpisodeOperations, CharacterOperations, StoryOperations, GuildOperations,
                     Episode, CharacterSnapshot, CharacterProgression, DatabaseOperationError)
    except ImportError as e:
        logger.error(f"Failed to import database operations: {e}")
        return False, (None, None, None, None, None, None, None, None)

def safe_import_enhanced_schema():
    """Safely import enhanced schema functionality"""
    try:
        from .enhanced_schema import upgrade_database_schema
        return True, upgrade_database_schema
    except ImportError as e:
        logger.warning(f"Enhanced schema not available: {e}")
        def dummy_upgrade():
            logger.warning("⚠️ Enhanced schema not available")
        return False, dummy_upgrade

def safe_import_memory_operations():
    """Safely import memory operations"""
    try:
        from .memory_operations import (
            AdvancedMemoryOperations, 
            ConversationMemory, 
            NPCMemory
        )
        return True, (AdvancedMemoryOperations, ConversationMemory, NPCMemory)
    except ImportError as e:
        logger.warning(f"Memory operations not available: {e}")
        # Create fallback classes
        class AdvancedMemoryOperations:
            def __init__(self, claude_client):
                pass
        class ConversationMemory:
            pass
        class NPCMemory:
            pass
        return False, (AdvancedMemoryOperations, ConversationMemory, NPCMemory)

# ====== PERFORM SAFE IMPORTS ======
logger.info("Initializing database module...")

# Import core functions
CORE_AVAILABLE, core_imports = safe_import_database_core()
if CORE_AVAILABLE:
    (_core_init_database, close_database, get_db_connection, backup_database,
     get_database_stats, health_check, serialize_json, deserialize_json) = core_imports
    logger.info("✅ Core database functions imported")
else:
    logger.error("❌ Core database functions failed to import")
    # Create dummy functions to prevent crashes
    def _core_init_database(): pass
    def close_database(): pass
    def get_db_connection(): return None
    def backup_database(): return None
    def get_database_stats(): return {}
    def health_check(): return False
    def serialize_json(data): return "{}"
    def deserialize_json(json_str): return {}

# Import operations
OPERATIONS_AVAILABLE, ops_imports = safe_import_database_operations()
if OPERATIONS_AVAILABLE:
    (EpisodeOperations, CharacterOperations, StoryOperations, GuildOperations,
     Episode, CharacterSnapshot, CharacterProgression, DatabaseOperationError) = ops_imports
    logger.info("✅ Database operations imported")
else:
    logger.error("❌ Database operations failed to import")
    # Create dummy classes (already defined in main.py fallbacks)

# Import enhanced schema
ENHANCED_SCHEMA_AVAILABLE, upgrade_database_schema = safe_import_enhanced_schema()

# Import memory operations
MEMORY_OPERATIONS_AVAILABLE, memory_imports = safe_import_memory_operations()
if MEMORY_OPERATIONS_AVAILABLE:
    AdvancedMemoryOperations, ConversationMemory, NPCMemory = memory_imports
    logger.info("✅ Memory operations imported")
else:
    AdvancedMemoryOperations, ConversationMemory, NPCMemory = memory_imports
    logger.warning("⚠️ Using fallback memory operations")

# ====== UNIFIED DATABASE INITIALIZATION ======
def init_database():
    """
    UNIFIED database initialization function - single entry point
    Handles both core database setup and enhanced schema upgrade
    """
    logger.info("🔄 Starting unified database initialization...")
    
    if not CORE_AVAILABLE:
        logger.error("❌ Cannot initialize database - core functions not available")
        return False
    
    try:
        # Step 1: Initialize core database
        logger.info("Step 1: Initializing core database schema...")
        _core_init_database()
        logger.info("✅ Core database schema initialized")
        
        # Step 2: Test database health
        if not health_check():
            logger.error("❌ Database health check failed after core initialization")
            return False
        
        # Step 3: Upgrade to enhanced schema if available
        if ENHANCED_SCHEMA_AVAILABLE:
            try:
                logger.info("Step 2: Upgrading to enhanced memory schema...")
                upgrade_database_schema()
                logger.info("✅ Enhanced memory schema upgrade completed")
            except Exception as e:
                logger.error(f"❌ Enhanced schema upgrade failed: {e}")
                # Continue anyway - core database is working
        else:
            logger.warning("⚠️ Enhanced schema not available - using core database only")
        
        # Step 4: Final health check
        if health_check():
            stats = get_database_stats()
            logger.info(f"✅ Database initialization complete - {stats}")
            return True
        else:
            logger.error("❌ Final database health check failed")
            return False
            
    except Exception as e:
        logger.error(f"❌ Database initialization failed: {e}")
        import traceback
        traceback.print_exc()
        return False

# ====== VERSION INFO ======
__version__ = "2.0.0-"

# ====== EXPORT ALL ======
__all__ = [
    # Core database functions
    'init_database',
    'close_database', 
    'get_db_connection',
    'backup_database',
    'get_database_stats',
    'health_check',
    'serialize_json',
    'deserialize_json',
    
    # Operations classes (if available)
    'EpisodeOperations',
    'CharacterOperations', 
    'StoryOperations',
    'GuildOperations',
    
    # Data classes (if available)
    'Episode',
    'CharacterSnapshot',
    'CharacterProgression',
    
    # Enhanced memory classes (if available)
    'AdvancedMemoryOperations',
    'ConversationMemory',
    'NPCMemory',
    'upgrade_database_schema',
    
    # Exceptions
    'DatabaseOperationError',
    
    # Availability flags
    'CORE_AVAILABLE',
    'OPERATIONS_AVAILABLE', 
    'ENHANCED_SCHEMA_AVAILABLE',
    'MEMORY_OPERATIONS_AVAILABLE'
]

# ====== INITIALIZATION STATUS REPORT ======
logger.info(f"📊 Database module status:")
logger.info(f"   Core Functions: {'✅' if CORE_AVAILABLE else '❌'}")
logger.info(f"   Operations: {'✅' if OPERATIONS_AVAILABLE else '❌'}")
logger.info(f"   Enhanced Schema: {'✅' if ENHANCED_SCHEMA_AVAILABLE else '❌'}")
logger.info(f"   Memory Operations: {'✅' if MEMORY_OPERATIONS_AVAILABLE else '❌'}")

if CORE_AVAILABLE and OPERATIONS_AVAILABLE:
    logger.info("✅ Database module ready for full functionality")
elif CORE_AVAILABLE:
    logger.warning("⚠️ Database module ready with limited functionality")
else:
    logger.error("❌ Database module in fallback mode - limited functionality")