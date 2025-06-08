import discord
from discord.ext import commands
from discord import app_commands
from typing import Optional, Dict, Any, Callable
import asyncio
from datetime import datetime
import random

# Import our database operations with better error handling
try:
    from database.operations import EpisodeOperations, CharacterOperations, GuildOperations, DatabaseOperationError
    DATABASE_AVAILABLE = True
    print("✅ Episode commands: Database operations imported successfully")
except ImportError as e:
    DATABASE_AVAILABLE = False
    print(f"❌ Episode commands: Database operations failed: {e}")
    # Create fallback classes to prevent crashes
    class EpisodeOperations:
        @staticmethod
        def create_episode(*args, **kwargs): return None
        @staticmethod
        def get_current_episode(*args, **kwargs): return None
        @staticmethod
        def end_episode(*args, **kwargs): return False
        @staticmethod
        def get_episode_history(*args, **kwargs): return []
        @staticmethod
        def get_next_episode_number(*args, **kwargs): return 1
        @staticmethod
        def update_session_history(*args, **kwargs): pass
    
    class CharacterOperations:
        @staticmethod
        def create_character_snapshot(*args, **kwargs): return None
    
    class GuildOperations:
        @staticmethod
        def update_guild_settings(*args, **kwargs): return False
        @staticmethod
        def get_guild_settings(*args, **kwargs): return {}

    class DatabaseOperationError(Exception):
        pass

# Import Enhanced DM System for memory consolidation
try:
    from enhanced_dm_system import EnhancedMemoryManager
    PERSISTENT_MEMORY_AVAILABLE = True
    print("✅ Episode commands: Enhanced DM system available for memory consolidation")
except ImportError:
    PERSISTENT_MEMORY_AVAILABLE = False
    print("⚠️ Episode commands: Enhanced DM system not available - memory consolidation disabled")

