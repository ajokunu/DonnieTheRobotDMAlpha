import discord
from discord.ext import commands
from discord import app_commands
import anthropic
import asyncio
import os
from dotenv import load_dotenv
import random
from typing import Optional
import aiohttp
import tempfile
import io
import time
from datetime import datetime

# Combat system imports (simplified)
import json
from typing import Dict, List, Tuple, Optional
load_dotenv()

# ⚡ PERFORMANCE CONFIGURATION
MAX_MEMORIES_FAST = 2  # Limited memory retrieval for speed@bot.event
MAX_MEMORIES_FULL = 10  # Full memory retrieval when needed
BACKGROUND_PROCESSING = True  # Process memories after response sent
MAX_RESPONSE_LENGTH = 650  # Shorter responses for faster TTS
RESPONSE_TIMEOUT = 8.0  # Maximum time to wait for Claude response


try:
    from voice_manager import initialize_voice_manager, get_voice_manager
    VOICE_MANAGER_AVAILABLE = True
    print("✅ Voice manager module imported successfully")
except ImportError as e:
    print(f"⚠️ Voice manager not available: {e}")
    VOICE_MANAGER_AVAILABLE = False

voice_manager = None  # Will be initialized later

async def add_to_voice_queue(guild_id: int, text: str, speaker: str, message=None):
    """Minimal wrapper for voice_manager - required for episode/progression systems"""
    global voice_manager
    
    if voice_manager and voice_manager.is_voice_active(guild_id):
        await voice_manager.speak_text(guild_id, text, speaker)
        
        # Update message if provided (for backwards compatibility)
        if message:
            try:
                embed = message.embeds[0] if message.embeds else None
                if embed:
                    for i, field in enumerate(embed.fields):
                        if field.name == "🎤":
                            embed.set_field_at(i, name="🎤", value=f"*Donnie responds to {speaker}*", inline=False)
                            break
                    await message.edit(embed=embed)
            except Exception as e:
                print(f"⚠️ Message update failed: {e}")
    else:
        print(f"⚠️ Voice not active for guild {guild_id}")


# ====== FFMPEG AVAILABILITY CHECK ======
FFMPEG_AVAILABLE = False
try:
    import subprocess
    subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True)
    FFMPEG_AVAILABLE = True
    print("✅ FFmpeg detected")
except:
    print("❌ FFmpeg not found - voice features will be disabled")

# ====== HELPER FUNCTIONS FOR SAFE TYPE CHECKING ======
def is_user_in_voice(interaction: discord.Interaction) -> bool:
    """Safely check if user is in voice channel"""
    return (isinstance(interaction.user, discord.Member) and 
            interaction.user.voice is not None and 
            interaction.user.voice.channel is not None)

def is_admin(interaction: discord.Interaction) -> bool:
    """Safely check if user is admin"""
    return (isinstance(interaction.user, discord.Member) and 
            interaction.user.guild_permissions.administrator)

def get_voice_channel(interaction: discord.Interaction):
    """Safely get user's voice channel"""
    if not isinstance(interaction.user, discord.Member):
        return None
    if not interaction.user.voice:
        return None
    return interaction.user.voice.channel

try:
    from combat_system.combat_integration import initialize_combat_system, get_combat_integration
    from unified_dm_response import generate_dm_response_with_combat  # New import for combat integration
    print("✅ Enhanced Combat System with unified integration loaded!")
    COMBAT_AVAILABLE = True
except ImportError as e:
    print(f"⚠️ Combat system not available: {e}")
    COMBAT_AVAILABLE = False
    # Fallback: define get_combat_integration to avoid unbound errors
    def get_combat_integration():
        return None

# ====== Memory System Adapter ======

class MemoryDatabaseAdapter:
    """Adapter that uses real memory operations"""
    
    def __init__(self, episode_ops, character_ops, guild_ops):
        self.episode_ops = episode_ops
        self.character_ops = character_ops
        self.guild_ops = guild_ops
        self.initialized = DATABASE_AVAILABLE
        
        # Initialize the REAL memory operations
        self.memory_ops = None
        if DATABASE_AVAILABLE:
            try:
                from database.memory_operations import AdvancedMemoryOperations
                self.memory_ops = AdvancedMemoryOperations(claude_client)
                print("✅ Real memory operations initialized!")
            except Exception as e:
                print(f"❌ Failed to initialize memory operations: {e}")
                self.memory_ops = None
                self.initialized = False
        
        print(f"✅ Memory database adapter created (Available: {self.initialized})")
    
    async def store_conversation_memory(self, campaign_id: str, episode_id: int, 
                                      user_id: str, character_name: str, 
                                      player_input: str, dm_response: str, **kwargs) -> bool:
        """Store conversation memory using REAL database operations"""
        if not self.initialized or not self.memory_ops:
            print("⚠️ Memory operations not available")
            return False
        
        try:
            # Use the REAL memory operations
            result = await self.memory_ops.store_conversation_memory(
                campaign_id=campaign_id,
                episode_id=episode_id,
                user_id=user_id,
                character_name=character_name,
                player_input=player_input,
                dm_response=dm_response
            )
            
            if result:
                print(f"✅ Stored memory for {character_name}")
            return bool(result)
            
        except Exception as e:
            print(f"❌ Error storing conversation memory: {e}")
            return False
    
    async def retrieve_relevant_memories(self, campaign_id: str, query: str, 
                                       max_memories: int = 5, **kwargs) -> list:
        """Retrieve relevant memories using REAL database operations"""
        if not self.initialized or not self.memory_ops:
            return []
        
        try:
            # Use the REAL memory operations
            memories = await self.memory_ops.retrieve_relevant_memories(
                campaign_id=campaign_id,
                query=query,
                max_memories=max_memories,
                min_importance=kwargs.get('min_importance', 0.4)
            )
            
            print(f"✅ Retrieved {len(memories)} memories for query: {query[:50]}...")
            return memories
            
        except Exception as e:
            print(f"❌ Error retrieving memories: {e}")
            return []
    
    async def get_campaign_npcs(self, campaign_id: str, importance: str = "important") -> list:
        """Get campaign NPCs using REAL database operations"""
        if not self.initialized or not self.memory_ops:
            return []
        
        try:
            npcs = await self.memory_ops.get_campaign_npcs(campaign_id, importance)
            print(f"✅ Retrieved {len(npcs)} NPCs")
            return npcs
        except Exception as e:
            print(f"❌ Error retrieving NPCs: {e}")
            return []

# ====== DATABASE HELPER FUNCTIONS ======
def update_database_from_campaign_context(guild_id: str):
    """FIXED: Update database with current campaign context"""
    if not DATABASE_AVAILABLE:
        return
    
    try:
        # Ensure guild_id is string
        guild_id = str(guild_id)
        
        current_episode = EpisodeOperations.get_current_episode(guild_id)
        if current_episode and campaign_context.get("session_history"):
            EpisodeOperations.update_session_history(
                current_episode.id,
                campaign_context["session_history"]
            )
        
        # Convert guild_id to int for voice settings if possible
        try:
            guild_id_int = int(guild_id)
            settings_update = {
                'voice_speed': voice_speed.get(guild_id_int, 1.25),
                'tts_enabled': tts_enabled.get(guild_id_int, False),
                'current_scene': campaign_context.get("current_scene", ""),
                'current_episode': campaign_context.get("current_episode", 0)
            }
            
            GuildOperations.update_guild_settings(guild_id, **settings_update)
            print(f"✅ Updated database settings for guild {guild_id}")
        except ValueError:
            print(f"⚠️ Could not convert guild_id to int: {guild_id}")
    except Exception as e:
        print(f"⚠️ Failed to update database from campaign context: {e}")

def sync_campaign_context_with_database(guild_id: str):
    """FIXED: Sync in-memory campaign context with database state"""
    if not DATABASE_AVAILABLE:
        return
    
    try:
        # Ensure guild_id is string for database operations
        guild_id = str(guild_id)
        
        print(f"🔄 Syncing campaign context for guild {guild_id}")
        
        # Get current episode from database
        current_episode = EpisodeOperations.get_current_episode(guild_id)
        if current_episode:
            campaign_context["current_episode"] = current_episode.episode_number
            campaign_context["episode_active"] = True
            campaign_context["episode_start_time"] = current_episode.start_time
            campaign_context["guild_id"] = guild_id
            
            if current_episode.session_history:
                campaign_context["session_history"] = current_episode.session_history
            
            print(f"✅ Synced campaign context with Episode {current_episode.episode_number}")
        
        # Get guild settings
        guild_settings = GuildOperations.get_guild_settings(guild_id)
        if guild_settings:
            try:
                guild_id_int = int(guild_id)
                voice_speed[guild_id_int] = guild_settings.get('voice_speed', 1.25)
                tts_enabled[guild_id_int] = guild_settings.get('tts_enabled', False)
            except ValueError:
                print(f"⚠️ Could not convert guild_id to int for voice settings: {guild_id}")
            
            if 'current_scene' in guild_settings and guild_settings['current_scene']:
                campaign_context["current_scene"] = guild_settings['current_scene']
                print(f"✅ Synced scene from database")
            
            print(f"✅ Synced guild settings for {guild_id}")
            
    except Exception as e:
        print(f"⚠️ Failed to sync campaign context: {e}")

# ====== GLOBAL SYSTEM VARIABLE DECLARATIONS ======

episode_commands = None
character_progression = None
unified_response_system_instance = None
memory_database_adapter = None



# ====== DATABASE AND EPISODE MANAGEMENT IMPORTS ======

def safe_import_database():
    """Safely import database operations with proper error handling"""
    try:
        from database import init_database, close_database, health_check, get_database_stats
        from database.operations import EpisodeOperations, CharacterOperations, GuildOperations, DatabaseOperationError
        print("✅ Database operations imported successfully")
        return True, (init_database, close_database, health_check, get_database_stats, 
                     EpisodeOperations, CharacterOperations, GuildOperations, DatabaseOperationError)
    except ImportError as e:
        print(f"❌ Database operations failed to import: {e}")
        return False, (None, None, None, None, None, None, None, None)

def safe_import_episode_manager():
    """Safely import episode management with proper error handling"""
    try:
        from episode_manager import EpisodeCommands
        print("✅ Episode management imported successfully")
        return True, EpisodeCommands
    except ImportError as e:
        print(f"❌ Episode management failed to import: {e}")
        return False, None

def safe_import_character_progression():
    """Safely import character progression with proper error handling"""
    try:
        from character_tracker import CharacterProgressionCommands
        print("✅ Character progression imported successfully") 
        return True, CharacterProgressionCommands
    except ImportError as e:
        print(f"❌ Character progression failed to import: {e}")
        return False, None

def safe_import_unified_response():
    """Safely import unified response system"""
    try:
        from unified_dm_response import (
            initialize_unified_response_system,
            generate_dm_response,
            store_interaction_background,
            get_response_system_status
        )
        print("✅ Unified DM Response System imported!")
        return True, (initialize_unified_response_system, generate_dm_response, 
                     store_interaction_background, get_response_system_status)
    except ImportError as e:
        print(f"⚠️ Unified response system not available: {e}")
        return False, (None, None, None, None)

# Perform safe imports
DATABASE_AVAILABLE, database_imports = safe_import_database()
if DATABASE_AVAILABLE:
    init_database, close_database, health_check, get_database_stats, EpisodeOperations, CharacterOperations, GuildOperations, DatabaseOperationError = database_imports
else:
    # Create fallback empty classes to prevent crashes
    class EpisodeOperations:
        @staticmethod
        def create_episode(*args, **kwargs): pass
        @staticmethod
        def get_current_episode(*args, **kwargs): return None
    
    class CharacterOperations:
        @staticmethod
        def create_character_snapshot(*args, **kwargs): pass
    
    class GuildOperations:
        @staticmethod
        def get_guild_settings(*args, **kwargs): return {}
        @staticmethod
        def update_guild_settings(*args, **kwargs): pass
    
    def init_database(): pass
    def close_database(): pass
    def health_check(): return False
    def get_database_stats(): return {}

EPISODE_MANAGER_AVAILABLE, EpisodeCommands = safe_import_episode_manager()
CHARACTER_PROGRESSION_AVAILABLE, CharacterProgressionCommands = safe_import_character_progression()
UNIFIED_RESPONSE_AVAILABLE, unified_imports = safe_import_unified_response()

if UNIFIED_RESPONSE_AVAILABLE:
    initialize_unified_response_system, generate_dm_response, store_interaction_background, get_response_system_status = unified_imports
    PERSISTENT_MEMORY_AVAILABLE = True  # The unified system handles fallbacks
else:
    PERSISTENT_MEMORY_AVAILABLE = False

# Combat system imports - NEW COMBAT INTEGRATION!
try:
    from combat_system.combat_integration import initialize_combat_system, get_combat_integration
    print("✅ STREAMLINED Combat System loaded!")
    COMBAT_AVAILABLE = True
except ImportError as e:
    print(f"⚠️ Combat system not available: {e}")
    COMBAT_AVAILABLE = False
    # Fallback: define get_combat_integration to avoid unbound errors
    def get_combat_integration():
        return None

# Initialize APIs
claude_client = anthropic.Anthropic(api_key=os.getenv('ANTHROPIC_API_KEY'))

# Discord bot setup with voice intents
intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True  # Required for voice functionality

bot = commands.Bot(command_prefix='/', intents=intents, help_command=None)

# Voice quality was moved to top of file with other voice globals

# Voice client storage
voice_manager = None


