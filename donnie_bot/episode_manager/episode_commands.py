# episode_manager/episode_commands.py
# UPDATE: Replace your existing episode_commands.py with this enhanced version

import discord
from discord.ext import commands
from discord import app_commands
from typing import Optional, Dict, Any, Callable
import asyncio
from datetime import datetime
import random

# Import our database operations
try:
    from database.operations import EpisodeOperations, CharacterOperations, GuildOperations, DatabaseOperationError
    DATABASE_AVAILABLE = True
except ImportError:
    DATABASE_AVAILABLE = False
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
    
    class CharacterOperations:
        @staticmethod
        def create_character_snapshot(*args, **kwargs): return None
    
    class GuildOperations:
        @staticmethod
        def update_guild_settings(*args, **kwargs): return False

class EpisodeCommands:
    """Enhanced Episode Management with Database Integration"""
    
    def __init__(self, bot: commands.Bot, campaign_context: Dict, voice_clients: Dict,
                 tts_enabled: Dict, add_to_voice_queue_func: Callable,
                 episode_operations=None, character_operations=None, guild_operations=None):
        self.bot = bot
        self.campaign_context = campaign_context
        self.voice_clients = voice_clients
        self.tts_enabled = tts_enabled
        self.add_to_voice_queue = add_to_voice_queue_func
        
        # Store database operations classes
        self.episode_ops = episode_operations or EpisodeOperations
        self.character_ops = character_operations or CharacterOperations
        self.guild_ops = guild_operations or GuildOperations
        
        # Register commands
        self._register_commands()
        
        print(f"✅ Episode Commands initialized (Database: {'✅' if DATABASE_AVAILABLE else '❌'})")
    
    def _register_commands(self):
        """Register all episode-related commands"""
        
        @self.bot.tree.command(name="start_episode", description="Begin a new episode with database tracking and AI recap")
        @app_commands.describe(
            episode_name="Optional name for this episode",
            recap_previous="Generate AI recap of previous episodes"
        )
        async def start_episode(interaction: discord.Interaction, 
                              episode_name: Optional[str] = None,
                              recap_previous: bool = True):
            await self._start_episode_command(interaction, episode_name, recap_previous)
        
        @self.bot.tree.command(name="end_episode", description="End the current episode with summary and character snapshots")
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
    
    async def _start_episode_command(self, interaction: discord.Interaction, 
                                   episode_name: Optional[str], recap_previous: bool):
        """Start a new episode with database integration"""
        guild_id = str(interaction.guild.id)
        
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
                print(f"Error checking current episode: {e}")
        
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
        if DATABASE_AVAILABLE:
            try:
                episode_number = self.episode_ops.get_next_episode_number(guild_id)
            except Exception as e:
                print(f"Error getting episode number: {e}")
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
                print(f"Database episode creation failed: {e}")
        
        # Update campaign context
        self.campaign_context["episode_active"] = True
        self.campaign_context["current_episode"] = episode_number
        self.campaign_context["episode_start_time"] = datetime.now()
        self.campaign_context["guild_id"] = guild_id
        self.campaign_context["session_started"] = True  # For compatibility
        
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
                    print(f"Error creating character snapshot: {e}")
        
        # Create response embed
        embed = discord.Embed(
            title=f"🎬 {episode_name}",
            description="**Episode begins!** The adventure continues in the Storm King's Thunder campaign.",
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
        
        # Add database status
        if DATABASE_AVAILABLE:
            embed.add_field(
                name="💾 Episode Tracking",
                value="✅ Character snapshots saved\n✅ Progress will be tracked\n✅ Recaps available anytime",
                inline=False
            )
        
        embed.set_footer(text=f"Episode {episode_number} • {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        
        await interaction.response.send_message(embed=embed)
        
        # Add to voice queue if enabled
        voice_will_speak = (interaction.guild.id in self.voice_clients and 
                           self.voice_clients[interaction.guild.id].is_connected() and 
                           self.tts_enabled.get(interaction.guild.id, False))
        
        if voice_will_speak:
            announcement = f"Welcome, brave adventurers, to {episode_name}! Your journey through the Storm King's Thunder campaign continues. The giants still threaten the Sword Coast, and heroes are needed now more than ever. What will you do first?"
            await self.add_to_voice_queue(interaction.guild.id, announcement, "Episode Start")
    
    async def _end_episode_command(self, interaction: discord.Interaction, summary: Optional[str]):
        """End the current episode with database integration"""
        guild_id = str(interaction.guild.id)
        
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
                print(f"Error checking current episode: {e}")
        
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
        
        # End episode in database
        if DATABASE_AVAILABLE and current_episode:
            try:
                # Update session history in database
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
                        print(f"Error creating end snapshot: {e}")
                        
                print(f"✅ Episode {episode_number} ended in database")
                        
            except Exception as e:
                print(f"Error ending episode in database: {e}")
        
        # Update campaign context
        self.campaign_context["episode_active"] = False
        self.campaign_context["episode_start_time"] = None
        
        # Create response
        embed = discord.Embed(
            title=f"🎬 Episode {episode_number} Complete!",
            description="**Episode concluded!** Your adventure progress has been saved.",
            color=0x32CD32
        )
        
        embed.add_field(
            name="📝 Episode Summary",
            value=summary,
            inline=False
        )
        
        if DATABASE_AVAILABLE:
            embed.add_field(
                name="💾 Progress Saved",
                value="✅ Character snapshots created\n✅ Episode summary recorded\n✅ Session history preserved",
                inline=False
            )
        
        embed.add_field(
            name="🎉 Next Steps",
            value="Use `/episode_recap` for a dramatic retelling!\nStart the next episode with `/start_episode`",
            inline=False
        )
        
        embed.set_footer(text=f"Episode ended • {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        
        await interaction.response.send_message(embed=embed)
        
        # Voice announcement
        voice_will_speak = (interaction.guild.id in self.voice_clients and 
                           self.voice_clients[interaction.guild.id].is_connected() and 
                           self.tts_enabled.get(interaction.guild.id, False))
        
        if voice_will_speak:
            announcement = f"And so concludes Episode {episode_number} of your Storm King's Thunder adventure! The heroes have faced new challenges and grown stronger. What legends will the next episode bring?"
            await self.add_to_voice_queue(interaction.guild.id, announcement, "Episode End")
    
    async def _episode_recap_command(self, interaction: discord.Interaction, 
                                   episode_number: int, style: str):
        """Generate AI recap of episodes"""
        await interaction.response.send_message("🎭 *Donnie prepares a dramatic recap...* (This feature will be enhanced in the next update!)", ephemeral=True)
    
    async def _episode_history_command(self, interaction: discord.Interaction):
        """Show episode history"""
        guild_id = str(interaction.guild.id)
        
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
                embed.set_footer(text=f"Showing last 5 of {len(episodes)} episodes")
            
            await interaction.response.send_message(embed=embed)
            
        except Exception as e:
            embed = discord.Embed(
                title="❌ Error Loading History",
                description=f"Could not load episode history: {str(e)}",
                color=0xFF6B6B
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
    
    async def _episode_status_command(self, interaction: discord.Interaction):
        """Show current episode status"""
        guild_id = str(interaction.guild.id)
        
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
                else:
                    embed.description = "No episode is currently active."
                    embed.add_field(
                        name="🎬 Start New Episode",
                        value="Use `/start_episode` to begin your next adventure!",
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