class EpisodeCommands:
    """FIXED: Enhanced Episode Management with proper initialization and error handling"""
    
    def __init__(self, bot: commands.Bot, campaign_context: Dict, voice_clients: Dict,
             tts_enabled: Dict, add_to_voice_queue_func: Callable,
             episode_operations=None, character_operations=None, guild_operations=None,
             claude_client=None, sync_function=None, unified_response_system=None):
        
        self.bot = bot
        self.campaign_context = campaign_context
        self.voice_clients = voice_clients
        self.tts_enabled = tts_enabled
        self.add_to_voice_queue = add_to_voice_queue_func
        self.unified_response_system = unified_response_system
        
        # Store database operations classes with fallbacks
        self.episode_ops = episode_operations or EpisodeOperations
        self.character_ops = character_operations or CharacterOperations
        self.guild_ops = guild_operations or GuildOperations
        
        # Store passed parameters
        self.claude_client = claude_client
        self.sync_function = sync_function
        
        # Track if commands have been registered for this bot instance
        self.commands_registered = False
        
        # Register commands
        self._register_commands()
        
        print(f"✅ Episode Commands initialized")
        print(f"🔄 State Sync: {'✅' if self.sync_function else '❌'}")
        print(f"🧠 Memory Consolidation: {'✅' if self.unified_response_system else '❌'}")
        print(f"🤖 Claude Client: {'✅' if self.claude_client else '❌'}")
        print(f"📊 Database: {'✅' if DATABASE_AVAILABLE else '❌'}")
    
    def _register_commands(self):
        """FIXED: Register commands with proper error handling and no duplicate registration"""
        
        if self.commands_registered:
            print("⚠️ Episode commands already registered for this instance")
            return
        
        try:
            # Clear any existing commands with these names to prevent conflicts
            existing_commands = []
            for command in self.bot.tree.get_commands():
                if command.name in ['start_episode', 'end_episode', 'episode_recap', 'episode_history', 'episode_status']:
                    existing_commands.append(command)
            
            for cmd in existing_commands:
                self.bot.tree.remove_command(cmd.name)
            
            print("📺 Registering episode commands...")
            
            @self.bot.tree.command(name="start_episode", description="Begin a new episode with database tracking and AI recap")
            @app_commands.describe(
                episode_name="Optional name for this episode",
                recap_previous="Generate AI recap of previous episodes"
            )
            async def start_episode(interaction: discord.Interaction, 
                                  episode_name: Optional[str] = None,
                                  recap_previous: bool = True):
                await self._start_episode_command(interaction, episode_name, recap_previous)
            
            @self.bot.tree.command(name="end_episode", description="End the current episode with summary, character snapshots, and memory consolidation")
            @app_commands.describe(summary="Optional summary of what happened this episode")
            async def end_episode(interaction: discord.Interaction, summary: Optional[str] = None):
                await self._end_episode_command(interaction, summary)
            
            @self.bot.tree.command(name="episode_recap", description="Get an AI-generated dramatic recap of previous episodes")
            @app_commands.describe(
                episode_number="Specific episode to recap (0 for all)",
                style="Recap style"
            )
            @app_commands.choices(style=[
                app_commands.Choice(name="Dramatic & Epic", value="dramatic"),
                app_commands.Choice(name="Quick Summary", value="quick"),
                app_commands.Choice(name="Character Focus", value="character"),
                app_commands.Choice(name="Comedy Style", value="comedy")
            ])
            async def episode_recap(interaction: discord.Interaction, 
                                  episode_number: int = 0,
                                  style: str = "dramatic"):
                await self._episode_recap_command(interaction, episode_number, style)
            
            @self.bot.tree.command(name="episode_history", description="View episode history and campaign timeline")
            async def episode_history(interaction: discord.Interaction):
                await self._episode_history_command(interaction)
            
            @self.bot.tree.command(name="episode_status", description="Check current episode status and progress")
            async def episode_status(interaction: discord.Interaction):
                await self._episode_status_command(interaction)
            
            self.commands_registered = True
            print("✅ Episode commands registered successfully")
            
        except Exception as e:
            print(f"❌ Failed to register episode commands: {e}")
            import traceback
            traceback.print_exc()
    
    def _safe_guild_id_conversion(self, guild_id) -> str:
        """FIXED: Safely convert guild ID to string for database operations"""
        if isinstance(guild_id, str):
            return guild_id
        elif isinstance(guild_id, int):
            return str(guild_id)
        elif hasattr(guild_id, 'id'):
            return str(guild_id.id)
        else:
            raise ValueError(f"Invalid guild_id type: {type(guild_id)}")
    
    async def _start_episode_command(self, interaction: discord.Interaction, 
                                   episode_name: Optional[str], recap_previous: bool):
        """FIXED: Start episode with proper error handling and state sync"""
        
        try:
            guild_id = self._safe_guild_id_conversion(interaction.guild.id)
            
            # Check if episode is already active
            if DATABASE_AVAILABLE:
                try:
                    current_episode = self.episode_ops.get_current_episode(guild_id)
                    if current_episode:
                        embed = discord.Embed(
                            title="⚠️ Episode Already Active",
                            description=f"Episode {current_episode.episode_number} '{current_episode.name}' is currently running!",
                            color=0xFFD700
                        )
                        embed.add_field(
                            name="💡 Options",
                            value="Use `/end_episode` first, or `/episode_status` to check progress",
                            inline=False
                        )
                        await interaction.response.send_message(embed=embed, ephemeral=True)
                        return
                except Exception as e:
                    print(f"⚠️ Error checking current episode: {e}")
            
            # Check if characters are registered
            if not self.campaign_context.get("characters"):
                embed = discord.Embed(
                    title="🎭 No Characters Registered",
                    description="Register characters before starting an episode!",
                    color=0xFF6B6B
                )
                embed.add_field(
                    name="📝 Required First",
                    value="Use `/character` to register your character, then start the episode.",
                    inline=False
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return
            
            # Get next episode number
            episode_number = 1
            if DATABASE_AVAILABLE:
                try:
                    episode_number = self.episode_ops.get_next_episode_number(guild_id)
                except Exception as e:
                    print(f"⚠️ Error getting episode number: {e}")
                    episode_number = self.campaign_context.get("current_episode", 0) + 1
            else:
                episode_number = self.campaign_context.get("current_episode", 0) + 1
            
            # Generate episode name if not provided
            if not episode_name:
                episode_name = f"Episode {episode_number}: The Adventure Continues"
            
            # Create episode in database
            episode = None
            if DATABASE_AVAILABLE:
                try:
                    episode = self.episode_ops.create_episode(
                        guild_id=guild_id,
                        episode_number=episode_number,
                        name=episode_name,
                        scene_data=self.campaign_context.get("current_scene", "")
                    )
                    print(f"✅ Created database episode: {episode.name}")
                except DatabaseOperationError as e:
                    embed = discord.Embed(
                        title="❌ Episode Creation Failed",
                        description=str(e),
                        color=0xFF6B6B
                    )
                    await interaction.response.send_message(embed=embed, ephemeral=True)
                    return
                except Exception as e:
                    print(f"⚠️ Database episode creation failed: {e}")
            
            # Update campaign context with proper state sync
            self.campaign_context["episode_active"] = True
            self.campaign_context["current_episode"] = episode_number
            self.campaign_context["episode_start_time"] = datetime.now()
            self.campaign_context["guild_id"] = guild_id
            self.campaign_context["session_started"] = True
            
            # Create character snapshots
            if DATABASE_AVAILABLE and episode:
                for user_id, player_data in self.campaign_context["players"].items():
                    try:
                        char_data = player_data["character_data"]
                        self.character_ops.create_character_snapshot(
                            episode_id=episode.id,
                            user_id=user_id,
                            character_name=char_data["name"],
                            character_data=char_data,
                            snapshot_type="episode_start",
                            notes=f"Episode {episode_number} start"
                        )
                    except Exception as e:
                        print(f"⚠️ Error creating character snapshot: {e}")
            
            # Create response embed
            embed = discord.Embed(
                title=f"🎬 {episode_name}",
                description="**Episode begins!** The adventure continues in the Storm King's Thunder campaign with enhanced memory.",
                color=0x4169E1
            )
            
            # Add party information
            party_info = []
            for user_id, player_data in self.campaign_context["players"].items():
                char_data = player_data["character_data"]
                party_info.append(f"🎭 **{char_data['name']}** - Level {char_data['level']} {char_data['race']} {char_data['class']}")
            
            embed.add_field(
                name="🗡️ Adventuring Party",
                value="\n".join(party_info),
                inline=False
            )
            
            embed.add_field(
                name="📍 Current Scene",
                value=self.campaign_context.get("current_scene", "The adventure awaits..."),
                inline=False
            )
            
            embed.add_field(
                name="🎮 Ready for Action",
                value="Use `/action <what you do>` to begin your adventure!\n🎤 Use `/join_voice` for Donnie's dramatic narration!",
                inline=False
            )
            
            # Add enhanced features status
            features = []
            if DATABASE_AVAILABLE:
                features.append("✅ Character snapshots saved")
                features.append("✅ Progress will be tracked")
                features.append("✅ Recaps available anytime")
            
            if PERSISTENT_MEMORY_AVAILABLE:
                features.append("✅ Enhanced memory active")
                features.append("✅ NPCs will be remembered") 
                features.append("✅ Past events referenced")
            
            if features:
                embed.add_field(
                    name="💾 Enhanced Features",
                    value="\n".join(features),
                    inline=False
                )
            
            embed.set_footer(text=f"Episode {episode_number} • {datetime.now().strftime('%Y-%m-%d %H:%M')}")
            
            await interaction.response.send_message(embed=embed)
            
            # Add to voice queue if enabled
            guild_id_int = int(guild_id)
            voice_will_speak = (guild_id_int in self.voice_clients and 
                               self.voice_clients[guild_id_int].is_connected() and 
                               self.tts_enabled.get(guild_id_int, False))
            
            if voice_will_speak:
                announcement = f"Welcome, brave adventurers, to {episode_name}! Your journey through the Storm King's Thunder campaign continues with enhanced memory. The giants still threaten the Sword Coast, and heroes are needed now more than ever. What will you do first?"
                await self.add_to_voice_queue(guild_id_int, announcement, "Episode Start")
            
            # Sync campaign state
            if self.sync_function:
                try:
                    self.sync_function(guild_id)
                    print(f"🔄 Episode {episode_number} started and state synced")
                except Exception as e:
                    print(f"⚠️ State sync failed: {e}")
            else:
                print(f"⚠️ Could not sync state after episode start - sync function unavailable")
                
        except Exception as e:
            print(f"❌ Critical error in start_episode_command: {e}")
            import traceback
            traceback.print_exc()
            
            try:
                embed = discord.Embed(
                    title="❌ Episode Start Failed",
                    description=f"An unexpected error occurred: {str(e)}",
                    color=0xFF6B6B
                )
                if not interaction.response.is_done():
                    await interaction.response.send_message(embed=embed, ephemeral=True)
                else:
                    await interaction.followup.send(embed=embed, ephemeral=True)
            except:
                pass  # Fail silently if we can't even send error message
    
    async def _end_episode_command(self, interaction: discord.Interaction, summary: Optional[str]):
        """FIXED: End episode with proper error handling and memory consolidation"""
        
        try:
            guild_id = self._safe_guild_id_conversion(interaction.guild.id)
            
            # Check if episode is active
            current_episode = None
            if DATABASE_AVAILABLE:
                try:
                    current_episode = self.episode_ops.get_current_episode(guild_id)
                    if not current_episode:
                        embed = discord.Embed(
                            title="⚠️ No Active Episode",
                            description="No episode is currently running!",
                            color=0xFFD700
                        )
                        await interaction.response.send_message(embed=embed, ephemeral=True)
                        return
                except Exception as e:
                    print(f"⚠️ Error checking current episode: {e}")
            
            if not self.campaign_context.get("episode_active"):
                embed = discord.Embed(
                    title="⚠️ No Active Episode", 
                    description="No episode is currently running!",
                    color=0xFFD700
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return
            
            episode_number = self.campaign_context.get("current_episode", 0)
            
            # Generate summary if not provided
            if not summary:
                summary = f"The heroes continue their quest in the Storm King's Thunder campaign. Episode {episode_number} concludes with new challenges ahead."
            
            # Send initial response
            embed = discord.Embed(
                title="🔄 Ending Episode...",
                description="Donnie is consolidating memories and saving progress...",
                color=0xFFD700
            )
            await interaction.response.send_message(embed=embed)
            
            # Memory consolidation
            memory_consolidation_result = None
            if DATABASE_AVAILABLE and current_episode and self.unified_response_system:
                try:
                    print(f"🧠 Consolidating memories for episode {episode_number}")
                    
                    # Use unified system's memory operations
                    if hasattr(self.unified_response_system, 'memory_ops') and self.unified_response_system.memory_ops:
                        memory_consolidation_result = await self.unified_response_system.memory_ops.consolidate_episode_memories(
                            guild_id, current_episode.id
                        )
                        
                        if memory_consolidation_result:
                            print(f"✅ Episode {episode_number} memories consolidated via unified system")
                        else:
                            print(f"⚠️ No memories to consolidate for episode {episode_number}")
                    else:
                        print("⚠️ Memory operations not available in unified system")
                        
                except Exception as e:
                    print(f"⚠️ Memory consolidation failed: {e}")
            
            # End episode in database
            if DATABASE_AVAILABLE and current_episode:
                try:
                    # Update session history
                    if self.campaign_context.get("session_history"):
                        self.episode_ops.update_session_history(
                            current_episode.id, 
                            self.campaign_context["session_history"]
                        )
                    
                    # End the episode
                    self.episode_ops.end_episode(current_episode.id, summary)
                    
                    # Create end-of-episode character snapshots
                    for user_id, player_data in self.campaign_context["players"].items():
                        try:
                            char_data = player_data["character_data"]
                            self.character_ops.create_character_snapshot(
                                episode_id=current_episode.id,
                                user_id=user_id,
                                character_name=char_data["name"],
                                character_data=char_data,
                                snapshot_type="episode_end",
                                notes=f"Episode {episode_number} end"
                            )
                        except Exception as e:
                            print(f"⚠️ Error creating end snapshot: {e}")
                            
                    print(f"✅ Episode {episode_number} ended in database")
                            
                except Exception as e:
                    print(f"⚠️ Error ending episode in database: {e}")
            
            # Update campaign context
            self.campaign_context["episode_active"] = False
            self.campaign_context["episode_start_time"] = None
            self.campaign_context["session_started"] = False
            
            # Create final response embed
            embed = discord.Embed(
                title=f"🎬 Episode {episode_number} Complete!",
                description="**Episode concluded!** Your adventure progress has been saved with enhanced memory consolidation.",
                color=0x32CD32
            )
            
            embed.add_field(
                name="📝 Episode Summary",
                value=summary,
                inline=False
            )
            
            # Add memory consolidation results if available
            if memory_consolidation_result:
                memory_summary = []
                
                key_events = memory_consolidation_result.get('key_events', [])
                if key_events:
                    memory_summary.append(f"🎯 **{len(key_events)} key events** preserved")
                
                if memory_summary:
                    embed.add_field(
                        name="🧠 Memory Consolidation",
                        value="\n".join(memory_summary),
                        inline=False
                    )
            
            if DATABASE_AVAILABLE:
                database_features = [
                    "✅ Character snapshots created",
                    "✅ Episode summary recorded", 
                    "✅ Session history preserved"
                ]
                
                if memory_consolidation_result:
                    database_features.append("✅ Memories consolidated for future episodes")
                
                embed.add_field(
                    name="💾 Progress Saved",
                    value="\n".join(database_features),
                    inline=False
                )
            
            embed.add_field(
                name="🎉 Next Steps",
                value="Use `/episode_recap` for a dramatic retelling!\nStart the next episode with `/start_episode` - Donnie will remember everything!",
                inline=False
            )
            
            embed.set_footer(text=f"Episode ended • {datetime.now().strftime('%Y-%m-%d %H:%M')}")
            
            # Update the original message
            original_message = await interaction.original_response()
            await original_message.edit(embed=embed)
            
            # Voice announcement
            guild_id_int = int(guild_id)
            voice_will_speak = (guild_id_int in self.voice_clients and 
                               self.voice_clients[guild_id_int].is_connected() and 
                               self.tts_enabled.get(guild_id_int, False))
            
            if voice_will_speak:
                consolidation_note = ""
                if memory_consolidation_result:
                    consolidation_note = " Your memories have been preserved for future adventures."
                
                announcement = f"And so concludes Episode {episode_number} of your Storm King's Thunder adventure! The heroes have faced new challenges and grown stronger.{consolidation_note} What legends will the next episode bring?"
                await self.add_to_voice_queue(guild_id_int, announcement, "Episode End")
            
            # Sync campaign state
            if self.sync_function:
                try:
                    self.sync_function(guild_id)
                    print(f"🔄 Episode {episode_number} ended and state synced")
                except Exception as e:
                    print(f"⚠️ State sync failed: {e}")
            else:
                print(f"⚠️ Could not sync state after episode end - sync function unavailable")
                
        except Exception as e:
            print(f"❌ Critical error in end_episode_command: {e}")
            import traceback
            traceback.print_exc()
            
            try:
                embed = discord.Embed(
                    title="❌ Episode End Failed",
                    description=f"An unexpected error occurred: {str(e)}",
                    color=0xFF6B6B
                )
                if not interaction.response.is_done():
                    await interaction.response.send_message(embed=embed, ephemeral=True)
                else:
                    await interaction.followup.send(embed=embed, ephemeral=True)
            except:
                pass
    
    async def _episode_recap_command(self, interaction: discord.Interaction, 
                                   episode_number: int, style: str):
        """Generate AI recap of episodes"""
        await interaction.response.send_message("🎭 *Donnie prepares a dramatic recap...* (This feature will be enhanced in the next update!)", ephemeral=True)
    
    async def _episode_history_command(self, interaction: discord.Interaction):
        """Show episode history with proper error handling"""
        
        try:
            guild_id = self._safe_guild_id_conversion(interaction.guild.id)
            
            if not DATABASE_AVAILABLE:
                embed = discord.Embed(
                    title="⚠️ Database Required",
                    description="Episode history requires database functionality.",
                    color=0xFFD700
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return
            
            try:
                episodes = self.episode_ops.get_episode_history(guild_id, limit=10)
                
                if not episodes:
                    embed = discord.Embed(
                        title="📺 No Episode History",
                        description="No episodes have been recorded yet!",
                        color=0x808080
                    )
                    await interaction.response.send_message(embed=embed)
                    return
                
                embed = discord.Embed(
                    title="📺 Episode History",
                    description="Your Storm King's Thunder campaign timeline:",
                    color=0x4169E1
                )
                
                for episode in episodes[:5]:  # Show last 5 episodes
                    status = "🟢 Active" if not episode.end_time else "✅ Complete"
                    duration = ""
                    if episode.end_time and episode.start_time:
                        delta = episode.end_time - episode.start_time
                        hours = delta.total_seconds() / 3600
                        duration = f" ({hours:.1f}h)"
                    
                    embed.add_field(
                        name=f"Episode {episode.episode_number}: {episode.name}",
                        value=f"{status}{duration}\n{episode.start_time.strftime('%Y-%m-%d') if episode.start_time else 'Unknown date'}",
                        inline=True
                    )
                
                if len(episodes) > 5:
                    embed.set_footer(text=f"Showing last 5 of {len(episodes)} episodes • Enhanced with persistent memory")
                else:
                    embed.set_footer(text="Enhanced with persistent memory")
                
                await interaction.response.send_message(embed=embed)
                
            except Exception as e:
                embed = discord.Embed(
                    title="❌ Error Loading History",
                    description=f"Could not load episode history: {str(e)}",
                    color=0xFF6B6B
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                
        except Exception as e:
            print(f"❌ Critical error in episode_history_command: {e}")
            try:
                embed = discord.Embed(
                    title="❌ History Command Failed",
                    description="An unexpected error occurred",
                    color=0xFF6B6B
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
            except:
                pass
    
    async def _episode_status_command(self, interaction: discord.Interaction):
        """Show current episode status with proper error handling"""
        
        try:
            guild_id = self._safe_guild_id_conversion(interaction.guild.id)
            
            # Sync state if possible
            if self.sync_function:
                try:
                    self.sync_function(guild_id)
                except Exception as e:
                    print(f"⚠️ State sync failed in status command: {e}")
            
            embed = discord.Embed(
                title="📺 Episode Status",
                color=0x4169E1
            )
            
            if DATABASE_AVAILABLE:
                try:
                    current_episode = self.episode_ops.get_current_episode(guild_id)
                    if current_episode:
                        # Calculate duration
                        duration = datetime.now() - current_episode.start_time
                        hours = duration.total_seconds() / 3600
                        
                        embed.description = f"**{current_episode.name}** is currently active!"
                        embed.add_field(
                            name="📊 Episode Info",
                            value=f"**Number:** {current_episode.episode_number}\n**Duration:** {hours:.1f} hours\n**Started:** {current_episode.start_time.strftime('%Y-%m-%d %H:%M')}",
                            inline=False
                        )
                        
                        # Session history count
                        history_count = len(self.campaign_context.get("session_history", []))
                        embed.add_field(
                            name="🎮 Progress",
                            value=f"**Actions Taken:** {history_count}\n**Combat Active:** {'Yes' if self.campaign_context.get('combat_active') else 'No'}",
                            inline=True
                        )
                        
                        # Enhanced features status
                        features_status = []
                        if DATABASE_AVAILABLE:
                            features_status.append("✅ Database tracking")
                        if PERSISTENT_MEMORY_AVAILABLE:
                            features_status.append("✅ Enhanced memory")
                        else:
                            features_status.append("⚠️ Basic memory only")
                        
                        embed.add_field(
                            name="🧠 Enhanced Features",
                            value="\n".join(features_status),
                            inline=True
                        )
                        
                        # State sync verification
                        memory_active = self.campaign_context.get("episode_active", False)
                        memory_started = self.campaign_context.get("session_started", False)
                        
                        sync_status = "✅ Synced" if memory_active and memory_started else "⚠️ Desync"
                        embed.add_field(
                            name="🔄 State Sync",
                            value=f"Memory/DB: {sync_status}\nEpisode Active: {memory_active}\nSession Started: {memory_started}",
                            inline=False
                        )
                    else:
                        embed.description = "No episode is currently active."
                        embed.add_field(
                            name="🎬 Start New Episode",
                            value="Use `/start_episode` to begin your next adventure with enhanced memory!",
                            inline=False
                        )
                        
                        # Show sync status for no active episode
                        memory_active = self.campaign_context.get("episode_active", False)
                        memory_started = self.campaign_context.get("session_started", False)
                        
                        if memory_active or memory_started:
                            embed.add_field(
                                name="⚠️ State Warning",
                                value=f"Memory shows active ({memory_active}/{memory_started}) but DB shows none. Use `/debug_memory` for details.",
                                inline=False
                            )
                except Exception as e:
                    embed.description = f"Error loading episode status: {str(e)}"
            else:
                # Fallback to campaign context
                if self.campaign_context.get("episode_active"):
                    episode_num = self.campaign_context.get("current_episode", 0)
                    embed.description = f"Episode {episode_num} is active (Database disabled)"
                else:
                    embed.description = "No episode is currently active."
            
            await interaction.response.send_message(embed=embed)
            
        except Exception as e:
            print(f"❌ Critical error in episode_status_command: {e}")
            try:
                embed = discord.Embed(
                    title="❌ Status Command Failed",
                    description="An unexpected error occurred",
                    color=0xFF6B6B
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
            except:
                pass