@bot.event
async def on_ready():
    """FIXED: Proper initialization with voice_manager and scope fixes"""
    global episode_commands, character_progression, unified_response_system_instance
    global memory_database_adapter, voice_manager
    global DATABASE_AVAILABLE, EPISODE_MANAGER_AVAILABLE, CHARACTER_PROGRESSION_AVAILABLE
    global UNIFIED_RESPONSE_AVAILABLE, PERSISTENT_MEMORY_AVAILABLE, COMBAT_AVAILABLE

    print(f'⚡ {bot.user} is ready for Storm King\'s Thunder!')
    print(f'🏔️ Giants threaten the Sword Coast!')
    
    # ====== VOICE SYSTEM INITIALIZATION (FIRST!) ======
    print("🎤 Initializing voice system...")
    try:
        # Get OpenAI API key for voice features
        openai_api_key = os.getenv('OPENAI_API_KEY')
        if openai_api_key and FFMPEG_AVAILABLE:
            voice_manager = initialize_voice_manager(bot, openai_api_key)
            print("✅ Voice manager initialized successfully")
            print("🎤 Donnie the DM is ready to speak!")
            print("🎤 Features: Enhanced audio system, voice queue, TTS optimization")
        else:
            print("⚠️ Voice manager not initialized - missing OPENAI_API_KEY or FFmpeg")
            if not openai_api_key:
                print("   Add OPENAI_API_KEY to your .env file")
            if not FFMPEG_AVAILABLE:
                print("   Install FFmpeg for voice features")
    except Exception as e:
        print(f"⚠️ Voice manager initialization failed: {e}")
        voice_manager = None
    
    print(f'⚔️ Enhanced Combat System: {"✅ Active" if COMBAT_AVAILABLE else "❌ Disabled"}')
    
    # ====== DATABASE INITIALIZATION ======
    if DATABASE_AVAILABLE:
        try:
            print("🔄 Initializing database with enhanced memory schema...")
            
            # Step 1: Initialize core database
            init_database()
            print("✅ Core database initialized")
            
            # Step 2: Upgrade to enhanced memory schema
            try:
                from database.enhanced_schema import upgrade_database_schema
                upgrade_database_schema()
                print("✅ Enhanced memory schema upgraded successfully")
            except Exception as e:
                print(f"⚠️ Enhanced schema upgrade failed: {e}")
            
            # Step 3: Create REAL memory adapter
            memory_database_adapter = MemoryDatabaseAdapter(
                EpisodeOperations, CharacterOperations, GuildOperations
            )
            print("✅ Real memory adapter initialized")
            
            # Step 4: Test database health
            if health_check():
                stats = get_database_stats()
                print(f"📊 Database stats: {stats}")
                
                # Test memory tables
                try:
                    from database.database import get_db_connection
                    conn = get_db_connection()
                    cursor = conn.cursor()
                    
                    memory_tables = ['conversation_memories', 'npc_memories', 'memory_consolidation']
                    for table in memory_tables:
                        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,))
                        if cursor.fetchone():
                            print(f"✅ Memory table '{table}' exists")
                        else:
                            print(f"❌ Memory table '{table}' missing")
                    
                    conn.close()
                    
                except Exception as e:
                    print(f"⚠️ Memory table check failed: {e}")
            else:
                print("⚠️ Database health check failed")
                
        except Exception as e:
            print(f"❌ Database initialization failed: {e}")
            DATABASE_AVAILABLE = False
            memory_database_adapter = None
    else:
        print("⚠️ Database features disabled")
        memory_database_adapter = None
    
    # ====== UNIFIED RESPONSE SYSTEM INITIALIZATION ======
    if UNIFIED_RESPONSE_AVAILABLE:
        try:
            print("🔄 Initializing unified response system with REAL memory...")
            
            memory_available = (DATABASE_AVAILABLE and 
                              memory_database_adapter and 
                              hasattr(memory_database_adapter, 'memory_ops') and 
                              memory_database_adapter.memory_ops is not None)
            
            unified_response_system_instance = initialize_unified_response_system(
                claude_client=claude_client,
                campaign_context=campaign_context,
                persistent_memory_available=memory_available,
                database_operations=memory_database_adapter,
                max_response_length=MAX_RESPONSE_LENGTH,
                response_timeout=RESPONSE_TIMEOUT
            )
            
            print(f"🎯 Unified DM Response System initialized with memory: {'✅' if memory_available else '❌'}")
            
        except Exception as e:
            print(f"❌ Failed to initialize unified response system: {e}")
            import traceback
            traceback.print_exc()
    else:
        print("⚠️ Unified response system not available - using basic fallbacks")
    
    # ====== EPISODE MANAGEMENT INITIALIZATION ======
    if EPISODE_MANAGER_AVAILABLE and DATABASE_AVAILABLE:
        try:
            print("🔄 Initializing episode management...")
            episode_commands = EpisodeCommands(
                bot=bot,
                campaign_context=campaign_context,
                voice_clients=voice_manager.voice_clients if voice_manager else {},
                tts_enabled=voice_manager.tts_enabled if voice_manager else {},
                add_to_voice_queue_func=add_to_voice_queue,  # ✅ Now available!
                episode_operations=EpisodeOperations,
                character_operations=CharacterOperations,
                guild_operations=GuildOperations,
                claude_client=claude_client,
                sync_function=sync_campaign_context_with_database,
                unified_response_system=unified_response_system_instance
            )
            print("✅ Episode management system initialized with database support")
        except Exception as e:
            print(f"⚠️ Episode management initialization failed: {e}")
            import traceback
            traceback.print_exc()
            episode_commands = None
    else:
        print("⚠️ Episode management disabled (missing dependencies)")
        episode_commands = None
    
    # ====== CHARACTER PROGRESSION INITIALIZATION ======
    if CHARACTER_PROGRESSION_AVAILABLE and DATABASE_AVAILABLE:
        try:
            print("🔄 Initializing character progression...")
            character_progression = CharacterProgressionCommands(
                bot=bot,
                campaign_context=campaign_context,
                voice_clients=voice_manager.voice_clients if voice_manager else {},
                tts_enabled=voice_manager.tts_enabled if voice_manager else {},
                add_to_voice_queue_func=add_to_voice_queue,  # ✅ Now available!
                character_operations=CharacterOperations,
                episode_operations=EpisodeOperations
            )
            print("✅ Character progression system initialized with database support")
        except Exception as e:
            print(f"⚠️ Character progression initialization failed: {e}")
            import traceback
            traceback.print_exc()
            character_progression = None
    else:
        print("⚠️ Character progression disabled (missing dependencies)")
        character_progression = None
    
    # ====== COMBAT SYSTEM INITIALIZATION ======
    if COMBAT_AVAILABLE:
        try:
            print("🔄 Initializing combat system...")
            if 'initialize_combat_system' in globals() and callable(initialize_combat_system):
                await initialize_combat_system(bot, campaign_context)
                print("✅ Combat system initialized successfully")
            else:
                print("⚠️ Combat system initialize function not found")
        except Exception as e:
            print(f"⚠️ Combat system initialization failed: {e}")
    
    # ====== COMMAND SYNCHRONIZATION ======
    print('🔄 Syncing slash commands...')
    
    try:
        synced = await bot.tree.sync()
        print(f'✅ Synced {len(synced)} slash commands')
        
        # ====== FINAL STATUS REPORT ======
        features = {
            "Database": "✅" if DATABASE_AVAILABLE else "❌",
            "Unified Response System": "✅" if UNIFIED_RESPONSE_AVAILABLE else "❌", 
            "Episodes": "✅" if episode_commands else "❌",
            "Progression": "✅" if character_progression else "❌",
            "Persistent Memory": "✅" if PERSISTENT_MEMORY_AVAILABLE else "❌",
            "Enhanced Combat": "✅" if COMBAT_AVAILABLE else "❌",
            "Continue Buttons": "✅",
            "PDF Upload": "✅" if hasattr(bot, 'pdf_character_commands') else "❌",
            "Voice Manager": "✅" if voice_manager else "❌"
        }
        
        print("🎲 Storm King's Thunder Bot Feature Status:")
        for feature, status in features.items():
            print(f"   {status} {feature}")
            
        print("🎉 Ready for UNIFIED epic adventures!")
        
        # ====== SYSTEM VERIFICATION ======
        if UNIFIED_RESPONSE_AVAILABLE and unified_response_system_instance:
            try:
                status = get_response_system_status()
                if "Not Initialized" not in str(status):
                    print("✅ Unified response system verified working!")
                else:
                    print("⚠️ Unified response system initialization issue detected")
            except Exception as e:
                print(f"⚠️ Could not verify unified response system: {e}")
        
        # Verify systems
        if episode_commands:
            print("✅ Episode management verified working!")
        else:
            print("⚠️ Episode management not properly initialized")
            
        if voice_manager:
            print("✅ Voice manager verified working!")
        else:
            print("⚠️ Voice manager not properly initialized")
        
    except Exception as e:
        print(f'❌ Failed to sync commands: {e}')
        import traceback
        traceback.print_exc()


# DM Thinking Sounds - ACTUAL sounds, not descriptions
DM_THINKING_SOUNDS = [
    "...Hhhhhmm...",
    "...Aaahhh okay let's try",  # actual throat clearing sound
    "...Uhhhh...huh yes okay...",
    "...Let meeee see...",
    "...Mmm-hmm...",
    "...Ah, okay then...",
    "...Right well okay...",
    "...Well...",
    "...Okay...",
    "...Hmm, hmm...",
    "...Uh-huh...", 
    "...Mmm...",
    "...Oh...",
    "...Alright...",
    "...Err...",
    "...Umm...",
    "...Ah-huh...",
    "...Hmmph...",
    "...alright, alright, alright...",
    "...Let me think...",
]

# Enhanced Storm King's Thunder Campaign Context with Episode Management
campaign_context = {
    "campaign_name": "Storm King's Thunder",
    "setting": "The Sword Coast - Giants have begun raiding settlements across the land. The ancient ordning that kept giant society in check has collapsed, throwing giantkind into chaos.",
    "players": {},
    "characters": {},  # Store character information
    "current_scene": "The village of Nightstone sits eerily quiet. Giant-sized boulders litter the village square, and not a soul can be seen moving in the streets. The party approaches the mysteriously open gates...",
    "session_history": [],
    "session_started": False,
    
    # New Episode Management Fields
    "current_episode": 0,
    "episode_active": False,
    "episode_start_time": None,
    "guild_id": None,  # Track which Discord server this campaign belongs to
}

class ContinueView(discord.ui.View):
    def __init__(self, original_user_id: str):
        super().__init__(timeout=300)  # 5 minute timeout
        self.original_user_id = original_user_id
    
    @discord.ui.button(label="Continue", style=discord.ButtonStyle.primary, emoji="▶️")
    async def continue_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Anyone can click - no user restriction
        await interaction.response.defer()
        
        # Process "continue" for the original player
        await process_continue_action(interaction, self.original_user_id)
    
    async def on_timeout(self):
        # Disable the button after timeout
        for item in self.children:
            item.disabled = True

def sync_campaign_context_with_database(guild_id: str):
    """Sync in-memory campaign context with database state"""
    if not DATABASE_AVAILABLE:
        return
    
    try:
        # ✅ FIXED: Ensure guild_id is string for database operations
        if isinstance(guild_id, int):
            guild_id = str(guild_id)
        
        print(f"🔄 Syncing campaign context for guild {guild_id}")
        
        # Get current episode from database
        current_episode = EpisodeOperations.get_current_episode(guild_id)
        if current_episode:
            campaign_context["current_episode"] = current_episode.episode_number
            campaign_context["episode_active"] = True
            campaign_context["episode_start_time"] = current_episode.start_time
            campaign_context["guild_id"] = guild_id
            
            # Load session history from database
            if current_episode.session_history:
                campaign_context["session_history"] = current_episode.session_history
            
            print(f"✅ Synced campaign context with Episode {current_episode.episode_number}")
        
        # Get guild settings including current scene
        guild_settings = GuildOperations.get_guild_settings(guild_id)
        if guild_settings:
            # ✅ FIXED: Safe conversion to int for voice dictionaries
            try:
                guild_id_int = int(guild_id) if guild_id.isdigit() else None
                if guild_id_int:
                    # Sync voice settings with database
                    voice_speed[guild_id_int] = guild_settings.get('voice_speed', 1.25)
                    tts_enabled[guild_id_int] = guild_settings.get('tts_enabled', False)
            except (ValueError, TypeError) as e:
                print(f"⚠️ Could not convert guild_id {guild_id} to int for voice settings: {e}")
            
            # Sync current scene if stored in database
            if 'current_scene' in guild_settings and guild_settings['current_scene']:
                campaign_context["current_scene"] = guild_settings['current_scene']
                print(f"✅ Synced scene from database")
            
            print(f"✅ Synced guild settings for {guild_id}")
        
        # If no scene in database, try to get from last completed episode
        if campaign_context["current_scene"] == "The village of Nightstone sits eerily quiet. Giant-sized boulders litter the village square, and not a soul can be seen moving in the streets. The party approaches the mysteriously open gates...":
            try:
                if hasattr(EpisodeOperations, 'get_last_completed_episode'):
                    last_episode = None
                    if hasattr(EpisodeOperations, 'get_last_completed_episode'):
                        last_episode = EpisodeOperations.get_last_completed_episode(guild_id)
                    else:
                        print("⚠️ get_last_completed_episode method not found on EpisodeOperations")
                    if last_episode and hasattr(last_episode, 'ending_scene') and last_episode.ending_scene:
                        campaign_context["current_scene"] = last_episode.ending_scene
                        print(f"✅ Loaded scene from last episode: {last_episode.episode_number}")
                else:
                    print("⚠️ get_last_completed_episode method not available")
            except Exception as e:
                print(f"⚠️ Could not load scene from last episode: {e}")
            
    except Exception as e:
        print(f"⚠️ Failed to sync campaign context: {e}")

# Continue Action Processor
async def process_continue_action(interaction: discord.Interaction, user_id: str):
    """Process 'continue' action using unified system"""
    # Get character data
    player_data = campaign_context["players"][user_id]
    char_data = player_data["character_data"]
    character_name = char_data["name"]
    
    guild_id = interaction.guild.id
    channel_id = interaction.channel.id
    voice_will_speak = voice_manager and voice_manager.is_voice_active(guild_id)
    
    # Create processing message
    embed = discord.Embed(color=0x2E8B57)
    embed.add_field(
        name=f"🎭 {character_name} continues...",
        value="*Waiting for the story to unfold...*",
        inline=False
    )
    embed.add_field(
        name="🐉 Donnie the DM- Alpha",
        value="*Alpha Donnie continues the narrative...*",
        inline=False
    )
    
    if voice_will_speak:
        embed.add_field(name="🎤", value="*Alpha Donnie prepares his response...*", inline=False)
    
    # Send processing message
    message = await interaction.followup.send(embed=embed)
    
    # ✅ FIXED: Use "continue" as the player input and get player name
    asyncio.create_task(process_unified_dm_response_background(
        user_id, "continue", message, character_name, char_data, 
        player_data["player_name"],  # ✅ FIXED: Get player name from player_data
        guild_id, channel_id, voice_will_speak
    ))

def extract_npc_names_fast(text: str) -> list:
    """FAST NPC name extraction using simple pattern matching"""
    # Quick and dirty NPC detection for background processing
    storm_kings_npcs = [
        "Morak", "Zephyros", "Harshnag", "Serissa", "Zalto", "Imryth",
        "Felgolos", "Claugiyliamatar", "Klauth", "Iymrith"
    ]
    
    common_npc_types = [
        "guard", "captain", "merchant", "innkeeper", "villager", "priest",
        "mayor", "blacksmith", "tavern keeper", "shopkeeper"
    ]
    
    text_lower = text.lower()
    found_npcs = []
    
    # Check for specific Storm King's Thunder NPCs first
    for npc in storm_kings_npcs:
        if npc.lower() in text_lower:
            found_npcs.append(npc)
    
    # Check for common NPC types
    for npc_type in common_npc_types:
        if npc_type in text_lower and npc_type.title() not in found_npcs:
            found_npcs.append(npc_type.title())
    
    return found_npcs[:3]  # Limit to 3 for speed

def extract_locations_fast(text: str) -> list:
    """FAST location extraction for world state updates"""
    storm_kings_locations = [
        "Nightstone", "Triboar", "Waterdeep", "Neverwinter", "Bryn Shander",
        "Ironslag", "Maelstrom", "Eye of the All-Father", "Lyn Armaal"
    ]
    
    text_lower = text.lower()
    found_locations = []
    
    for location in storm_kings_locations:
        if location.lower() in text_lower:
            found_locations.append(location)
    
    return found_locations[:2]  # Limit to 2 for speed

# ⚡ PERFORMANCE MONITORING FUNCTIONS

def log_performance_metrics(start_time: float, operation: str):
    """Log performance metrics for monitoring"""
    elapsed = time.time() - start_time
    
    if elapsed > 5.0:
        print(f"🚨 SLOW {operation}: {elapsed:.2f}s")
    elif elapsed > 3.0:
        print(f"⚠️ MEDIUM {operation}: {elapsed:.2f}s")
    else:
        print(f"✅ FAST {operation}: {elapsed:.2f}s")
    
    return elapsed


async def handle_dm_response_error(message, user_id: str, error_msg: str = "*Donnie pauses momentarily...*"):
    """Centralized error handling for DM response failures"""
    try:
        embed = message.embeds[0]
        for i, field in enumerate(embed.fields):
            if field.name == "🐉 Donnie the DM":
                embed.set_field_at(i, name="🐉 Donnie the DM", value=error_msg, inline=False)
                break
        
        view = ContinueView(user_id)
        await message.edit(embed=embed, view=view)
    except Exception as e:
        print(f"Error in error handler: {e}")

# Configuration helper
def configure_performance_mode(fast_mode: bool = True):
    """Configure performance settings"""
    global MAX_MEMORIES_FAST, BACKGROUND_PROCESSING, MAX_RESPONSE_LENGTH
    
    if fast_mode:
        MAX_MEMORIES_FAST = 2  # Fewer memories for speed
        BACKGROUND_PROCESSING = True
        MAX_RESPONSE_LENGTH = 550  # Shorter responses
        print("⚡ PERFORMANCE MODE: Fast memory retrieval with background processing")
    else:
        MAX_MEMORIES_FAST = 5  # More memories
        BACKGROUND_PROCESSING = True
        MAX_RESPONSE_LENGTH = 600  # Longer responses
        print("🧠 QUALITY MODE: Full memory features with background processing")

def create_tts_version(dm_response: str) -> str:
    """Create TTS-optimized version of DM response"""
    # Clean for TTS
    return dm_response.replace("**", "").replace("*", "")

# Continuation functionality removed - not implemented in this version

# Enhanced Background Processor with Memory Integration
async def process_unified_dm_response_background(user_id: str, player_input: str, message, 
                                               character_name: str, char_data: dict, 
                                               player_name: str, guild_id: int, channel_id: int, 
                                               voice_will_speak: bool):
    """UNIFIED background processing - single response generation path"""
    try:
        guild_id_str = str(guild_id)
        
        # Ensure guild_id is set in context
        if campaign_context.get("guild_id") != guild_id_str:
            campaign_context["guild_id"] = guild_id_str
        
        print(f"🎯 Unified background processing for {character_name}")
        
        # Get episode ID
        episode_id = campaign_context.get("current_episode", 1)
        if DATABASE_AVAILABLE:
            try:
                current_episode = EpisodeOperations.get_current_episode(guild_id_str)
                if current_episode:
                    episode_id = current_episode.id
            except:
                pass
        
        # ✅ SINGLE RESPONSE GENERATION using unified system
        if UNIFIED_RESPONSE_AVAILABLE:
            try:
                dm_response, response_mode = await generate_dm_response(
                    user_id=user_id,
                    player_input=player_input,
                    guild_id=guild_id_str,
                    episode_id=episode_id
                )
                
                print(f"✅ Response generated using {response_mode} mode")
                
            except Exception as e:
                print(f"❌ Unified response error: {e}")
                # Emergency fallback
                dm_response = "Donnie pauses thoughtfully as the giants' threat looms over the Sword Coast..."
                response_mode = "emergency_fallback"
        else:
            # Basic fallback if unified system not available
            dm_response = "Donnie considers the situation as the giant crisis unfolds around you..."
            response_mode = "basic_fallback"
        
        # Update Discord message
        tts_text = create_tts_version(dm_response)
        
        embed = message.embeds[0]
        for i, field in enumerate(embed.fields):
            if field.name == "🐉 Donnie the DM":
                # Include response mode in Discord message for debugging (only if not enhanced memory)
                if response_mode != "enhanced_memory" and len(dm_response) < 400:
                    mode_indicator = f" *({response_mode})*"
                    embed.set_field_at(i, name="🐉 Donnie the DM", value=dm_response + mode_indicator, inline=False)
                else:
                    embed.set_field_at(i, name="🐉 Donnie the DM", value=dm_response, inline=False)
                break
        
        view = ContinueView(user_id)
        await message.edit(embed=embed, view=view)
        
        # Background memory storage (only if enhanced memory was used)
        if UNIFIED_RESPONSE_AVAILABLE and response_mode == "enhanced_memory":
            asyncio.create_task(store_interaction_background(
                guild_id_str, episode_id, user_id, player_input, dm_response
            ))
        
        # Voice processing (unchanged)
        # Voice processing with enhanced audio
        if voice_will_speak and voice_manager:
            await voice_manager.speak_text(guild_id, tts_text, character_name)
            
    except Exception as e:
        print(f"❌ Unified background processing error: {e}")
        import traceback
        traceback.print_exc()
        await handle_dm_response_error(message, user_id)

