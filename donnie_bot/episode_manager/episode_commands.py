import discord
from discord.ext import commands
from discord import app_commands
from typing import Optional
import asyncio
from datetime import datetime

# Fixed imports - use absolute imports instead of relative
from database.operations import (
    CampaignOperations, EpisodeOperations, CharacterOperations, PlayerNoteOperations
)
from episode_manager.recap_generator import RecapGenerator

class EpisodeCommands:
    """Episode management commands for Donnie the DM bot"""
    
    def __init__(self, bot: commands.Bot, campaign_context: dict, voice_clients: dict, 
                 tts_enabled: dict, add_to_voice_queue_func):
        self.bot = bot
        self.campaign_context = campaign_context
        self.voice_clients = voice_clients
        self.tts_enabled = tts_enabled
        self.add_to_voice_queue = add_to_voice_queue_func
        self.recap_generator = RecapGenerator()
        
        self._register_commands()
    
    def _register_commands(self):
        """Register all episode-related slash commands"""
        
        @self.bot.tree.command(name="start_episode", description="Begin a new episode of Storm King's Thunder")
        @app_commands.describe(
            episode_name="Custom name for this episode (optional)",
            skip_recap="Skip the recap of the previous episode"
        )
        @app_commands.default_permissions(administrator=True)  # Only admins can start episodes
        async def start_episode(interaction: discord.Interaction, 
                              episode_name: Optional[str] = None, 
                              skip_recap: bool = False):
            guild_id = str(interaction.guild.id)
            
            try:
                # Auto-save current character states to database
                await self._sync_characters_to_db(guild_id)
                
                # Start new episode in database
                episode, ended_previous = EpisodeOperations.start_new_episode(guild_id, episode_name)
                
                # Update campaign context
                self.campaign_context["current_episode"] = episode.episode_number
                self.campaign_context["episode_active"] = True
                self.campaign_context["episode_start_time"] = datetime.utcnow()
                self.campaign_context["session_started"] = True
                
                # Create response embed
                embed = discord.Embed(
                    title="📺 New Episode Started!",
                    description=f"**{episode.name}** (Episode {episode.episode_number})",
                    color=0x32CD32
                )
                
                if ended_previous:
                    embed.add_field(
                        name="📝 Previous Episode",
                        value="Previous episode automatically saved and ended",
                        inline=False
                    )
                
                embed.add_field(
                    name="⚡ Episode Details",
                    value=f"Started: {episode.start_time.strftime('%Y-%m-%d %H:%M:%S')}\nStatus: Active",
                    inline=True
                )
                
                # Character sync info
                character_count = len(self.campaign_context.get("characters", {}))
                embed.add_field(
                    name="🎭 Characters",
                    value=f"{character_count} characters synced to database",
                    inline=True
                )
                
                await interaction.response.send_message(embed=embed)
                
                # Generate and deliver recap if requested
                if not skip_recap and episode.episode_number > 1:
                    await self._deliver_episode_recap(interaction, episode.episode_number - 1)
                
            except Exception as e:
                error_embed = discord.Embed(
                    title="❌ Episode Start Failed",
                    description=f"Failed to start episode: {str(e)}",
                    color=0xFF6B6B
                )
                await interaction.response.send_message(embed=error_embed, ephemeral=True)
        
        @self.bot.tree.command(name="end_episode", description="End the current episode and save progress")
        @app_commands.describe(
            summary="Brief summary of what happened this episode",
            cliffhanger="How the episode ended / what happens next",
            dm_notes="Private DM notes about the episode"
        )
        @app_commands.default_permissions(administrator=True)
        async def end_episode(interaction: discord.Interaction, 
                            summary: Optional[str] = None,
                            cliffhanger: Optional[str] = None,
                            dm_notes: Optional[str] = None):
            guild_id = str(interaction.guild.id)
            
            try:
                # Auto-save current character states
                await self._sync_characters_to_db(guild_id)
                
                # End episode in database
                episode = EpisodeOperations.end_current_episode(
                    guild_id, summary, dm_notes, cliffhanger, []
                )
                
                if not episode:
                    await interaction.response.send_message(
                        "❌ No active episode to end!", ephemeral=True
                    )
                    return
                
                # Update campaign context
                self.campaign_context["episode_active"] = False
                self.campaign_context["session_started"] = False
                
                # Create response embed
                embed = discord.Embed(
                    title="🎬 Episode Completed!",
                    description=f"**{episode.name}** has been saved",
                    color=0x4169E1
                )
                
                embed.add_field(
                    name="⏱️ Session Stats",
                    value=f"Duration: {episode.duration_hours:.1f} hours\nEpisode: {episode.episode_number}",
                    inline=True
                )
                
                embed.add_field(
                    name="💾 Saved Data",
                    value="Character snapshots\nEpisode summary\nStory progression",
                    inline=True
                )
                
                if episode.summary:
                    embed.add_field(
                        name="📋 Episode Summary",
                        value=episode.summary[:200] + ("..." if len(episode.summary) > 200 else ""),
                        inline=False
                    )
                
                if episode.cliffhanger:
                    embed.add_field(
                        name="🎭 Cliffhanger",
                        value=episode.cliffhanger,
                        inline=False
                    )
                
                embed.set_footer(text="Use /episode_recap to review this episode later")
                await interaction.response.send_message(embed=embed)
                
            except Exception as e:
                error_embed = discord.Embed(
                    title="❌ Episode End Failed",
                    description=f"Failed to end episode: {str(e)}",
                    color=0xFF6B6B
                )
                await interaction.response.send_message(embed=error_embed, ephemeral=True)
        
        @self.bot.tree.command(name="episode_recap", description="Get a dramatic recap of a previous episode")
        @app_commands.describe(
            episode_number="Episode number to recap (defaults to most recent)",
            style="Recap style"
        )
        @app_commands.choices(style=[
            app_commands.Choice(name="Dramatic (Full AI Narration)", value="dramatic"),
            app_commands.Choice(name="Quick Summary", value="quick"),
            app_commands.Choice(name="Character Focus", value="character"),
            app_commands.Choice(name="Story Beats", value="story")
        ])
        async def episode_recap(interaction: discord.Interaction, 
                              episode_number: Optional[int] = None,
                              style: str = "dramatic"):
            guild_id = str(interaction.guild.id)
            
            await interaction.response.defer()  # This might take a moment
            
            try:
                # Get recap data
                recap_data = EpisodeOperations.get_episode_recap_data(guild_id, episode_number)
                
                if not recap_data:
                    await interaction.followup.send("❌ No episode found to recap!", ephemeral=True)
                    return
                
                episode = recap_data['episode']
                
                # Generate recap based on style
                if style == "dramatic":
                    recap_text = await self.recap_generator.generate_dramatic_recap(recap_data)
                elif style == "character":
                    recap_text = await self.recap_generator.generate_character_focused_recap(recap_data)
                elif style == "story":
                    recap_text = await self.recap_generator.generate_story_beats_recap(recap_data)
                else:  # quick
                    recap_text = self.recap_generator.generate_quick_recap(recap_data)
                
                # Create embed
                embed = discord.Embed(
                    title=f"📺 Episode {episode.episode_number} Recap",
                    description=f"**{episode.name}**",
                    color=0x9370DB
                )
                
                # Split recap if too long for Discord
                if len(recap_text) > 1000:
                    embed.add_field(
                        name="🎭 Previously on Storm King's Thunder...",
                        value=recap_text[:1000] + "...",
                        inline=False
                    )
                    # Send continuation as separate message if needed
                    if len(recap_text) > 1000:
                        continuation = recap_text[1000:]
                        embed.add_field(
                            name="📖 Continued...",
                            value=continuation[:1000] + ("..." if len(continuation) > 1000 else ""),
                            inline=False
                        )
                else:
                    embed.add_field(
                        name="🎭 Previously on Storm King's Thunder...",
                        value=recap_text,
                        inline=False
                    )
                
                # Add episode info
                embed.add_field(
                    name="📅 Episode Info",
                    value=f"Date: {episode.start_time.strftime('%Y-%m-%d')}\nDuration: {episode.duration_hours:.1f}h",
                    inline=True
                )
                
                if episode.cliffhanger:
                    embed.add_field(
                        name="🎬 Cliffhanger",
                        value=episode.cliffhanger,
                        inline=False
                    )
                
                await interaction.followup.send(embed=embed)
                
                # Add to voice queue for dramatic delivery
                if (style == "dramatic" and 
                    guild_id in self.voice_clients and 
                    self.voice_clients[guild_id].is_connected() and 
                    self.tts_enabled.get(guild_id, False)):
                    
                    voice_recap = f"Previously, on Storm King's Thunder... {recap_text}"
                    await self.add_to_voice_queue(guild_id, voice_recap, "Episode Recap")
                
            except Exception as e:
                await interaction.followup.send(
                    f"❌ Failed to generate recap: {str(e)}", ephemeral=True
                )
        
        @self.bot.tree.command(name="episode_history", description="View episode history for this campaign")
        @app_commands.describe(limit="Number of episodes to show")
        async def episode_history(interaction: discord.Interaction, limit: int = 5):
            guild_id = str(interaction.guild.id)
            
            try:
                episodes = EpisodeOperations.get_episode_history(guild_id, limit)
                
                if not episodes:
                    await interaction.response.send_message("No episodes found for this campaign.", ephemeral=True)
                    return
                
                embed = discord.Embed(
                    title="📚 Episode History",
                    description=f"Recent {len(episodes)} episodes",
                    color=0x4B0082
                )
                
                for episode in episodes:
                    status_emoji = "✅" if episode.status == "completed" else "🔄"
                    duration_text = f"{episode.duration_hours:.1f}h" if episode.duration_hours else "In progress"
                    
                    value = f"Status: {status_emoji} {episode.status.title()}\n"
                    value += f"Duration: {duration_text}\n"
                    value += f"Date: {episode.start_time.strftime('%Y-%m-%d')}"
                    
                    if episode.summary:
                        value += f"\n📝 {episode.summary[:100]}{'...' if len(episode.summary) > 100 else ''}"
                    
                    embed.add_field(
                        name=f"Episode {episode.episode_number}: {episode.name}",
                        value=value,
                        inline=False
                    )
                
                embed.set_footer(text="Use /episode_recap [number] to get detailed recaps")
                await interaction.response.send_message(embed=embed)
                
            except Exception as e:
                await interaction.response.send_message(
                    f"❌ Failed to get episode history: {str(e)}", ephemeral=True
                )
        
        @self.bot.tree.command(name="add_story_note", description="Add a story note to the current episode")
        @app_commands.describe(
            note="Your story note or character thought",
            note_type="Type of note",
            public="Should other players see this note?"
        )
        @app_commands.choices(note_type=[
            app_commands.Choice(name="Character Thought", value="character_thought"),
            app_commands.Choice(name="Player Observation", value="player_observation"),
            app_commands.Choice(name="Theory/Speculation", value="theory"),
            app_commands.Choice(name="Question", value="question")
        ])
        async def add_story_note(interaction: discord.Interaction, 
                               note: str, 
                               note_type: str = "player_observation",
                               public: bool = True):
            guild_id = str(interaction.guild.id)
            user_id = str(interaction.user.id)
            player_name = interaction.user.display_name
            
            try:
                success = PlayerNoteOperations.add_player_note(
                    guild_id, user_id, player_name, note, note_type, public
                )
                
                if not success:
                    await interaction.response.send_message(
                        "❌ No active episode! Use `/start_episode` first.", ephemeral=True
                    )
                    return
                
                embed = discord.Embed(
                    title="📝 Story Note Added",
                    color=0x32CD32
                )
                
                note_type_names = {
                    "character_thought": "💭 Character Thought",
                    "player_observation": "👁️ Player Observation", 
                    "theory": "🤔 Theory/Speculation",
                    "question": "❓ Question"
                }
                
                embed.add_field(
                    name=note_type_names.get(note_type, "📝 Note"),
                    value=note,
                    inline=False
                )
                
                embed.add_field(
                    name="ℹ️ Note Info",
                    value=f"Type: {note_type.replace('_', ' ').title()}\nPublic: {'Yes' if public else 'No'}\nPlayer: {player_name}",
                    inline=False
                )
                
                embed.set_footer(text="Note saved to episode history • This is marked as player perspective, not canonical truth")
                
                await interaction.response.send_message(embed=embed, ephemeral=not public)
                
            except Exception as e:
                await interaction.response.send_message(
                    f"❌ Failed to add note: {str(e)}", ephemeral=True
                )
    
    async def _sync_characters_to_db(self, guild_id: str):
        """Sync characters from campaign_context to database"""
        try:
            for user_id, player_data in self.campaign_context.get("players", {}).items():
                if "character_data" in player_data:
                    CharacterOperations.sync_character_from_context(
                        guild_id, user_id, player_data["character_data"]
                    )
        except Exception as e:
            print(f"Error syncing characters to database: {e}")
    
    async def _deliver_episode_recap(self, interaction: discord.Interaction, episode_number: int):
        """Deliver episode recap after starting new episode"""
        try:
            guild_id = str(interaction.guild.id)
            recap_data = EpisodeOperations.get_episode_recap_data(guild_id, episode_number)
            
            if not recap_data:
                return
            
            recap_text = await self.recap_generator.generate_dramatic_recap(recap_data)
            
            # Send as follow-up
            recap_embed = discord.Embed(
                title=f"📺 Last Time on Storm King's Thunder...",
                description=f"**Episode {episode_number} Recap**",
                color=0x9370DB
            )
            
            recap_embed.add_field(
                name="🎭 Previously...",
                value=recap_text[:1000] + ("..." if len(recap_text) > 1000 else ""),
                inline=False
            )
            
            await asyncio.sleep(2)  # Brief pause
            await interaction.followup.send(embed=recap_embed)
            
            # Add to voice queue
            if (guild_id in self.voice_clients and 
                self.voice_clients[guild_id].is_connected() and 
                self.tts_enabled.get(guild_id, False)):
                
                voice_recap = f"Previously, on Storm King's Thunder... {recap_text}"
                await self.add_to_voice_queue(guild_id, voice_recap, "Episode Recap")
                
        except Exception as e:
            print(f"Error delivering episode recap: {e}")