async def process_unified_dm_response_background_with_combat(user_id: str, player_input: str, message, 
                                                           character_name: str, char_data: dict, 
                                                           player_name: str, guild_id: int, channel_id: int, 
                                                           voice_will_speak: bool):
    """ENHANCED background processing with combat integration"""
    try:
        guild_id_str = str(guild_id)
        
        # Ensure guild_id is set in context
        if campaign_context.get("guild_id") != guild_id_str:
            campaign_context["guild_id"] = guild_id_str
        
        print(f"🎯⚔️ Enhanced combat processing for {character_name} in channel {channel_id}")
        
        # Get episode ID
        episode_id = campaign_context.get("current_episode", 1)
        if DATABASE_AVAILABLE:
            try:
                current_episode = EpisodeOperations.get_current_episode(guild_id_str)
                if current_episode:
                    episode_id = current_episode.id
            except:
                pass
        
        # ✅ ENHANCED: Generate response with combat integration
        if UNIFIED_RESPONSE_AVAILABLE:
            try:
                # Check if the enhanced unified system supports combat
                if (unified_response_system_instance and 
                    hasattr(unified_response_system_instance, '_generate_response_with_combat')):
                    
                    print("🎯⚔️ Using combat-integrated response generation")
                    dm_response, response_mode = await unified_response_system_instance._generate_response_with_combat(
                        user_id=user_id,
                        player_input=player_input,
                        guild_id=guild_id_str,
                        episode_id=episode_id,
                        channel_id=channel_id,  # Pass channel_id for combat
                        character_name=character_name
                    )
                    
                    print(f"✅ Combat-integrated response generated using {response_mode} mode")
                    
                else:
                    # Fallback to existing unified system
                    print("🎯 Using standard unified response (combat integration not available)")
                    dm_response, response_mode = await generate_dm_response(
                        user_id=user_id,
                        player_input=player_input,
                        guild_id=guild_id_str,
                        episode_id=episode_id
                    )
                
            except Exception as e:
                print(f"❌ Enhanced combat response error: {e}")
                # Emergency fallback to existing system
                await process_unified_dm_response_background(
                    user_id, player_input, message, character_name, char_data, 
                    player_name, guild_id, channel_id, voice_will_speak
                )
                return
        else:
            # Basic fallback if unified system not available
            dm_response = "Donnie considers the situation as the giant crisis unfolds around you..."
            response_mode = "basic_fallback"
        
        # Update Discord message
        tts_text = create_tts_version(dm_response)
        
        embed = message.embeds[0]
        for i, field in enumerate(embed.fields):
            if field.name == "🐉 Donnie the DM":
                # Include response mode indicator for debugging
                if response_mode not in ["enhanced_memory", "enhanced_memory_v2"] and len(dm_response) < 400:
                    mode_indicator = f" *({response_mode})*"
                    embed.set_field_at(i, name="🐉 Donnie the DM", value=dm_response + mode_indicator, inline=False)
                else:
                    embed.set_field_at(i, name="🐉 Donnie the DM", value=dm_response, inline=False)
                break
        
        view = ContinueView(user_id)
        await message.edit(embed=embed, view=view)
        
        # Background memory storage (only if enhanced memory was used)
        if UNIFIED_RESPONSE_AVAILABLE and response_mode in ["enhanced_memory", "enhanced_memory_v2"]:
            asyncio.create_task(store_interaction_background(
                guild_id_str, episode_id, user_id, player_input, dm_response
            ))
        
        # Voice processing (unchanged)
        # Voice processing with enhanced audio
        if voice_will_speak and voice_manager:
            await voice_manager.speak_text(guild_id, tts_text, character_name)
            
    except Exception as e:
        print(f"❌ Enhanced combat processing error: {e}")
        import traceback
        traceback.print_exc()
        # Safe fallback to existing processor
        await process_unified_dm_response_background(
            user_id, player_input, message, character_name, char_data, 
            player_name, guild_id, channel_id, voice_will_speak
        )

async def process_unified_dm_response_background_enhanced(user_id: str, player_input: str, message, 
                                                        character_name: str, char_data: dict, 
                                                        player_name: str, guild_id: int, channel_id: int, 
                                                        voice_will_speak: bool):
    """Enhanced version with structured memory - SAFE VERSION"""
    try:
        guild_id_str = str(guild_id)
        
        # Get episode ID
        episode_id = campaign_context.get("current_episode", 1)
        if DATABASE_AVAILABLE:
            try:
                current_episode = EpisodeOperations.get_current_episode(guild_id_str)
                if current_episode:
                    episode_id = current_episode.id
            except:
                pass
        
        # SAFE: Try enhanced method first, fall back to original
        if (UNIFIED_RESPONSE_AVAILABLE and unified_response_system_instance and 
            hasattr(unified_response_system_instance, '_generate_enhanced_memory_response_v2')):
            
            try:
                dm_response = await unified_response_system_instance._generate_enhanced_memory_response_v2(
                    user_id=user_id,
                    player_input=player_input,
                    guild_id=guild_id_str,
                    episode_id=episode_id,
                    character_name=character_name,
                    channel_id=channel_id
                )
                response_mode = "enhanced_memory_v2"
                print(f"✅ Enhanced structured response generated")
                
            except Exception as e:
                print(f"⚠️ Enhanced method failed, using standard: {e}")
                # SAFE: Fall back to existing method
                dm_response, response_mode = await generate_dm_response(
                    user_id=user_id,
                    player_input=player_input,
                    guild_id=guild_id_str,
                    episode_id=episode_id
                )
        else:
            # SAFE: Use existing method
            dm_response, response_mode = await generate_dm_response(
                user_id=user_id,
                player_input=player_input,
                guild_id=guild_id_str,
                episode_id=episode_id
            )
        
        # Update Discord message
        tts_text = create_tts_version(dm_response)
        
        embed = message.embeds[0]
        for i, field in enumerate(embed.fields):
            if field.name == "🐉 Donnie the DM":
                # Include response mode in Discord message for debugging (only if not enhanced memory)
                if response_mode != "enhanced_memory_v2" and len(dm_response) < 400:
                    mode_indicator = f" *({response_mode})*"
                    embed.set_field_at(i, name="🐉 Donnie the DM", value=dm_response + mode_indicator, inline=False)
                else:
                    embed.set_field_at(i, name="🐉 Donnie the DM", value=dm_response, inline=False)
                break
        
        view = ContinueView(user_id)
        await message.edit(embed=embed, view=view)
        
        # Background memory storage (only if enhanced memory was used)
        if UNIFIED_RESPONSE_AVAILABLE and response_mode == "enhanced_memory_v2":
            asyncio.create_task(store_interaction_background(
                guild_id_str, episode_id, user_id, player_input, dm_response
            ))
        
        # Voice processing (unchanged)
        # Voice processing with enhanced audio
        if voice_will_speak and voice_manager:
            await voice_manager.speak_text(guild_id, tts_text, character_name)
            
    except Exception as e:
        print(f"❌ Enhanced background processing error: {e}")
        import traceback
        traceback.print_exc()
        # SAFE: Fall back to original function
        await process_unified_dm_response_background(
            user_id, player_input, message, character_name, char_data, 
            player_name, guild_id, channel_id, voice_will_speak
        )


def optimize_text_for_tts(text: str) -> str:
    """Optimize text specifically for faster, clearer TTS delivery"""
    import re
    
    # Remove excessive formatting
    clean_text = text.replace("**", "").replace("*", "").replace("_", "")
    
    # Spell out dice notation for better pronunciation
    clean_text = re.sub(r'\b(\d+)d(\d+)\b', r'\1 dee \2', clean_text)
    clean_text = re.sub(r'\bDC\s*(\d+)\b', r'difficulty class \1', clean_text)
    clean_text = re.sub(r'\bAC\s*(\d+)\b', r'armor class \1', clean_text)
    clean_text = re.sub(r'\bHP\s*(\d+)\b', r'hit points \1', clean_text)
    
    # Simplify complex words for faster speech
    replacements = {
        "immediately": "now",
        "suddenly": "",
        "extremely": "very",
        "tremendous": "huge",
        "magnificent": "great",
        "extraordinary": "amazing"
    }
    
    for old, new in replacements.items():
        clean_text = clean_text.replace(old, new)
    
    # Remove redundant phrases
    clean_text = re.sub(r'\b(very|quite|rather|extremely|incredibly|tremendously)\s+', '', clean_text)
    clean_text = re.sub(r'\b(suddenly|immediately|quickly|slowly)\s+', '', clean_text)
    
    # Clean up extra spaces
    clean_text = re.sub(r'\s+', ' ', clean_text).strip()
    
    return clean_text


@bot.tree.command(name="debug_memory_detailed", description="Detailed memory system diagnostics (Admin only)")
async def debug_memory_detailed(interaction: discord.Interaction):
    """FIXED: Comprehensive memory system diagnostics"""
    
    if not is_admin(interaction):
        await interaction.response.send_message("❌ Admin only!", ephemeral=True)
        return
    
    guild_id = str(interaction.guild.id)
    
    embed = discord.Embed(
        title="🔍 Detailed Memory System Diagnostics",
        description="Comprehensive analysis of memory system components",
        color=0x4169E1
    )
    
    # Check database availability
    db_status = "✅ Available" if DATABASE_AVAILABLE else "❌ Not Available"
    embed.add_field(name="💾 Database", value=db_status, inline=True)
    
    # Check memory adapter
    if memory_database_adapter:
        adapter_status = f"✅ Initialized (Real ops: {'✅' if hasattr(memory_database_adapter, 'memory_ops') and memory_database_adapter.memory_ops else '❌'})"
    else:
        adapter_status = "❌ Not Initialized"
    embed.add_field(name="🔌 Memory Adapter", value=adapter_status, inline=True)
    
    # Check unified response system
    if unified_response_system_instance:
        unified_status = f"✅ Active (Memory: {'✅' if unified_response_system_instance.persistent_memory_available else '❌'})"
    else:
        unified_status = "❌ Not Active"
    embed.add_field(name="🎯 Unified Response", value=unified_status, inline=True)
    
    # Check memory tables
    if DATABASE_AVAILABLE:
        try:
            from database.database import get_db_connection
            conn = get_db_connection()
            cursor = conn.cursor()
            
            table_status = []
            memory_tables = ['conversation_memories', 'npc_memories', 'memory_consolidation', 'world_state']
            
            for table in memory_tables:
                try:
                    cursor.execute(f"SELECT COUNT(*) FROM {table} WHERE campaign_id = ?", (guild_id,))
                    count = cursor.fetchone()[0]
                    table_status.append(f"✅ {table}: {count} records")
                except:
                    table_status.append(f"❌ {table}: missing/error")
            
            embed.add_field(
                name="📊 Memory Tables",
                value="\n".join(table_status),
                inline=False
            )
            
            conn.close()
            
        except Exception as e:
            embed.add_field(name="📊 Memory Tables", value=f"❌ Error: {e}", inline=False)
    
    # Test memory operations
    if memory_database_adapter and hasattr(memory_database_adapter, 'memory_ops') and memory_database_adapter.memory_ops:
        try:
            # Test store operation
            test_result = await memory_database_adapter.store_conversation_memory(
                campaign_id=guild_id,
                episode_id=1,
                user_id="test",
                character_name="Test Character",
                player_input="Test input",
                dm_response="Test response"
            )
            
            store_status = "✅ Working" if test_result else "❌ Failed"
            
            # Test retrieve operation  
            memories = await memory_database_adapter.retrieve_relevant_memories(
                campaign_id=guild_id,
                query="test",
                max_memories=1
            )
            
            retrieve_status = f"✅ Working ({len(memories)} results)" if isinstance(memories, list) else "❌ Failed"
            
            embed.add_field(
                name="🧪 Memory Operations Test",
                value=f"Store: {store_status}\nRetrieve: {retrieve_status}",
                inline=True
            )
            
        except Exception as e:
            embed.add_field(name="🧪 Memory Operations Test", value=f"❌ Error: {e}", inline=True)
    
    await interaction.response.send_message(embed=embed, ephemeral=True)

# ====== BOT DISCONNECT HANDLER ======
@bot.event
async def on_disconnect():
    """FIXED: Proper cleanup with global variable access"""
    global episode_commands, character_progression, unified_response_system_instance
    
    print("🔌 Bot disconnecting...")
    
    # Save any pending changes to database
    if DATABASE_AVAILABLE:
        try:
            # Update all active guild settings
            for guild_id in voice_speed.keys():
                update_database_from_campaign_context(str(guild_id))
            
            close_database()
            print("✅ Database connections closed and data saved")
        except Exception as e:
            print(f"⚠️ Error during database cleanup: {e}")
    
    # Clean up global references
    episode_commands = None
    character_progression = None
    unified_response_system_instance = None
    
    print("👋 Goodbye!")

@bot.event
async def on_guild_join(guild):
    """Initialize database settings when bot joins a new guild"""
    if DATABASE_AVAILABLE:
        try:
            guild_id = str(guild.id)
            
            # Initialize guild settings in database
            GuildOperations.update_guild_settings(
                guild_id,
                voice_speed=1.25,
                voice_quality='smart',
                tts_enabled=False,
                current_episode=0,
                current_scene=""  # Initialize with empty scene
            )
            
            print(f"✅ Initialized database settings for guild: {guild.name}")
            
        except Exception as e:
            print(f"⚠️ Failed to initialize guild settings: {e}")

@bot.event  
async def on_guild_remove(guild):
    """Clean up when bot leaves a guild"""
    guild_id = guild.id  # This is already an int
    
    # Clean up in-memory state
    if guild_id in voice_clients:
        try:
            await voice_clients[guild_id].disconnect()
            del voice_clients[guild_id]
        except:
            pass
    
    # Clean up other guild-specific data (use int keys)
    voice_speed.pop(guild_id, None)
    tts_enabled.pop(guild_id, None) 
    voice_queue.pop(guild_id, None)
    
    print(f"🧹 Cleaned up data for guild: {guild.name}")

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return
    
    # Auto-sync campaign context with database when messages are received
    if DATABASE_AVAILABLE and message.guild:
        guild_id = str(message.guild.id)  # Convert to string for database operations
        
        # Only sync occasionally to avoid performance issues
        if random.random() < 0.1:  # 10% chance per message
            sync_campaign_context_with_database(guild_id)
    
    await bot.process_commands(message)

# ====== VOICE CHANNEL COMMANDS ======

# Add these VOICE FUNCTIONS at the top of main.py, right after imports and before @bot.event:

# ====== VOICE SYSTEM FUNCTIONS (DEFINE EARLY) ======
import asyncio
import os
from io import BytesIO

# Voice system globals (ensure these are defined early)
voice_clients = {}
tts_enabled = {}
voice_speed = {}
voice_queue = {}

async def add_to_voice_queue(guild_id: int, text: str, speaker: str, message=None):
    """Add text to voice queue - CRITICAL: This function must be available early"""
    if not FFMPEG_AVAILABLE:
        print(f"⚠️ FFmpeg not available - skipping voice for guild {guild_id}")
        return
        
    if guild_id not in voice_clients or not voice_clients[guild_id].is_connected():
        print(f"⚠️ Voice not connected for guild {guild_id} - text: {text[:50]}...")
        return
        
    if not tts_enabled.get(guild_id, False):
        print(f"⚠️ TTS disabled for guild {guild_id}")
        return
    
    try:
        # Add to queue if it exists
        if guild_id not in voice_queue:
            voice_queue[guild_id] = []
        
        voice_queue[guild_id].append({
            'text': text,
            'speaker': speaker,
            'message': message
        })
        
        # Process queue if not already processing
        if not hasattr(voice_clients[guild_id], '_processing_queue'):
            voice_clients[guild_id]._processing_queue = True
            await process_voice_queue(guild_id)
            
    except Exception as e:
        print(f"❌ Voice queue error for guild {guild_id}: {e}")

async def process_voice_queue(guild_id: int):
    """Process voice queue for a guild"""
    if guild_id not in voice_clients or not voice_clients[guild_id].is_connected():
        return
        
    voice_client = voice_clients[guild_id]
    
    try:
        while voice_queue.get(guild_id) and voice_client.is_connected():
            if voice_client.is_playing():
                await asyncio.sleep(0.5)
                continue
                
            item = voice_queue[guild_id].pop(0)
            await speak_text(guild_id, item['text'], item['speaker'], item['message'])
            
    except Exception as e:
        print(f"❌ Error processing voice queue for guild {guild_id}: {e}")
    finally:
        if hasattr(voice_client, '_processing_queue'):
            voice_client._processing_queue = False

async def speak_text(guild_id: int, text: str, speaker: str, message=None):
    """Speak text using TTS"""
    if not FFMPEG_AVAILABLE or guild_id not in voice_clients:
        return
        
    voice_client = voice_clients[guild_id]
    if not voice_client.is_connected() or not tts_enabled.get(guild_id, False):
        return
    
    try:
        # Get OpenAI API key
        openai_api_key = os.getenv('OPENAI_API_KEY')
        if not openai_api_key:
            print("⚠️ OPENAI_API_KEY not found - cannot generate TTS")
            return
        
        # Clean text for TTS
        clean_text = create_tts_version(text)
        if len(clean_text.strip()) == 0:
            return
            
        # Generate TTS using OpenAI
        import aiohttp
        
        tts_data = {
            "model": "tts-1",
            "input": clean_text[:4000],  # OpenAI limit
            "voice": "fable",  # Donnie's character voice
            "speed": voice_speed.get(guild_id, 1.25)
        }
        
        headers = {
            "Authorization": f"Bearer {openai_api_key}",
            "Content-Type": "application/json"
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://api.openai.com/v1/audio/speech",
                json=tts_data,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                if response.status == 200:
                    audio_data = await response.read()
                    
                    # Play audio
                    audio_source = discord.FFmpegPCMAudio(
                        BytesIO(audio_data),
                        pipe=True,
                        options='-f mp3'
                    )
                    
                    if not voice_client.is_playing():
                        voice_client.play(audio_source)
                        
                        # Update message if provided
                        if message:
                            try:
                                embed = message.embeds[0] if message.embeds else None
                                if embed:
                                    for i, field in enumerate(embed.fields):
                                        if field.name == "🎤":
                                            embed.set_field_at(i, name="🎤", value=f"*Donnie responds to {speaker}*", inline=False)
                                            break
                                    await message.edit(embed=embed)
                            except Exception as e:
                                print(f"⚠️ Message update failed: {e}")
                else:
                    print(f"❌ TTS API error: {response.status}")
                    
    except Exception as e:
        print(f"❌ TTS error for guild {guild_id}: {e}")

def create_tts_version(dm_response: str) -> str:
    """Create TTS-optimized version of DM response"""
    # Remove Discord formatting
    clean_text = dm_response.replace("**", "").replace("*", "")
    
    # Remove excessive punctuation
    clean_text = clean_text.replace("...", ".")
    
    # Remove action descriptions in brackets
    import re
    clean_text = re.sub(r'\[.*?\]', '', clean_text)
    
    # Remove dice roll results (keep descriptions)
    clean_text = re.sub(r'\(\d+\s*[+-]\s*\d+\s*=\s*\d+\)', '', clean_text)
    
    # Clean up spacing
    clean_text = ' '.join(clean_text.split())
    
    return clean_text.strip()

def is_voice_active(guild_id: int) -> bool:
    """Check if voice is active for guild"""
    return (guild_id in voice_clients and 
            voice_clients[guild_id].is_connected() and 
            tts_enabled.get(guild_id, False))

# ====== HELPER FUNCTIONS (PRESERVE YOUR EXISTING ONES) ======
def is_user_in_voice(interaction):
    """Check if user is in a voice channel"""
    return (isinstance(interaction.user, discord.Member) and 
            interaction.user.voice and 
            interaction.user.voice.channel)

def get_voice_channel(interaction):
    """Get the user's voice channel"""
    if isinstance(interaction.user, discord.Member) and interaction.user.voice:
        return interaction.user.voice.channel
    return None

@bot.tree.command(name="response_status", description="Check DM response system status")
async def check_response_status(interaction: discord.Interaction):
    """Check the status of the unified response system"""
    
    embed = discord.Embed(
        title="🎯 DM Response System Status",
        description="Current status of all response generation systems",
        color=0x4169E1
    )
    
    if UNIFIED_RESPONSE_AVAILABLE:
        try:
            status = get_response_system_status()
            
            for system, status_text in status.items():
                embed.add_field(
                    name=f"🔧 {system.replace('_', ' ').title()}",
                    value=status_text,
                    inline=True
                )
            
            # Show recent response modes if available
            recent_history = campaign_context.get("session_history", [])[-3:]
            if recent_history:
                mode_history = []
                for entry in recent_history:
                    mode = entry.get("mode", "unknown")
                    player = entry.get("player", "Unknown")
                    mode_history.append(f"• {player}: {mode}")
                
                embed.add_field(
                    name="📊 Recent Response Modes",
                    value="\n".join(mode_history) or "No recent history",
                    inline=False
                )
            
            embed.color = 0x32CD32
        except Exception as e:
            embed.add_field(
                name="❌ System Error",
                value=f"Error getting status: {e}",
                inline=False
            )
            embed.color = 0xFF4500
    else:
        embed.add_field(
            name="❌ System Status",
            value="Unified response system not available",
            inline=False
        )
        embed.color = 0xFF4500
    
    await interaction.response.send_message(embed=embed, ephemeral=True)                

@bot.tree.command(name="leave_voice", description="Donnie leaves the voice channel")
async def leave_voice_channel(interaction: discord.Interaction):
    """Leave the voice channel"""
    if not interaction.guild:
        await interaction.response.send_message("❌ This command can only be used in a server!", ephemeral=True)
        return
        
    guild_id = interaction.guild.id
    
    if guild_id not in voice_clients or not voice_clients[guild_id].is_connected():
        await interaction.response.send_message("❌ Donnie isn't in a voice channel!", ephemeral=True)
        return
    
    try:
        await voice_clients[guild_id].disconnect()
        del voice_clients[guild_id]
        tts_enabled[guild_id] = False
        if guild_id in voice_speed:
            del voice_speed[guild_id]  # Clean up speed setting
        if guild_id in voice_queue:
            del voice_queue[guild_id]  # Clean up voice queue
        
        embed = discord.Embed(
            title="👋 Donnie the DM Departs",
            description="*Donnie's expressive voice fades away as he steps back from the microphone*",
            color=0xFF4500
        )
        
        embed.add_field(
            name="🔇 Voice Disabled",
            value="Use `/join_voice` to have Donnie speak again!",
            inline=False
        )
        
        await interaction.response.send_message(embed=embed)
        
    except Exception as e:
        await interaction.response.send_message(f"❌ Error leaving voice channel: {str(e)}", ephemeral=True)

@bot.tree.command(name="mute_donnie", description="Mute Donnie's voice (stay in channel)")
async def mute_tts(interaction: discord.Interaction):
    """Disable TTS while staying in voice channel"""
    if not interaction.guild:
        await interaction.response.send_message("❌ This command can only be used in a server!", ephemeral=True)
        return
        
    guild_id = interaction.guild.id
    
    if guild_id not in voice_clients or not voice_clients[guild_id].is_connected():
        await interaction.response.send_message("❌ Donnie isn't in a voice channel!", ephemeral=True)
        return
    
    tts_enabled[guild_id] = False
    
    embed = discord.Embed(
        title="🔇 Donnie Muted",
        description="Donnie remains in the voice channel but won't speak responses aloud",
        color=0xFFD700
    )
    
    embed.add_field(
        name="ℹ️ Note",
        value="Use `/unmute_donnie` to re-enable voice narration",
        inline=False
    )
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="unmute_donnie", description="Unmute Donnie's voice")
async def unmute_tts(interaction: discord.Interaction):
    """Re-enable TTS in voice channel"""
    if not interaction.guild:
        await interaction.response.send_message("❌ This command can only be used in a server!", ephemeral=True)
        return
        
    guild_id = interaction.guild.id
    
    if guild_id not in voice_clients or not voice_clients[guild_id].is_connected():
        await interaction.response.send_message("❌ Donnie isn't in a voice channel! Use `/join_voice` first.", ephemeral=True)
        return
    
    tts_enabled[guild_id] = True
    
    embed = discord.Embed(
        title="🔊 Donnie Unmuted",
        description="Donnie's expressive voice returns to narrate your adventure!",
        color=0x32CD32
    )
    
    await interaction.response.send_message(embed=embed)

# Voice quality preferences per guild
voice_quality = {}  # Guild ID -> "speed" or "quality"

@bot.tree.command(name="donnie_speed", description="Adjust Donnie's speaking speed")
@app_commands.describe(speed="Speaking speed (0.5 = very slow, 1.0 = normal, 1.5 = fast, 2.0 = very fast)")
async def adjust_voice_speed(interaction: discord.Interaction, speed: float):
    """Adjust TTS speaking speed"""
    if not interaction.guild:
        await interaction.response.send_message("❌ This command can only be used in a server!", ephemeral=True)
        return
        
    guild_id = interaction.guild.id
    
    if guild_id not in voice_clients or not voice_clients[guild_id].is_connected():
        await interaction.response.send_message("❌ Donnie isn't in a voice channel! Use `/join_voice` first.", ephemeral=True)
        return
    
    # Validate speed range
    if speed < 0.25 or speed > 4.0:
        await interaction.response.send_message("❌ Speed must be between 0.25 and 4.0!", ephemeral=True)
        return
    
    # Update speed
    voice_speed[guild_id] = speed
    
    # Create response with speed descriptions
    if speed < 0.7:
        speed_desc = "Very Slow & Dramatic"
    elif speed < 0.9:
        speed_desc = "Slow & Theatrical"
    elif speed < 1.1:
        speed_desc = "Normal Pace"
    elif speed < 1.3:
        speed_desc = "Fast & Engaging"
    elif speed < 1.7:
        speed_desc = "Very Fast"
    else:
        speed_desc = "Extremely Fast"
    
    embed = discord.Embed(
        title="⚡ Donnie's Speed Adjusted!",
        description=f"Speed set to **{speed}x** ({speed_desc})",
        color=0x32CD32
    )
    
    embed.add_field(
        name="🎤 Streamlined Performance",
        value="Donnie uses optimized responses and enhanced text processing for faster gameplay!",
        inline=False
    )
    
    # Test the new speed with a quick message
    if tts_enabled.get(guild_id, False):
        test_message = f"Speed adjusted to {speed}x. This is how fast I speak now!"
        await add_to_voice_queue(guild_id, test_message, "Speed Test")
    
    await interaction.response.send_message(embed=embed)

# ====== CHARACTER MANAGEMENT COMMANDS ======

@bot.tree.command(name="character", description="Register your character for the Storm King's Thunder campaign")
@app_commands.describe(
    name="Your character's name",
    race="Character race (Human, Elf, Dwarf, etc.)",
    character_class="Character class (Fighter, Wizard, Rogue, etc.)",
    level="Character level (1-20)",
    background="Character background (Folk Hero, Acolyte, etc.)",
    stats="Key ability scores (STR 16, DEX 14, CON 15, etc.)",
    equipment="Important weapons, armor, and magical items",
    spells="Known spells (if applicable)",
    affiliations="Factions, organizations, or important relationships",
    personality="Key personality traits, ideals, bonds, and flaws"
)
async def register_character(interaction: discord.Interaction, 
                           name: str,
                           race: str, 
                           character_class: str,
                           level: int,
                           background: Optional[str] = None,
                           stats: Optional[str] = None,
                           equipment: Optional[str] = None,
                           spells: Optional[str] = None,
                           affiliations: Optional[str] = None,
                           personality: Optional[str] = None):
    """Register a detailed character for the campaign"""
    user_id = str(interaction.user.id)
    player_name = interaction.user.display_name
    
    # ✅ FIXED: Set guild_id in campaign context if not set
    if campaign_context["guild_id"] is None:
        guild_id_int = interaction.guild.id
        guild_id_str = str(guild_id_int)
        campaign_context["guild_id"] = guild_id_str
        print(f"✅ Set guild_id in campaign_context: {guild_id_str}")
    
    # Validate level
    if level < 1 or level > 20:
        await interaction.response.send_message("❌ Character level must be between 1 and 20!", ephemeral=True)
        return
    
    # Safely handle optional parameters
    safe_background = background if background is not None else "Unknown"
    safe_stats = stats if stats is not None else "Standard array"
    safe_equipment = equipment if equipment is not None else "Basic adventuring gear"
    safe_affiliations = affiliations if affiliations is not None else "None"
    safe_personality = personality if personality is not None else "To be determined in play"
    
    # Handle spells with class detection
    if spells is not None:
        safe_spells = spells
    else:
        spellcaster_classes = ["wizard", "cleric", "sorcerer", "warlock", "bard", "druid", "paladin", "ranger"]
        if any(cls in character_class.lower() for cls in spellcaster_classes):
            safe_spells = "Basic spells for class"
        else:
            safe_spells = "None"
    
    # Build comprehensive character profile
    character_profile = {
        "name": name,
        "race": race,
        "class": character_class,
        "level": level,
        "background": safe_background,
        "stats": safe_stats,
        "equipment": safe_equipment,
        "spells": safe_spells,
        "affiliations": safe_affiliations,
        "personality": safe_personality,
        "player_name": player_name,
        "discord_user_id": user_id
    }
    
    # Create formatted character description for Claude
    character_description = f"""
NAME: {character_profile['name']}
PLAYER: {player_name} (Discord ID: {user_id})
RACE & CLASS: {character_profile['race']} {character_profile['class']} (Level {character_profile['level']})
BACKGROUND: {character_profile['background']}
ABILITY SCORES: {character_profile['stats']}
EQUIPMENT: {character_profile['equipment']}
SPELLS: {character_profile['spells']}
AFFILIATIONS: {character_profile['affiliations']}
PERSONALITY: {character_profile['personality']}
"""
    
    # Store using Discord User ID as primary key
    campaign_context["characters"][user_id] = character_description
    campaign_context["players"][user_id] = {
        "user_id": user_id,
        "player_name": player_name,
        "character_data": character_profile,
        "character_description": character_description
    }
    
    # Create response embed
    embed = discord.Embed(
        title="🎭 Character Registered Successfully!",
        color=0x32CD32
    )
    
    embed.add_field(
        name=f"⚔️ {character_profile['name']}",
        value=f"**{character_profile['race']} {character_profile['class']}** (Level {character_profile['level']})\n*{character_profile['background']}*\n👤 Player: {player_name}",
        inline=False
    )
    
    if character_profile['stats'] != "Standard array":
        embed.add_field(name="📊 Ability Scores", value=character_profile['stats'], inline=True)
    
    if character_profile['equipment'] != "Basic adventuring gear":
        embed.add_field(name="⚔️ Equipment", value=character_profile['equipment'][:100] + ("..." if len(character_profile['equipment']) > 100 else ""), inline=True)
    
    if character_profile['spells'] not in ["None", "Basic spells for class"]:
        embed.add_field(name="✨ Spells", value=character_profile['spells'][:100] + ("..." if len(character_profile['spells']) > 100 else ""), inline=True)
    
    if character_profile['affiliations'] != "None":
        embed.add_field(name="🏛️ Affiliations", value=character_profile['affiliations'], inline=False)
    
    if character_profile['personality'] != "To be determined in play":
        embed.add_field(name="🎭 Personality", value=character_profile['personality'][:200] + ("..." if len(character_profile['personality']) > 200 else ""), inline=False)
    
    embed.add_field(
        name="⚡ Next Steps",
        value="Start an episode with `/start_episode`, or use `/upload_character_sheet` to import a PDF character sheet, then use `/join_voice` to have Donnie narrate your adventure with streamlined combat!",
        inline=False
    )
    
    if PERSISTENT_MEMORY_AVAILABLE:
        embed.add_field(
            name="🧠 Memory System",
            value="Donnie will remember your character across episodes and sessions!",
            inline=False
        )
    
    if COMBAT_AVAILABLE:
        embed.add_field(
            name="⚔️ Combat System",
            value="Combat will be tracked automatically with separate display messages and initiative tracking!",
            inline=False
        )
    
        embed.set_footer(text="Character bound to your Discord account and ready for enhanced combat!")
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="party", description="View all registered characters in your party")
async def view_party(interaction: discord.Interaction):
    """Show all registered characters"""
    if not campaign_context["characters"]:
        embed = discord.Embed(
            title="🎭 No Characters Registered",
            description="No one has registered their character yet! Use `/character` to introduce yourself.",
            color=0xFF6B6B
        )
        await interaction.response.send_message(embed=embed)
        return
    
    embed = discord.Embed(
        title="🗡️ Your Adventuring Party",
        description="Heroes ready to face the giant threat:",
        color=0x4B0082
    )
    
    for user_id, character_desc in campaign_context["characters"].items():
        if user_id in campaign_context["players"]:
            player_data = campaign_context["players"][user_id]
            char_data = player_data["character_data"]
            current_player_name = player_data["player_name"]
            
            # Create character summary
            char_summary = f"**{char_data['race']} {char_data['class']}** (Level {char_data['level']})"
            if char_data['background'] != "Unknown":
                char_summary += f"\n*{char_data['background']}*"
            
            # Add key equipment if specified
            if char_data['equipment'] != "Basic adventuring gear":
                equipment_brief = char_data['equipment'][:60] + ("..." if len(char_data['equipment']) > 60 else "")
                char_summary += f"\n🎒 {equipment_brief}"
            
            # Add affiliations if any
            if char_data['affiliations'] != "None":
                affiliations_brief = char_data['affiliations'][:50] + ("..." if len(char_data['affiliations']) > 50 else "")
                char_summary += f"\n🏛️ {affiliations_brief}"
            
            embed.add_field(
                name=f"⚔️ {char_data['name']} ({current_player_name})",
                value=char_summary,
                inline=False
            )
    
    embed.set_footer(text=f"Party size: {len(campaign_context['characters'])} heroes ready for adventure!")
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="character_sheet", description="View detailed character information")
@app_commands.describe(player="View another player's character (optional)")
async def view_character_sheet(interaction: discord.Interaction, player: Optional[discord.Member] = None):
    """Show detailed character sheet"""
    target_user = player or interaction.user
    user_id = str(target_user.id)
    
    if user_id not in campaign_context["characters"]:
        embed = discord.Embed(
            title="❌ Character Not Found",
            description=f"No character registered for {target_user.display_name}. Use `/character` to register!",
            color=0xFF6B6B
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    
    # Get character data
    char_data = campaign_context["players"][user_id]["character_data"]
    
    embed = discord.Embed(
        title=f"📜 Character Sheet: {char_data['name']}",
        description=f"**{char_data['race']} {char_data['class']}** (Level {char_data['level']})",
        color=0x4169E1
    )

    embed.add_field(name="📚 Background", value=char_data['background'], inline=True)
    embed.add_field(name="📊 Ability Scores", value=char_data['stats'], inline=True)
    embed.add_field(name="👤 Player", value=target_user.display_name, inline=True)
    embed.add_field(name="⚔️ Equipment & Items", value=char_data['equipment'], inline=False)
    
    if char_data['spells'] not in ["None", "Basic spells for class"]:
        embed.add_field(name="✨ Spells & Abilities", value=char_data['spells'], inline=False)
    
    if char_data['affiliations'] != "None":
        embed.add_field(name="🏛️ Affiliations & Connections", value=char_data['affiliations'], inline=False)
    
    if char_data['personality'] != "To be determined in play":
        embed.add_field(name="🎭 Personality & Roleplay", value=char_data['personality'], inline=False)
    
    embed.set_footer(text="Use /update_character to modify details • /character_progression to view progression")
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="update_character", description="Update specific aspects of your character")
@app_commands.describe(
    aspect="What to update",
    new_value="The new value"
)
@app_commands.choices(aspect=[
    app_commands.Choice(name="Level", value="level"),
    app_commands.Choice(name="Stats/Ability Scores", value="stats"),
    app_commands.Choice(name="Equipment/Items", value="equipment"), 
    app_commands.Choice(name="Spells/Abilities", value="spells"),
    app_commands.Choice(name="Affiliations/Connections", value="affiliations"),
    app_commands.Choice(name="Personality/Roleplay", value="personality")
])
async def update_character(interaction: discord.Interaction, aspect: str, new_value: str):
    """Update specific character aspects"""
    user_id = str(interaction.user.id)
    player_name = interaction.user.display_name
    
    if user_id not in campaign_context["characters"]:
        embed = discord.Embed(
            title="❌ No Character Found",
            description="Please register a character first using `/character`!",
            color=0xFF6B6B
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    
    # Get current character data
    char_data = campaign_context["players"][user_id]["character_data"]
    
    # Update the specified aspect
    if aspect == "level":
        try:
            level = int(new_value)
            if level < 1 or level > 20:
                await interaction.response.send_message("❌ Level must be between 1 and 20! Use `/level_up` to properly track progression.", ephemeral=True)
                return
            char_data["level"] = level
        except ValueError:
            await interaction.response.send_message("❌ Level must be a number!", ephemeral=True)
            return
    else:
        char_data[aspect] = new_value
    
    # Update player name in case it changed
    char_data["player_name"] = player_name
    
    # Rebuild character description for Claude
    character_description = f"""
NAME: {char_data['name']}
PLAYER: {player_name} (Discord ID: {user_id})
RACE & CLASS: {char_data['race']} {char_data['class']} (Level {char_data['level']})
BACKGROUND: {char_data['background']}
ABILITY SCORES: {char_data['stats']}
EQUIPMENT: {char_data['equipment']}
SPELLS: {char_data['spells']}
AFFILIATIONS: {char_data['affiliations']}
PERSONALITY: {char_data['personality']}
"""
    
    # Update stored data
    campaign_context["characters"][user_id] = character_description
    campaign_context["players"][user_id]["character_description"] = character_description
    campaign_context["players"][user_id]["player_name"] = player_name
    
    # Create confirmation embed  
    aspect_names = {
        "level": "⭐ Level",
        "stats": "📊 Ability Scores",
        "equipment": "⚔️ Equipment", 
        "spells": "✨ Spells",
        "affiliations": "🏛️ Affiliations",
        "personality": "🎭 Personality"
    }
    
    embed = discord.Embed(
        title=f"✅ {char_data['name']} Updated!",
        color=0x32CD32
    )
    
    embed.add_field(
        name=f"{aspect_names[aspect]} Updated",
        value=new_value,
        inline=False
    )
    
    embed.set_footer(text="Character changes will be saved to the next episode snapshot")
    await interaction.response.send_message(embed=embed)

# ====== CORE GAMEPLAY COMMANDS ======

@bot.tree.command(name="start", description="Begin your Storm King's Thunder adventure (legacy - use /start_episode)")
async def start_adventure(interaction: discord.Interaction):
    """Start the Storm King's Thunder campaign (legacy command)"""
    
    # Check if we have any characters registered
    if not campaign_context["characters"]:
        embed = discord.Embed(
            title="⚡ Welcome to Storm King's Thunder!",
            description="Before we begin our adventure, we need to know who you are!",
            color=0xFF6B6B
        )
        
        embed.add_field(
            name="🎭 Character Registration Required",
            value="Please use `/character` to register your character before starting.\n\nThis helps the AI DM personalize the adventure for your specific character!",
            inline=False
        )
        
        embed.add_field(
            name="📝 Required Information",
            value="**Basic:** Name, Race, Class, Level\n**Optional:** Background, Stats, Equipment, Spells, Affiliations, Personality",
            inline=False
        )
        
        embed.add_field(
            name="🆕 New Episode System",
            value="**Recommended:** Use `/start_episode` instead for full episode management with recaps and progression tracking!",
            inline=False
        )
        
        embed.set_footer(text="Use /help for more detailed instructions!")
        await interaction.response.send_message(embed=embed)
        return
    
    # If characters are registered, start the adventure
    campaign_context["session_started"] = True
    
    embed = discord.Embed(
        title="⚡ Storm King's Thunder - Adventure Begins!",
        description=campaign_context["current_scene"],
        color=0x1E90FF
    )
    
    embed.add_field(
        name="🏔️ The Giant Crisis",
        value="Giants raid settlements across the Sword Coast. The ancient ordning that maintained giant society has shattered, throwing giantkind into chaos. Small folk live in terror as massive beings roam the land unchecked.",
        inline=False
    )
    
    # Show detailed party composition
    party_info = []
    for user_id, character_desc in campaign_context["characters"].items():
        if user_id in campaign_context["players"]:
            player_data = campaign_context["players"][user_id]
            char_data = player_data["character_data"]
            current_player_name = player_data["player_name"]
            party_info.append(f"**{char_data['name']}** - {char_data['race']} {char_data['class']} (Level {char_data['level']}) - *{current_player_name}*")
    
    embed.add_field(
        name="🗡️ Your Heroic Party",
        value="\n".join(party_info),
        inline=False
    )
    
    embed.add_field(
        name="⚔️ Ready for Action",
        value="Use `/action <what you do>` to interact with the world. The AI DM will respond based on your character's capabilities and the unfolding story.\n\n🎤 **Voice Narration:** Join a voice channel and use `/join_voice` to have Donnie speak his responses with dramatic flair!\n\n⚡ **Streamlined Combat:** Combat triggers automatically with Continue buttons!",
        inline=False
    )
    
    if PERSISTENT_MEMORY_AVAILABLE:
        embed.add_field(
            name="🧠 Enhanced Memory",
            value="Donnie will remember your actions, NPCs you meet, and plot developments across sessions!",
            inline=False
        )
    
    if COMBAT_AVAILABLE:
        embed.add_field(
            name="⚔️ Combat System",
            value="Combat encounters will be tracked automatically with separate display messages showing initiative, HP, and positions!",
            inline=False
        )
    
    embed.add_field(
        name="🆕 Episode Management Available",
        value="Use `/start_episode` for full campaign management with episode recaps, character progression tracking, and persistent story memory!",
        inline=False
    )
    
    embed.set_footer(text="What do you do in this moment of crisis?")
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="action", description="Take an action in the Storm King's Thunder campaign")
@app_commands.describe(what_you_do="Describe what your character does or says")
async def take_action_enhanced(interaction: discord.Interaction, what_you_do: str):
    """ENHANCED action processing with combat integration"""
    user_id = str(interaction.user.id)
    player_name = interaction.user.display_name
    
    # ✅ ENHANCED: Ensure guild_id and channel_id are properly set
    guild_id_int = interaction.guild.id  # This is an int from Discord
    guild_id_str = str(guild_id_int)     # Convert to string for database operations
    channel_id = interaction.channel.id if interaction.channel else 0  # Get channel_id for combat
    
    # Update campaign context with current guild_id
    campaign_context["guild_id"] = guild_id_str
    
    print(f"🎯 ENHANCED Action: {player_name} in guild {guild_id_str}, channel {channel_id}: '{what_you_do[:50]}...'")
    
    # Quick validation
    if user_id not in campaign_context["characters"]:
        embed = discord.Embed(
            title="🎭 Character Not Registered",
            description=f"Please register your character first using `/character`!",
            color=0xFF6B6B
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    
    if not campaign_context.get("session_started", False) and not campaign_context.get("episode_active", False):
        embed = discord.Embed(
            title="⚡ Adventure Not Started",
            description="Use `/start_episode` or `/start` to begin!",
            color=0xFF6B6B
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    
    # Get character data
    char_data = campaign_context["players"][user_id]["character_data"]
    character_name = char_data["name"]
    
    # Update player name in case it changed
    campaign_context["players"][user_id]["player_name"] = player_name
    
    # Create immediate response embed
    char_title = f"{character_name} ({char_data['race']} {char_data['class']})"
    
    embed = discord.Embed(color=0x2E8B57)
    embed.add_field(
        name=f"🎭 {char_title}",
        value=what_you_do,
        inline=False
    )
    embed.add_field(
        name="🐉 Donnie the DM",
        value="*Donnie responds...*",
        inline=False
    )
    
    # Voice status - use int guild_id for voice operations
    voice_will_speak = voice_manager and voice_manager.is_voice_active(guild_id)

    if voice_will_speak:
        embed.add_field(name="🎤", value="*Donnie prepares...*", inline=False)
    
    # ✅ ENHANCED: Updated footer to show combat system status
    footer_text = f"Level {char_data['level']} • {char_data['background']}"
    if UNIFIED_RESPONSE_AVAILABLE:
        footer_text += " • 🎯 Unified Response System"
    if COMBAT_AVAILABLE:
        footer_text += " • ⚔️ Enhanced Combat"
    embed.set_footer(text=footer_text)
    
    # Send immediate response
    await interaction.response.send_message(embed=embed)
    message = await interaction.original_response()
    
    # ✅ ENHANCED: Use the new combat-integrated background processor
    asyncio.create_task(process_unified_dm_response_background_with_combat(
        user_id, what_you_do, message, character_name, char_data, player_name, 
        guild_id_int, channel_id, voice_will_speak  # Added channel_id for combat
    ))

@bot.tree.command(name="roll", description="Roll dice for your Storm King's Thunder adventure")
@app_commands.describe(dice="Dice notation like 1d20, 3d6, 2d8+3")
async def roll_dice(interaction: discord.Interaction, dice: str = "1d20"):
    """Roll dice with D&D notation"""
    try:
        # Handle simple modifier (like 1d20+5)
        modifier = 0
        if '+' in dice:
            dice_part, mod_part = dice.split('+')
            modifier = int(mod_part.strip())
            dice = dice_part.strip()
        elif '-' in dice and dice.count('-') == 1:
            dice_part, mod_part = dice.split('-')
            modifier = -int(mod_part.strip())
            dice = dice_part.strip()
        
        if 'd' in dice:
            num_dice, die_size = dice.split('d')
            num_dice = int(num_dice) if num_dice else 1
            die_size = int(die_size)
            
            if num_dice > 20 or die_size > 1000:
                await interaction.response.send_message("❌ Maximum 20 dice of size 1000!", ephemeral=True)
                return
            
            rolls = [random.randint(1, die_size) for _ in range(num_dice)]
            total = sum(rolls) + modifier
            
            # Format the result
            result_text = f"🎲 **{interaction.user.display_name}** rolled {dice}"
            if modifier != 0:
                result_text += f"{'+' if modifier > 0 else ''}{modifier}"
            
            if len(rolls) > 1:
                result_text += f"\n**Rolls:** {rolls}"
                if modifier != 0:
                    result_text += f" {'+' if modifier > 0 else ''}{modifier}"
                result_text += f" = **{total}**"
            else:
                if modifier != 0:
                    result_text += f"\n**Roll:** {rolls[0]} {'+' if modifier > 0 else ''}{modifier} = **{total}**"
                else:
                    result_text += f"\n**Result:** **{total}**"
            
            # Add context for common D&D rolls
            if dice == "1d20":
                if rolls[0] == 20:
                    result_text += " 🎯 **Natural 20!**"
                elif rolls[0] == 1:
                    result_text += " 💥 **Natural 1!**"
            
            await interaction.response.send_message(result_text)
        else:
            await interaction.response.send_message("❌ Use dice notation like: 1d20, 3d6, 2d8+3", ephemeral=True)
            
    except ValueError:
        await interaction.response.send_message("❌ Invalid dice notation! Use format like: 1d20, 3d6, 2d8+3", ephemeral=True)

@bot.tree.command(name="status", description="Show current Storm King's Thunder campaign status")
async def show_status(interaction: discord.Interaction):
    """Display campaign status"""
    embed = discord.Embed(
        title="⚡ Storm King's Thunder - Campaign Status",
        color=0x4B0082
    )
    
    embed.add_field(
        name="📍 Current Scene",
        value=campaign_context["current_scene"],
        inline=False
    )
    
    # Show characters if any are registered
    if campaign_context["characters"]:
        party_info = []
        for user_id, character_desc in campaign_context["characters"].items():
            if user_id in campaign_context["players"]:
                player_data = campaign_context["players"][user_id]
                char_data = player_data["character_data"]
                current_player_name = player_data["player_name"]
                character_name = char_data["name"]
                party_info.append(f"**{character_name}** ({current_player_name})")
        
        embed.add_field(
            name="🗡️ Party Members",
            value="\n".join(party_info),
            inline=True
        )
    else:
        embed.add_field(
            name="🗡️ Party Members",
            value="No characters registered yet",
            inline=True
        )
    
    # Episode information
    episode_status = "⏸️ Not Started"
    if campaign_context.get("episode_active", False):
        episode_status = f"📺 Episode {campaign_context.get('current_episode', 0)} Active"
    elif campaign_context.get("session_started", False):
        episode_status = "✅ Legacy Session Active"
    
    embed.add_field(
        name="🎬 Episode Status",
        value=episode_status,
        inline=True
    )
    
    embed.add_field(
        name="📜 Session Progress",
        value=f"{len(campaign_context['session_history'])} interactions",
        inline=True
    )
    
    # Combat system status
    if COMBAT_AVAILABLE:
        combat = get_combat_integration()
        if combat:
            # Check if any combat managers are active
            active_combats = sum(1 for cm in combat.combat_managers.values() if cm.is_active())
            if active_combats > 0:
                combat_status = f"⚔️ {active_combats} Active Combat(s)"
            else:
                combat_status = "⚔️ No Active Combat"
        else:
            combat_status = "⚔️ Combat System Ready"
    else:
        combat_status = "⚔️ Combat System Disabled"
    
    embed.add_field(
        name="⚔️ Combat Status",
        value=combat_status,
        inline=True
    )
    
    # Memory status
    memory_status = "🧠 Enhanced Memory: " + ("✅ Active" if PERSISTENT_MEMORY_AVAILABLE else "❌ Disabled")
    embed.add_field(
        name="🧠 Memory System",
        value=memory_status,
        inline=True
    )
    
    # Combat system status
    combat_system_status = "⚔️ Combat System: " + ("✅ Active" if COMBAT_AVAILABLE else "❌ Disabled")
    embed.add_field(
        name="⚔️ Combat System",
        value=combat_system_status,
        inline=True
    )
    
    # Voice status
    guild_id = interaction.guild.id
    if guild_id in voice_clients and voice_clients[guild_id].is_connected():
        if tts_enabled.get(guild_id, False):
            speed = voice_speed.get(guild_id, 1.25)
            queue_size = len(voice_queue.get(guild_id, []))
            if queue_size > 0:
                voice_status = f"🎤 Connected ({speed}x speed, {queue_size} queued)"
            else:
                voice_status = f"🎤 Connected ({speed}x speed)"
        else:
            voice_status = "🔇 Muted"
    else:
        voice_status = "🔇 Not Connected"
    
    embed.add_field(
        name="🎭 Donnie's Voice",
        value=voice_status,
        inline=True
    )
    
    embed.add_field(
        name="🏔️ Giant Threat Level",
        value="🔴 **CRITICAL** - Multiple giant types terrorizing the Sword Coast",
        inline=False
    )
    
    if not campaign_context["characters"]:
        embed.add_field(
            name="⚠️ Next Step",
            value="Use `/character` to register your character, then `/start_episode` to begin with full episode management and enhanced combat!",
            inline=False
        )
    elif not campaign_context.get("session_started", False) and not campaign_context.get("episode_active", False):
        embed.add_field(
            name="⚠️ Next Step", 
            value="Use `/start_episode` for full episode management or `/start` for simple session with enhanced combat!",
            inline=False
        )
    
    await interaction.response.send_message(embed=embed)

# ====== COMBAT COMMANDS ======

@bot.tree.command(name="initiative", description="Add your initiative roll to combat")
@app_commands.describe(roll="Your initiative roll (d20 + modifier)")
async def add_initiative(interaction: discord.Interaction, roll: int):
    """FIXED: Add player initiative to combat with comprehensive error handling"""
    try:
        if not COMBAT_AVAILABLE:
            await interaction.response.send_message("❌ Combat system not available!", ephemeral=True)
            return
        
        user_id = str(interaction.user.id)
        
        # Check if character is registered
        if user_id not in campaign_context["characters"]:
            embed = discord.Embed(
                title="❌ Character Required",
                description="Register your character first with `/character`!",
                color=0xFF6B6B
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        # Validate initiative roll
        if not isinstance(roll, int) or roll < 1 or roll > 50:
            embed = discord.Embed(
                title="❌ Invalid Initiative",
                description="Initiative must be a number between 1 and 50!",
                color=0xFF6B6B
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        # Get combat integration
        combat = get_combat_integration()
        if not combat:
            await interaction.response.send_message("❌ Combat system not initialized!", ephemeral=True)
            return
        
        # Get character info
        char_data = campaign_context["players"][user_id]["character_data"]
        char_name = char_data["name"]
        player_name = campaign_context["players"][user_id]["player_name"]
        
        # Add to combat
        success = combat.add_player_to_combat(interaction.channel.id, user_id, roll)
        
        if success:
            # Create success embed
            embed = discord.Embed(
                title="🎲 Initiative Added!",
                description=f"**{char_name}** joins combat with initiative **{roll}**",
                color=0x32CD32
            )
            
            embed.add_field(
                name="⚔️ Character Info",
                value=f"**Player:** {player_name}\n**Class:** {char_data['race']} {char_data['class']} (Level {char_data['level']})",
                inline=True
            )
            
            # Get combat status for display
            combat_manager = combat.get_combat_manager(interaction.channel.id)
            if combat_manager:
                status = combat_manager.get_combat_status()
                
                embed.add_field(
                    name="🎯 Combat Status",
                    value=f"**Phase:** {status.get('phase', 'Unknown')}\n**Combatants:** {status.get('combatants_count', 0)}",
                    inline=True
                )
                
                # Show initiative order if combat is active
                if combat_manager.is_active() and combat_manager.initiative_order:
                    order_text = []
                    for i, combatant_id in enumerate(combat_manager.initiative_order[:5]):  # Show top 5
                        combatant = combat_manager.combatants.get(combatant_id)
                        if combatant:
                            indicator = "👑" if i == 0 else f"{i+1}."
                            order_text.append(f"{indicator} {combatant.name} ({combatant.initiative})")
                    
                    if order_text:
                        embed.add_field(
                            name="🏆 Initiative Order",
                            value="\n".join(order_text),
                            inline=False
                        )
                        
                        if combat_manager.round_number > 0:
                            current = combat_manager.get_current_combatant()
                            if current:
                                embed.add_field(
                                    name="⏰ Current Turn",
                                    value=f"Round {combat_manager.round_number}: **{current.name}**",
                                    inline=True
                                )
                
                # Auto-start message
                if combat_manager.phase.value == "active":
                    embed.add_field(
                        name="🚀 Combat Active!",
                        value="Combat has started! Use `/action` to describe what you do on your turn.",
                        inline=False
                    )
            
            embed.set_footer(text="Use /combat_status to check combat state • /action to take actions")
            
            await interaction.response.send_message(embed=embed)
            
            # Voice announcement if enabled
            guild_id = interaction.guild.id
            voice_will_speak = voice_manager and voice_manager.is_voice_active(guild_id)
            
            if voice_will_speak:
                announcement = f"{char_name} enters combat with initiative {roll}!"
                if voice_manager:
                    await voice_manager.speak_text(guild_id, tts_text, character_name)
        
        else:
            # Error adding to combat
            embed = discord.Embed(
                title="❌ Failed to Join Combat",
                description="Could not add character to combat. Check console for details.",
                color=0xFF6B6B
            )
            embed.add_field(
                name="🔧 Troubleshooting",
                value="• Make sure combat system is properly initialized\n• Check that your character is registered\n• Try `/combat_status` to see current state",
                inline=False
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
    except Exception as e:
        print(f"❌ Critical error in add_initiative: {e}")
        import traceback
        traceback.print_exc()
        
        try:
            embed = discord.Embed(
                title="❌ Initiative Command Failed",
                description=f"An unexpected error occurred: {str(e)}",
                color=0xFF6B6B
            )
            if not interaction.response.is_done():
                await interaction.response.send_message(embed=embed, ephemeral=True)
            else:
                await interaction.followup.send(embed=embed, ephemeral=True)
        except:
            pass  # Fail silently if we can't even send error message

@bot.tree.command(name="start_combat", description="Manually start combat (Admin only)")
@app_commands.describe(
    enemy_name="Name of enemy to add (optional)",
    enemy_initiative="Enemy's initiative roll (optional)",
    enemy_hp="Enemy's HP (optional)"
)
async def start_combat_command(interaction: discord.Interaction, 
                              enemy_name: Optional[str] = None,
                              enemy_initiative: Optional[int] = None,
                              enemy_hp: Optional[int] = None):
    """FIXED: Manual combat start with optional enemy"""
    try:
        if not is_admin(interaction):
            await interaction.response.send_message("❌ Admin only!", ephemeral=True)
            return
        
        if not COMBAT_AVAILABLE:
            await interaction.response.send_message("❌ Combat system not available!", ephemeral=True)
            return
        
        combat = get_combat_integration()
        if not combat:
            await interaction.response.send_message("❌ Combat system not initialized!", ephemeral=True)
            return
        
        # Get combat manager
        combat_manager = combat.get_combat_manager(interaction.channel.id)
        
        # Add enemy if specified
        if enemy_name and enemy_initiative is not None:
            success = combat_manager.add_enemy_manually(enemy_name, enemy_initiative, enemy_hp)
            if not success:
                await interaction.response.send_message(f"❌ Failed to add enemy: {enemy_name}", ephemeral=True)
                return
        
        # Try to start combat
        success = combat_manager.start_combat()
        
        if success:
            embed = discord.Embed(
                title="⚔️ Combat Started!",
                description="Combat has been manually initiated by the DM.",
                color=0xFF4500
            )
            
            if enemy_name:
                embed.add_field(
                    name="👹 Enemy Added",
                    value=f"**{enemy_name}** (Initiative: {enemy_initiative}, HP: {enemy_hp or 'Unknown'})",
                    inline=False
                )
            
            # Show current status
            status = combat_manager.get_combat_status()
            embed.add_field(
                name="🎯 Combat Info",
                value=f"**Round:** {status.get('round_number', 1)}\n**Combatants:** {status.get('combatants_count', 0)}",
                inline=True
            )
            
            embed.add_field(
                name="📋 Next Steps",
                value="Players should use `/initiative <roll>` to join combat!",
                inline=False
            )
            
            await interaction.response.send_message(embed=embed)
            
        else:
            embed = discord.Embed(
                title="❌ Cannot Start Combat",
                description="Combat could not be started. Check that there are combatants with initiative.",
                color=0xFF6B6B
            )
            
            status = combat_manager.get_combat_status()
            embed.add_field(
                name="🔍 Current State",
                value=f"**Phase:** {status.get('phase', 'Unknown')}\n**Combatants:** {status.get('combatants_count', 0)}",
                inline=False
            )
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
    except Exception as e:
        print(f"❌ Error in start_combat_command: {e}")
        await interaction.response.send_message(f"❌ Error starting combat: {e}", ephemeral=True)

@bot.tree.command(name="add_enemy", description="Add enemy to combat (Admin only)")
@app_commands.describe(
    name="Enemy name",
    initiative="Enemy initiative roll",
    hp="Enemy hit points (optional)"
)
async def add_enemy_command(interaction: discord.Interaction, name: str, initiative: int, hp: Optional[int] = None):
    """Add enemy to combat"""
    try:
        if not is_admin(interaction):
            await interaction.response.send_message("❌ Admin only!", ephemeral=True)
            return
        
        if not COMBAT_AVAILABLE:
            await interaction.response.send_message("❌ Combat system not available!", ephemeral=True)
            return
        
        combat = get_combat_integration()
        if not combat:
            await interaction.response.send_message("❌ Combat system not initialized!", ephemeral=True)
            return
        
        # Add enemy to combat
        success = await combat.add_enemy_to_combat(interaction.channel.id, name, initiative, hp)
        
        if success:
            embed = discord.Embed(
                title="👹 Enemy Added!",
                description=f"**{name}** has been added to combat.",
                color=0xFF4500
            )
            
            embed.add_field(
                name="⚔️ Enemy Stats",
                value=f"**Initiative:** {initiative}\n**HP:** {hp or 'Unknown'}",
                inline=True
            )
            
            await interaction.response.send_message(embed=embed)
        else:
            await interaction.response.send_message(f"❌ Failed to add enemy: {name}", ephemeral=True)
            
    except Exception as e:
        print(f"❌ Error in add_enemy_command: {e}")
        await interaction.response.send_message(f"❌ Error adding enemy: {e}", ephemeral=True)

@bot.tree.command(name="next_turn", description="Advance to next turn (Admin only)")
async def next_turn_command(interaction: discord.Interaction):
    """Advance to next turn"""
    try:
        if not is_admin(interaction):
            await interaction.response.send_message("❌ Admin only!", ephemeral=True)
            return
        
        if not COMBAT_AVAILABLE:
            await interaction.response.send_message("❌ Combat system not available!", ephemeral=True)
            return
        
        combat = get_combat_integration()
        if not combat:
            await interaction.response.send_message("❌ Combat system not initialized!", ephemeral=True)
            return
        
        success = await combat.advance_turn(interaction.channel.id)
        
        if success:
            combat_manager = combat.get_combat_manager(interaction.channel.id)
            current = combat_manager.get_current_combatant()
            
            embed = discord.Embed(
                title="⏭️ Turn Advanced",
                description=f"Round {combat_manager.round_number}",
                color=0x4169E1
            )
            
            if current:
                embed.add_field(
                    name="👤 Current Turn",
                    value=f"**{current.name}** ({'Player' if current.is_player else 'NPC'})",
                    inline=False
                )
            
            await interaction.response.send_message(embed=embed)
        else:
            await interaction.response.send_message("❌ No active combat to advance!", ephemeral=True)
            
    except Exception as e:
        print(f"❌ Error in next_turn_command: {e}")
        await interaction.response.send_message(f"❌ Error advancing turn: {e}", ephemeral=True)

@bot.tree.command(name="end_combat", description="End current combat (Admin only)")
async def end_combat_command(interaction: discord.Interaction):
    """FIXED: End combat with proper cleanup"""
    try:
        if not is_admin(interaction):
            await interaction.response.send_message("❌ Admin only!", ephemeral=True)
            return
        
        if not COMBAT_AVAILABLE:
            await interaction.response.send_message("❌ Combat system not available!", ephemeral=True)
            return
        
        combat = get_combat_integration()
        if not combat:
            await interaction.response.send_message("❌ Combat system not initialized!", ephemeral=True)
            return
        
        result = await combat.end_combat(interaction.channel.id)
        
        if result:
            embed = discord.Embed(
                title="✅ Combat Ended",
                description="The battle has concluded!",
                color=0x32CD32
            )
            
            embed.add_field(
                name="📊 Combat Summary",
                value=f"**Duration:** {result['rounds']} rounds\n**Participants:** {result['combatants']} combatants",
                inline=False
            )
            
            await interaction.response.send_message(embed=embed)
        else:
            await interaction.response.send_message("❌ No active combat found!", ephemeral=True)
            
    except Exception as e:
        print(f"❌ Error in end_combat_command: {e}")
        await interaction.response.send_message(f"❌ Error ending combat: {e}", ephemeral=True)

@bot.tree.command(name="combat_status", description="View detailed combat status")
async def view_combat_status(interaction: discord.Interaction):
    """FIXED: View combat status with comprehensive debugging info"""
    try:
        if not COMBAT_AVAILABLE:
            embed = discord.Embed(
                title="❌ Combat System Unavailable",
                description="The combat system is not currently loaded.",
                color=0xFF6B6B
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        combat = get_combat_integration()
        if not combat:
            embed = discord.Embed(
                title="❌ Combat Not Initialized",
                description="Combat system is loaded but not initialized.",
                color=0xFF6B6B
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        combat_manager = combat.get_combat_manager(interaction.channel.id)
        status = combat_manager.get_combat_status()
        
        # Create status embed
        embed = discord.Embed(
            title="⚔️ Combat Status",
            description=f"Channel: {interaction.channel.name}",
            color=0x4169E1 if status.get('phase') == 'active' else 0x808080
        )
        
        # Basic info
        embed.add_field(
            name="🎯 Combat State",
            value=f"**Phase:** {status.get('phase', 'Unknown').title()}\n**Round:** {status.get('round_number', 0)}\n**Turn Index:** {status.get('turn_index', 0)}",
            inline=True
        )
        
        embed.add_field(
            name="👥 Participants",
            value=f"**Total:** {status.get('combatants_count', 0)}\n**In Order:** {status.get('initiative_order_count', 0)}",
            inline=True
        )
        
        # Current turn
        current_name = status.get('current_combatant')
        if current_name:
            embed.add_field(
                name="👤 Current Turn",
                value=f"**{current_name}**",
                inline=True
            )
        
        # Show combatants
        combatants_info = status.get('combatants', {})
        if combatants_info:
            combatant_lines = []
            for cid, info in list(combatants_info.items())[:8]:  # Show max 8
                player_indicator = "🎭" if info.get('is_player') else "👹"
                init_text = f"Init: {info.get('initiative', '?')}"
                hp_text = f"HP: {info.get('hp', '?')}"
                combatant_lines.append(f"{player_indicator} **{info.get('name', 'Unknown')}** ({init_text}, {hp_text})")
            
            embed.add_field(
                name="🏆 All Combatants",
                value="\n".join(combatant_lines) if combatant_lines else "None",
                inline=False
            )
            
            if len(combatants_info) > 8:
                embed.add_field(
                    name="ℹ️ Note",
                    value=f"Showing 8 of {len(combatants_info)} combatants",
                    inline=False
                )
        
        # Instructions based on state
        if status.get('phase') == 'setup':
            embed.add_field(
                name="📋 Next Steps",
                value="• Players use `/initiative <roll>` to join\n• Admins can use `/add_enemy` to add opponents\n• Combat starts automatically when ready",
                inline=False
            )
        elif status.get('phase') == 'active':
            embed.add_field(
                name="📋 Combat Commands",
                value="• `/action <what you do>` - Take actions\n• `/next_turn` - Advance turn (Admin)\n• `/end_combat` - End combat (Admin)",
                inline=False
            )
        else:
            embed.add_field(
                name="📋 Start Combat",
                value="Use `/start_combat` (Admin) or have players roll initiative!",
                inline=False
            )
        
        # Debug info for admins
        if is_admin(interaction):
            embed.add_field(
                name="🔧 Debug Info (Admin Only)",
                value=f"Manager ID: {id(combat_manager)}\nIntegration ID: {id(combat)}\nError: {status.get('error', 'None')}",
                inline=False
            )
        
        embed.set_footer(text="Enhanced Combat System • Auto-updating displays")
        
        await interaction.response.send_message(embed=embed)
        
    except Exception as e:
        print(f"❌ Critical error in view_combat_status: {e}")
        import traceback
        traceback.print_exc()
        
        try:
            embed = discord.Embed(
                title="❌ Status Command Failed",
                description=f"Error getting combat status: {str(e)}",
                color=0xFF6B6B
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
        except:
            pass

@bot.tree.command(name="debug_combat", description="Debug combat system (Admin only)")
async def debug_combat_system(interaction: discord.Interaction):
    """Debug combat system"""
    try:
        if not is_admin(interaction):
            await interaction.response.send_message("❌ Admin only!", ephemeral=True)
            return
        
        embed = discord.Embed(
            title="🔧 Combat System Debug",
            description="Diagnostic information for the combat system",
            color=0x4169E1
        )
        
        # System availability
        embed.add_field(
            name="🎯 System Status",
            value=f"Combat Available: {'✅' if COMBAT_AVAILABLE else '❌'}\nIntegration: {'✅' if get_combat_integration() else '❌'}",
            inline=True
        )
        
        # Integration details
        if COMBAT_AVAILABLE:
            combat = get_combat_integration()
            if combat:
                embed.add_field(
                    name="🔗 Integration Info",
                    value=f"Active Managers: {len(combat.combat_managers)}\nDisplay Manager: {'✅' if combat.display_manager else '❌'}",
                    inline=True
                )
                
                # Current channel
                channel_id = interaction.channel.id
                if channel_id in combat.combat_managers:
                    combat_manager = combat.combat_managers[channel_id]
                    status = combat_manager.get_combat_status()
                    
                    embed.add_field(
                        name="📍 This Channel",
                        value=f"Phase: {status.get('phase', 'Unknown')}\nCombatants: {status.get('combatants_count', 0)}\nRound: {status.get('round_number', 0)}",
                        inline=True
                    )
                else:
                    embed.add_field(
                        name="📍 This Channel",
                        value="No combat manager found",
                        inline=True
                    )
            else:
                embed.add_field(
                    name="❌ Integration Error",
                    value="Combat integration failed to initialize",
                    inline=False
                )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
        
    except Exception as e:
        await interaction.response.send_message(f"❌ Debug error: {e}", ephemeral=True)

# ====== WORLD INFORMATION COMMANDS ======

@bot.tree.command(name="scene", description="View the current scene in detail")
async def view_scene(interaction: discord.Interaction):
    """Show detailed current scene"""
    embed = discord.Embed(
        title="📍 Current Scene",
        description=campaign_context["current_scene"],
        color=0x8FBC8F
    )
    
    embed.add_field(
        name="🗺️ Location Context",
        value="You are in the Sword Coast region, where the giant crisis has created chaos and fear among the small folk.",
        inline=False
    )
    
    embed.set_footer(text="Use /action to interact with your surroundings")
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="locations", description="Learn about key Sword Coast locations")
async def show_locations(interaction: discord.Interaction):
    """Show key Sword Coast locations"""
    embed = discord.Embed(
        title="🗺️ Key Locations - The Sword Coast",
        description="Important places in your Storm King's Thunder adventure",
        color=0x228B22
    )
    
    embed.add_field(
        name="🏰 Nightstone",
        value="Small village recently attacked by cloud giants and abandoned",
        inline=False
    )
    
    embed.add_field(
        name="🏰 Waterdeep",
        value="The City of Splendors, major hub of trade and politics",
        inline=False
    )
    
    embed.add_field(
        name="🏰 Neverwinter",
        value="Rebuilt city, seat of Lord Neverember's power",
        inline=False
    )
    
    embed.add_field(
        name="🏰 Triboar",
        value="Important crossroads town and target of giant raids",
        inline=False
    )
    
    embed.add_field(
        name="🏰 Bryn Shander",
        value="Largest settlement in Ten-Towns, threatened by frost giants",
        inline=False
    )
    
    embed.add_field(
        name="🏰 Ironslag",
        value="Fire giant stronghold where Duke Zalto forges weapons",
        inline=False
    )
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="campaign", description="Show comprehensive Storm King's Thunder campaign information")
async def show_campaign_info(interaction: discord.Interaction):
    """Show Storm King's Thunder campaign information"""
    embed = discord.Embed(
        title="⚡ Storm King's Thunder - Campaign Information",
        description="The giant crisis threatening the Sword Coast",
        color=0x191970
    )
    
    embed.add_field(
        name="📖 Campaign Setting",
        value=campaign_context["setting"][:800] + ("..." if len(campaign_context["setting"]) > 800 else ""),
        inline=False
    )
    
    embed.add_field(
        name="⚡ Current Crisis",
        value="Giants roam the land in unprecedented numbers. The ordning has collapsed. Heroes are needed to restore order and protect the innocent.",
        inline=False
    )
    
    embed.add_field(
        name="🎯 Key NPCs",
        value="**Zephyros** - Ancient cloud giant wizard\n**Harshnag** - Frost giant ally\n**Princess Serissa** - Storm giant princess\n**Duke Zalto** - Fire giant weaponsmith",
        inline=False
    )
    
    embed.set_footer(text="Use /locations for more detailed location information")
    await interaction.response.send_message(embed=embed)

# ====== ADMIN COMMANDS ======

@bot.tree.command(name="set_scene", description="Update the current scene (Admin only)")
@app_commands.describe(scene_description="The new scene description")
async def set_scene(interaction: discord.Interaction, scene_description: str):
    """Update current scene (Admin only)"""
    if not is_admin(interaction):
        await interaction.response.send_message("❌ Only server administrators can update scenes!", ephemeral=True)
        return
        
    campaign_context["current_scene"] = scene_description
    
    # Also update in database if available
    if DATABASE_AVAILABLE and interaction.guild:
        try:
            guild_id = str(interaction.guild.id)
            GuildOperations.update_guild_settings(
                guild_id,
                current_scene=scene_description
            )
            print(f"✅ Scene updated in database for guild {guild_id}")
        except Exception as e:
            print(f"⚠️ Failed to update scene in database: {e}")
    
    embed = discord.Embed(
        title="🏛️ Scene Updated",
        description=scene_description,
        color=0x4169E1
    )
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="get_last_scene", description="Retrieve scene from last episode (Admin only)")
async def get_last_scene(interaction: discord.Interaction):
    """Get scene from the last episode"""
    if not is_admin(interaction):
        await interaction.response.send_message("❌ Admin only!", ephemeral=True)
        return
    
    if not DATABASE_AVAILABLE:
        await interaction.response.send_message("❌ Database not available!", ephemeral=True)
        return
    
    try:
        guild_id = str(interaction.guild.id)
        
        # Get the last completed episode (check if method exists)
        if hasattr(EpisodeOperations, 'get_last_completed_episode'):
            last_episode = EpisodeOperations.get_last_completed_episode(guild_id)
        else:
            # Fallback: get episodes and find the last one manually
            print("⚠️ get_last_completed_episode method not found, using fallback")
            last_episode = None
        if last_episode and hasattr(last_episode, 'ending_scene') and last_episode.ending_scene:
            # Update current scene to last episode's ending
            campaign_context["current_scene"] = last_episode.ending_scene
            
            embed = discord.Embed(
                title="📍 Scene Retrieved from Last Episode",
                description=last_episode.ending_scene,
                color=0x32CD32
            )
            embed.add_field(
                name="Source",
                value=f"Episode {last_episode.episode_number}: {last_episode.name}",
                inline=False
            )
        else:
            embed = discord.Embed(
                title="⚠️ No Previous Scene Found",
                description="No completed episodes with ending scenes found. Using default scene.",
                color=0xFFD700
            )
        
        await interaction.response.send_message(embed=embed)
        
    except Exception as e:
        await interaction.response.send_message(f"❌ Error retrieving last scene: {e}", ephemeral=True)

@bot.tree.command(name="clear_test_data", description="Clear all episodes and memories for testing (Admin only)")
@app_commands.describe(confirm="Type 'DELETE ALL DATA' to confirm deletion")
async def clear_test_data(interaction: discord.Interaction, confirm: str):
    """Clear all test data (Admin only) - Fixed for foreign keys and column names"""
    if not is_admin(interaction):
        await interaction.response.send_message("❌ Admin only!", ephemeral=True)
        return
    
    if confirm != "DELETE ALL DATA":
        embed = discord.Embed(
            title="⚠️ Confirmation Required",
            description="To delete all episodes and memories, use:\n`/clear_test_data confirm:DELETE ALL DATA`",
            color=0xFF4500
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    
    if not DATABASE_AVAILABLE:
        await interaction.response.send_message("❌ Database not available!", ephemeral=True)
        return
    
    try:
        guild_id = str(interaction.guild.id)
        
        # Clear campaign context
        campaign_context["session_history"] = []
        campaign_context["current_episode"] = 0
        campaign_context["episode_active"] = False
        campaign_context["episode_start_time"] = None
        
        from database.database import get_db_connection
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # DISABLE foreign key checks temporarily
        cursor.execute("PRAGMA foreign_keys = OFF")
        
        deleted_counts = {}
        
        # Function to inspect actual column names
        def get_table_columns(table_name):
            try:
                cursor.execute(f"PRAGMA table_info({table_name})")
                columns = [row[1] for row in cursor.fetchall()]
                return columns
            except:
                return []
        
        # Clear tables in order (episodes last due to foreign keys)
        tables_to_clear = [
            "conversation_memories", 
            "npc_memories",
            "memory_consolidation", 
            "world_state",
            "character_progression",
            "character_snapshots",
            "story_notes",
            "episodes"  # LAST due to foreign keys
        ]
        
        for table in tables_to_clear:
            try:
                # Check if table exists
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,))
                if not cursor.fetchone():
                    deleted_counts[table] = "Table not found"
                    continue
                
                # Get actual column names
                columns = get_table_columns(table)
                print(f"🔍 Table {table} columns: {columns}")
                
                # Find the right column to use
                guild_column = None
                if "guild_id" in columns:
                    guild_column = "guild_id"
                elif "campaign_id" in columns:
                    guild_column = "campaign_id"
                
                if guild_column:
                    # Count and delete
                    cursor.execute(f"SELECT COUNT(*) FROM {table} WHERE {guild_column} = ?", (guild_id,))
                    count = cursor.fetchone()[0]
                    cursor.execute(f"DELETE FROM {table} WHERE {guild_column} = ?", (guild_id,))
                    deleted_counts[table] = f"{count} (using {guild_column})"
                    print(f"✅ Cleared {count} records from {table}")
                else:
                    deleted_counts[table] = f"No guild/campaign column found"
                    print(f"⚠️ No suitable column found for {table}")
                
            except Exception as e:
                deleted_counts[table] = f"Error: {str(e)}"
                print(f"❌ Error clearing {table}: {e}")
        
        # Re-enable foreign key checks
        cursor.execute("PRAGMA foreign_keys = ON")
        conn.commit()
        
        # Reset scene to default
        campaign_context["current_scene"] = "The village of Nightstone sits eerily quiet. Giant-sized boulders litter the village square, and not a soul can be seen moving in the streets. The party approaches the mysteriously open gates..."
        
        embed = discord.Embed(
            title="🗑️ Test Data Cleared Successfully",
            description="Foreign key constraints handled, scene reset to Nightstone.",
            color=0x32CD32
        )
        
        for table, result in deleted_counts.items():
            embed.add_field(name=f"📊 {table}", value=f"{result}", inline=True)
        
        await interaction.response.send_message(embed=embed)
        
    except Exception as e:
        # Always re-enable foreign keys
        try:
            cursor.execute("PRAGMA foreign_keys = ON")
            conn.commit()
        except:
            pass
        await interaction.response.send_message(f"❌ Error: {e}", ephemeral=True)

@bot.tree.command(name="update_scene_from_response", description="Update scene based on last DM response (Admin only)")
@app_commands.describe(new_scene="Description of where the party is now")
async def update_scene_from_response(interaction: discord.Interaction, new_scene: str):
    """Update the current scene based on recent events"""
    if not is_admin(interaction):
        await interaction.response.send_message("❌ Admin only!", ephemeral=True)
        return
    
    # Update scene
    campaign_context["current_scene"] = new_scene
    
    # Update in database if available
    if DATABASE_AVAILABLE and interaction.guild:
        try:
            guild_id = str(interaction.guild.id)
            
            # Update current episode with new scene
            current_episode = EpisodeOperations.get_current_episode(guild_id)
            if current_episode:
                # This would need a method to update episode scene - might need to add this
                pass
                
        except Exception as e:
            print(f"⚠️ Failed to update scene in episode: {e}")
    
    embed = discord.Embed(
        title="📍 Scene Updated",
        description=new_scene,
        color=0x4169E1
    )
    embed.add_field(
        name="💡 Tip",
        value="This scene will be used as the starting point for future episodes.",
        inline=False
    )
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="cleanup_confirmations", description="Clean up expired character sheet confirmations (Admin only)")
async def cleanup_confirmations(interaction: discord.Interaction):
    """Clean up expired confirmations (Admin only)"""
    if not is_admin(interaction):
        await interaction.response.send_message("❌ Only server administrators can use this command!", ephemeral=True)
        return
    
    try:
        # Import the PDF character parser
        from pdf_character_parser import PDFCharacterCommands
        
        if hasattr(bot, 'pdf_character_commands') and bot.pdf_character_commands:
            expired_count = bot.pdf_character_commands.cleanup_expired_confirmations()
            embed = discord.Embed(
                title="🧹 Cleanup Complete",
                description=f"Removed {expired_count} expired character sheet confirmations",
                color=0x32CD32
            )
        else:
            embed = discord.Embed(
                title="⚠️ PDF System Not Available",
                description="The PDF character system is not currently loaded",
                color=0xFFD700
            )
        
        await interaction.response.send_message(embed=embed)
        
    except Exception as e:
        await interaction.response.send_message(f"❌ Error during cleanup: {str(e)}", ephemeral=True)

# ====== MEMORY DEBUG COMMAND ======

@bot.tree.command(name="debug_memory", description="Check memory system status (Admin only)")
async def debug_memory(interaction: discord.Interaction):
    """Debug command to verify memory system functionality"""
    
    if not is_admin(interaction):
        await interaction.response.send_message("❌ Admin only!", ephemeral=True)
        return
    
    guild_id = str(interaction.guild.id)
    
    try:
        embed = discord.Embed(
            title="🧠 Enhanced Memory System Status",
            description="Current memory system statistics and recent important events",
            color=0x4169E1
        )
        
        if not PERSISTENT_MEMORY_AVAILABLE:
            embed.add_field(
                name="❌ Memory System Status",
                value="Persistent memory system is not available. Install enhanced_dm_system.py to enable.",
                inline=False
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        if not DATABASE_AVAILABLE:
            embed.add_field(
                name="⚠️ Database Status",
                value="Database system is not available. Memory system requires database support.",
                inline=False
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        # Get database connection and check memory tables
        from database.database import get_db_connection
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Memory statistics
        try:
            cursor.execute("SELECT COUNT(*) FROM conversation_memories WHERE campaign_id = ?", (guild_id,))
            conv_count = cursor.fetchone()[0]
        except:
            conv_count = 0
        
        try:
            cursor.execute("SELECT COUNT(*) FROM npc_memories WHERE campaign_id = ?", (guild_id,))
            npc_count = cursor.fetchone()[0]
        except:
            npc_count = 0
        
        try:
            cursor.execute("SELECT COUNT(*) FROM memory_consolidation WHERE campaign_id = ?", (guild_id,))
            consolidation_count = cursor.fetchone()[0]
        except:
            consolidation_count = 0
        
        try:
            cursor.execute("SELECT COUNT(*) FROM world_state WHERE campaign_id = ?", (guild_id,))
            world_state_count = cursor.fetchone()[0]
        except:
            world_state_count = 0
        
        embed.add_field(
            name="📊 Memory Statistics",
            value=f"**Conversations:** {conv_count}\n**NPCs Tracked:** {npc_count}\n**Episodes Consolidated:** {consolidation_count}\n**World States:** {world_state_count}",
            inline=True
        )
        
        # Recent important memories
        try:
            cursor.execute('''
                SELECT character_name, summary, importance_score, timestamp 
                FROM conversation_memories 
                WHERE campaign_id = ? AND importance_score >= 0.6
                ORDER BY timestamp DESC LIMIT 5
            ''', (guild_id,))
            important_memories = cursor.fetchall()
        except:
            important_memories = []
        
        if important_memories:
            memory_text = []
            for mem in important_memories:
                timestamp = mem[3][:10] if mem[3] else "Unknown"
                memory_text.append(f"**{mem[0]}** ({timestamp}): {mem[1][:60]}... (Score: {mem[2]:.1f})")
            
            embed.add_field(
                name="⭐ Recent Important Events",
                value="\n".join(memory_text[:3]),  # Show top 3
                inline=False
            )
        else:
            embed.add_field(
                name="⭐ Recent Important Events", 
                value="No high-importance events recorded yet",
                inline=False
            )
        
        # System status
        status_indicators = []
        status_indicators.append("✅ Database Connected" if DATABASE_AVAILABLE else "❌ Database Unavailable")
        status_indicators.append("✅ Memory Operations Active" if conv_count > 0 else "⚠️ No Memories Stored")
        status_indicators.append("✅ Episode Active" if campaign_context.get("episode_active") else "⚠️ No Active Episode")
        status_indicators.append("✅ Persistent Memory Available" if PERSISTENT_MEMORY_AVAILABLE else "❌ Memory System Disabled")
        status_indicators.append("✅ Combat System Available" if COMBAT_AVAILABLE else "❌ Combat System Disabled")
        
        embed.add_field(
            name="🔍 System Status",
            value="\n".join(status_indicators),
            inline=False
        )
        
        embed.set_footer(text="Enhanced Memory & Combat System | Storm King's Thunder")
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
        
    except Exception as e:
        await interaction.response.send_message(f"❌ Memory debug failed: {e}", ephemeral=True)
        print(f"Memory debug error: {e}")

# ====== HELP COMMAND ======

@bot.tree.command(name="help", description="Show comprehensive guide for the Storm King's Thunder TTS bot")
async def show_help(interaction: discord.Interaction):
    """Show comprehensive bot guide including TTS features, episode management, streamlined combat, and PDF uploads"""
    embed = discord.Embed(
        title="⚡ Storm King's Thunder TTS Bot - ENHANCED MEMORY & COMBAT EDITION",
        description="Your AI-powered D&D 5e adventure with Donnie the DM's optimized voice, persistent memory, episode management, and enhanced combat tracking!",
        color=0x4169E1
    )
    
    embed.add_field(
        name="🧠 Enhanced Memory System",
        value=f"{'✅ **ACTIVE** - Donnie remembers conversations, NPCs, and plot threads across episodes!' if PERSISTENT_MEMORY_AVAILABLE else '❌ **DISABLED** - Install enhanced_dm_system.py to enable persistent memory'}\n`/debug_memory` - Check memory system status (Admin)",
        inline=False
    )
    
    embed.add_field(
        name="⚔️ Enhanced Combat System (NEW!)",
        value=f"{'✅ **ACTIVE** - Auto-updating combat displays with initiative, HP, and position tracking!' if COMBAT_AVAILABLE else '❌ **DISABLED** - Combat files not found'}\n`/combat_status` - View current combat\n`/initiative <roll>` - Add to combat\n`/end_combat` - End combat (Admin)",
        inline=False
    )
    
    embed.add_field(
        name="🎤 Voice Features (OPTIMIZED!)",
        value="`/join_voice` - Donnie joins voice with fast, optimized narration\n`/leave_voice` - Donnie leaves voice channel\n`/mute_donnie` - Disable TTS narration\n`/unmute_donnie` - Enable TTS narration\n`/donnie_speed <1.0-2.0>` - Adjust speaking speed",
        inline=False
    )
    
    embed.add_field(
        name="📄 Character Upload",
        value="`/upload_character_sheet` - Upload PDF character sheet for auto-parsing\n`/character_sheet_help` - Get help with character sheet uploads\n`/character` - Manual character registration (alternative)",
        inline=False
    )
    
    embed.add_field(
        name="📺 Episode Management",
        value="`/start_episode [name]` - Begin new episode with recap\n`/end_episode [summary]` - End current episode\n`/episode_recap [#] [style]` - Get AI dramatic recaps\n`/episode_history` - View past episodes\n`/add_story_note` - Add player notes (non-canonical)",
        inline=False
    )
    
    embed.add_field(
        name="📈 Character Progression",
        value="`/level_up <level> [reason]` - Level up with tracking\n`/character_progression [player]` - View progression history\n`/character_snapshot [notes]` - Manual character snapshot\n`/party_progression` - View entire party progression",
        inline=False
    )
    
    embed.add_field(
        name="🎭 Character Management",
        value="`/character` - Register detailed character\n`/party` - View all party members\n`/character_sheet` - View character details\n`/update_character` - Modify character aspects",
        inline=False
    )
    
    embed.add_field(
        name="🎮 Core Gameplay",
        value="`/start_episode` - Begin with episode management (recommended)\n`/start` - Begin simple session (legacy)\n`/action <what_you_do>` - Take actions (AI DM responds + speaks quickly with Continue buttons!)\n`/roll <dice>` - Roll dice (1d20+3, 3d6, etc.)\n`/status` - Show campaign status",
        inline=False
    )
    
    embed.add_field(
        name="📚 World Information",
        value="`/scene` - View current scene\n`/locations` - Sword Coast locations\n`/campaign` - Full campaign info",
        inline=False
    )
    
    embed.add_field(
        name="⚙️ Admin Commands",
        value="`/set_scene` - Update current scene\n`/get_last_scene` - Load scene from last episode\n`/update_scene_from_response` - Update scene based on events\n`/clear_test_data` - Clear all test data (Admin only)",
        inline=False
    )
    
    await interaction.response.send_message(embed=embed)

# ====== INITIALIZATIONs SECTION ======

# ====== ENHANCED PDF CHARACTER PARSER INITIALIZATION ======
print("\n🔄 Initializing PDF Character Parser...")

# Check if we can import the module first
can_import_pdf_module = False
try:
    import pdf_character_parser
    can_import_pdf_module = True
    print("✅ pdf_character_parser module imported successfully")
    print(f"   PDF_AVAILABLE flag: {pdf_character_parser.PDF_AVAILABLE}")
    
    if hasattr(pdf_character_parser, 'IMPORT_ERRORS'):
        if pdf_character_parser.IMPORT_ERRORS:
            print(f"   Import errors detected: {pdf_character_parser.IMPORT_ERRORS}")
        else:
            print("   No import errors detected")
            
except ImportError as e:
    print(f"❌ Cannot import pdf_character_parser module: {e}")
    print("   Make sure pdf_character_parser.py is in the same directory as main.py")
except Exception as e:
    print(f"❌ Error during pdf_character_parser module import: {e}")

# Initialize PDF Character Parser with enhanced error handling
if can_import_pdf_module:
    try:
        print("🔄 Creating PDFCharacterCommands instance...")
        
        # Verify we have all required dependencies
        if not claude_client:
            raise ValueError("claude_client is not initialized")
        if not campaign_context:
            raise ValueError("campaign_context is not initialized")
        if not bot:
            raise ValueError("bot is not initialized")
            
        print("✅ All dependencies verified")
        
        # Create the PDF character commands instance
        from pdf_character_parser import PDFCharacterCommands
        bot.pdf_character_commands = PDFCharacterCommands(
            bot=bot,
            campaign_context=campaign_context,
            claude_client=claude_client
        )
        
        print("✅ PDF character sheet parser initialized successfully!")
        
        # Verify commands were registered
        if hasattr(bot.pdf_character_commands, '_register_commands'):
            print("✅ Command registration method found")
        else:
            print("⚠️ Command registration method not found")
            
    except ImportError as e:
        print(f"❌ PDF character parser import failed: {e}")
        print("   Install required packages: pip install PyPDF2 pymupdf pillow")
        bot.pdf_character_commands = None
        
    except Exception as e:
        print(f"❌ PDF character parser initialization failed: {e}")
        import traceback
        traceback.print_exc()
        bot.pdf_character_commands = None
else:
    print("❌ PDF character parser initialization skipped due to import failure")
    bot.pdf_character_commands = None

# Print final status
if hasattr(bot, 'pdf_character_commands') and bot.pdf_character_commands:
    print("🎉 PDF Character Parser: READY")
else:
    print("💔 PDF Character Parser: NOT AVAILABLE")
    print("   Fallback: Use /character for manual registration")

print("="*60)


async def check_command_availability():
    """Check which commands are actually available after sync"""
    try:
        synced_commands = await bot.tree.fetch_commands()
        command_names = [cmd.name for cmd in synced_commands]
        
        print(f"\n📋 Synced Commands ({len(command_names)}):")
        for name in sorted(command_names):
            print(f"   • {name}")
        
        # Check for PDF commands specifically
        pdf_commands = ['upload_character_sheet', 'character_sheet_help']
        pdf_available = all(cmd in command_names for cmd in pdf_commands)
        
        print(f"\n📄 PDF Commands Status:")
        for cmd in pdf_commands:
            status = "✅" if cmd in command_names else "❌"
            print(f"   {status} {cmd}")
        
        if pdf_available:
            print("🎉 All PDF commands are available!")
        else:
            print("💔 PDF commands are missing from bot")
            print("   This indicates a registration or sync issue")
            
    except Exception as e:
        print(f"❌ Could not check command availability: {e}")


# Database health updates function
def update_database_from_campaign_context(guild_id: str):
    """Update database with current campaign context"""
    if not DATABASE_AVAILABLE:
        return
    
    try:
        current_episode = EpisodeOperations.get_current_episode(guild_id)
        if current_episode and campaign_context.get("session_history"):
            # Update session history in database
            EpisodeOperations.update_session_history(
                current_episode.id,
                campaign_context["session_history"]
            )
        
        # Update guild settings including current scene
        guild_id_int = int(guild_id) if guild_id.isdigit() else None
        if guild_id_int:
            # Update guild settings with current voice preferences
            settings_update = {
                'voice_speed': voice_speed.get(guild_id_int, 1.25),
                'tts_enabled': tts_enabled.get(guild_id_int, False),
                'current_scene': campaign_context.get("current_scene", ""),
                'current_episode': campaign_context.get("current_episode", 0)
            }
            
            GuildOperations.update_guild_settings(guild_id, **settings_update)
            print(f"✅ Updated database settings for guild {guild_id}")
    except Exception as e:
        print(f"⚠️ Failed to update database from campaign context: {e}")

# Configure performance mode for optimal gameplay
configure_performance_mode(fast_mode=True)  # Enable fast mode by default

# Final system status report
def print_system_status():
    """Print comprehensive system status on startup"""
    print("\n" + "="*60)
    print("🎲 STORM KING'S THUNDER BOT - SYSTEM STATUS")
    print("="*60)
    
    print(f"🗃️  Database: {'✅ Active' if DATABASE_AVAILABLE else '❌ Disabled'}")
    print(f"📺 Episodes: {'✅ Active' if episode_commands else '❌ Disabled'}")
    print(f"📈 Progression: {'✅ Active' if character_progression else '❌ Disabled'}")
    print(f"🧠 Persistent Memory: {'✅ Active' if PERSISTENT_MEMORY_AVAILABLE else '❌ Disabled'}")
    print(f"⚔️  Enhanced Combat: {'✅ Active' if COMBAT_AVAILABLE else '❌ Disabled'}")
    print(f"📄 PDF Parser: {'✅ Active' if getattr(bot, 'pdf_character_commands', None) else '❌ Disabled'}")
    print(f"🎵 FFmpeg (Voice): {'✅ Active' if FFMPEG_AVAILABLE else '❌ Disabled'}")
    
    print("\n⚡ PERFORMANCE SETTINGS:")
    print(f"   Memory Retrieval: {MAX_MEMORIES_FAST} items (fast mode)")
    print(f"   Background Processing: {'✅ Enabled' if BACKGROUND_PROCESSING else '❌ Disabled'}")
    print(f"   Response Length Limit: {MAX_RESPONSE_LENGTH} chars")
    print(f"   Response Timeout: {RESPONSE_TIMEOUT}s")
    
    print("\n🎯 KEY FEATURES:")
    print("   • Fast AI responses with Continue buttons")
    print("   • Enhanced combat with auto-updating displays")
    print("   • Persistent memory across episodes")
    print("   • PDF character sheet auto-parsing")
    print("   • Voice narration with optimized TTS")
    print("   • Episode management with recaps")
    print("   • Character progression tracking")
    print("   • Safe User/Member type checking for voice")
    
    print("\n🚀 Ready for enhanced D&D adventures!")
    print("="*60 + "\n")

# Run the bot
if __name__ == "__main__":
    # Check for required dependencies
    print("🔍 Checking dependencies...")
    try:
        import discord
        print("✅ discord.py installed")
    except ImportError:
        print("❌ Install discord.py[voice]: pip install discord.py[voice]")
        exit(1)
    
    # FFmpeg already checked at top of file
    
    # Check for PDF dependencies
    try:
        import PyPDF2
        import fitz  # PyMuPDF
        print("✅ PDF processing libraries detected")
    except ImportError:
        print("⚠️ PDF processing libraries not found")
        print("Install with: pip install PyPDF2 pymupdf pillow")
    
    # Enhanced memory system initialization messages
    if PERSISTENT_MEMORY_AVAILABLE:
        print("✅ ENHANCED MEMORY SYSTEM loaded!")
        print("🧠 Features: Persistent conversations, NPC tracking, plot thread management")
        print("📊 Alpha Donnie will remember everything across episodes and sessions!")
    else:
        print("⚠️ Enhanced memory system not available")
        print("Install enhanced_dm_system.py and memory_operations.py for persistent memory")
    
    # Streamlined combat system initialization messages
    print("✅ STREAMLINED Combat System loaded!")
    print("⚡ Features: Fast keyword detection, Continue buttons, essential combat tracking")
    print("🎯 No heavy AI systems - optimized for speed and responsiveness!")
    print("▶️ Continue buttons allow anyone to advance the story for faster gameplay")
    print("🚀 All responses under 700 characters for maximum speed")
    
    # Voice system status
    if FFMPEG_AVAILABLE:
        print("✅ VOICE SYSTEM: FFmpeg detected - voice features enabled")
        print("🎤 Features: Safe Member/User checking, proper error handling, timeout protection")
    else:
        print("❌ VOICE SYSTEM: FFmpeg not found - voice features disabled")
        print("Install FFmpeg from https://ffmpeg.org/download.html")
    
    # GET THE DISCORD TOKEN
    print("🔑 Checking Discord token...")
    try:
        token = os.getenv('DISCORD_BOT_TOKEN')
        if not token:
            print("❌ DISCORD_BOT_TOKEN not found in environment variables!")
            print("Make sure you have a .env file with DISCORD_BOT_TOKEN=your_token_here")
            print("Current working directory:", os.getcwd())
            print("Looking for .env file...")
            
            # Check if .env exists
            if os.path.exists('.env'):
                print("✅ .env file found")
                # Try to load it manually to see what's wrong
                with open('.env', 'r') as f:
                    content = f.read()
                    if 'DISCORD_BOT_TOKEN' in content:
                        print("✅ DISCORD_BOT_TOKEN found in .env")
                    else:
                        print("❌ DISCORD_BOT_TOKEN not found in .env file")
            else:
                print("❌ .env file not found")
            
            input("Press Enter to exit...")
            exit(1)
        else:
            print("✅ Discord token found")
    except Exception as e:
        print(f"❌ Error checking token: {e}")
        input("Press Enter to exit...")
        exit(1)
    
    
    # TRY TO START THE BOT WITH FULL ERROR HANDLING
    print("🚀 Starting Discord bot...")
    try:
        bot.run(token)
    except discord.LoginFailure:
        print("❌ INVALID DISCORD TOKEN!")
        print("Check that your bot token is correct in the .env file")
        input("Press Enter to exit...")
    except discord.HTTPException as e:
        print(f"❌ Discord HTTP Error: {e}")
        print("This might be a network issue or Discord API problem")
        input("Press Enter to exit...")
    except KeyboardInterrupt:
        print("🛑 Bot shutdown requested")
    except Exception as e:
        print(f"❌ UNEXPECTED ERROR: {e}")
        print("Full error details:")
        import traceback
        traceback.print_exc()
        input("Press Enter to exit...")
    finally:
        if DATABASE_AVAILABLE:
            try:
                close_database()
                print("✅ Cleanup completed")
            except:
                pass
        print("🛑 Bot stopped")