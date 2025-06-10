"""
Episode management Discord commands
"""
import discord
from discord.ext import commands
from discord import app_commands
from typing import Optional

from ..dependency_injection import container
from ..discord_bot import handle_use_case_result, create_episode_embed
from ...application.dto import StartEpisodeCommand, EndEpisodeCommand, GetContextCommand


class EpisodeCommands(commands.Cog):
    """Episode management commands"""
    
    def __init__(self, bot):
        self.bot = bot
    
    @app_commands.command(name="episode", description="Episode management commands")
    @app_commands.describe(
        action="What to do with episodes",
        name="Episode name (for start)",
        opening_scene="Opening scene description (for start)",
        summary="Episode summary (for end)",
        closing_scene="Closing scene (for end)",
        episode_number="Episode number (for summary/history)"
    )
    @app_commands.choices(action=[
        app_commands.Choice(name="Start New Episode", value="start"),
        app_commands.Choice(name="Continue Current Episode", value="continue"),
        app_commands.Choice(name="End Current Episode", value="end"),
        app_commands.Choice(name="Episode Status", value="status"),
        app_commands.Choice(name="Episode History", value="history"),
        app_commands.Choice(name="Episode Summary", value="summary")
    ])
    async def episode(self,
                     interaction: discord.Interaction,
                     action: str,
                     name: Optional[str] = None,
                     opening_scene: Optional[str] = None,
                     summary: Optional[str] = None,
                     closing_scene: Optional[str] = None,
                     episode_number: Optional[int] = None):
        """Main episode command"""
        
        await interaction.response.defer()
        
        if not container.episode_use_case:
            await interaction.followup.send("❌ Episode system not available")
            return
        
        try:
            if action == "start":
                await self._handle_start(interaction, name, opening_scene)
            elif action == "continue":
                await self._handle_continue(interaction)
            elif action == "end":
                await self._handle_end(interaction, summary, closing_scene)
            elif action == "status":
                await self._handle_status(interaction)
            elif action == "history":
                await self._handle_history(interaction)
            elif action == "summary":
                await self._handle_summary(interaction, episode_number)
            else:
                await interaction.followup.send("❌ Unknown action")
                
        except Exception as e:
            await interaction.followup.send(f"❌ Error: {str(e)}")
    
    async def _handle_start(self, interaction, name, opening_scene):
        """Handle starting a new episode"""
        if not name:
            await interaction.followup.send(
                "❌ Episode name is required!\n"
                "Use: `/episode start name:\"The Village of Nightstone\"`"
            )
            return
        
        command = StartEpisodeCommand(
            guild_id=str(interaction.guild.id),
            episode_name=name,
            opening_scene=opening_scene or "",
            dm_user_id=str(interaction.user.id)
        )
        
        result = await container.episode_use_case.start_new_episode(command)
        
        if result.success:
            embed = create_episode_embed(result.episode)
            embed.set_author(
                name="🎬 Episode Started!",
                icon_url=interaction.user.display_avatar.url
            )
            
            # Add DM info
            embed.add_field(
                name="🎲 Dungeon Master",
                value=interaction.user.display_name,
                inline=True
            )
            
            await interaction.followup.send(embed=embed)
            
            # If there's an opening scene, also speak it if voice is enabled
            if opening_scene and container.voice_service:
                voice_connected = await container.voice_service.is_connected(str(interaction.guild.id))
                if voice_connected:
                    from ...application.dto import VoiceCommand
                    voice_command = VoiceCommand(
                        guild_id=str(interaction.guild.id),
                        action="speak",
                        text_to_speak=opening_scene
                    )
                    await container.voice_use_case.speak_text(voice_command)
        else:
            response = handle_use_case_result(result)
            await interaction.followup.send(**response)
    
    async def _handle_continue(self, interaction):
        """Handle continuing current episode"""
        result = await container.episode_use_case.continue_episode(str(interaction.guild.id))
        
        if result.success:
            embed = create_episode_embed(result.episode)
            embed.set_author(
                name="📖 Episode Continued",
                icon_url="https://i.imgur.com/book.png"
            )
            await interaction.followup.send(embed=embed)
        else:
            response = handle_use_case_result(result)
            await interaction.followup.send(**response)
    
    async def _handle_end(self, interaction, summary, closing_scene):
        """Handle ending current episode"""
        command = EndEpisodeCommand(
            guild_id=str(interaction.guild.id),
            summary=summary or "",
            closing_scene=closing_scene or "",
            dm_user_id=str(interaction.user.id)
        )
        
        result = await container.episode_use_case.end_episode(command)
        
        if result.success:
            embed = create_episode_embed(result.episode)
            embed.set_author(
                name="🏁 Episode Ended",
                icon_url=interaction.user.display_avatar.url
            )
            embed.color = 0x0000FF  # Blue for completed
            
            # Add completion stats
            stats = container.episode_use_case.episode_service.get_episode_stats(result.episode)
            embed.add_field(
                name="📈 Session Stats",
                value=f"⏰ Duration: {stats['duration_hours']:.1f} hours\n"
                      f"💬 Interactions: {stats['interaction_count']}\n"
                      f"👥 Characters: {stats['character_count']}",
                inline=False
            )
            
            await interaction.followup.send(embed=embed)
        else:
            response = handle_use_case_result(result)
            await interaction.followup.send(**response)
    
    async def _handle_status(self, interaction):
        """Show current episode status"""
        # Get current context
        context_command = GetContextCommand(
            guild_id=str(interaction.guild.id),
            include_recent_memories=True,
            memory_limit=5
        )
        
        result = await container.episode_use_case.get_current_context(context_command)
        
        if not result.success:
            response = handle_use_case_result(result)
            await interaction.followup.send(**response)
            return
        
        if not result.current_episode:
            embed = discord.Embed(
                title="📖 Episode Status",
                description="No active episode. Start one with `/episode start`!",
                color=0x808080
            )
            await interaction.followup.send(embed=embed)
            return
        
        embed = create_episode_embed(result.current_episode)
        embed.set_author(name="📊 Episode Status")
        
        # Add party info
        if result.party_members:
            party_names = [char.name for char in result.party_members]
            embed.add_field(
                name="👥 Active Party",
                value=", ".join(party_names[:5]) + (f" (+{len(party_names)-5} more)" if len(party_names) > 5 else ""),
                inline=False
            )
        
        # Add recent activity
        if result.recent_memories:
            recent_activity = []
            for memory in result.recent_memories[-3:]:
                if memory.character_name:
                    activity_line = f"**{memory.character_name}**: {memory.content[:50]}..."
                else:
                    activity_line = f"{memory.content[:50]}..."
                recent_activity.append(activity_line)
            
            if recent_activity:
                embed.add_field(
                    name="💭 Recent Activity",
                    value="\n".join(recent_activity),
                    inline=False
                )
        
        await interaction.followup.send(embed=embed)
    
    async def _handle_history(self, interaction):
        """Show episode history"""
        result = await container.episode_use_case.get_episode_history(str(interaction.guild.id), limit=10)
        
        if result.success:
            episodes = result.metadata.get("episodes", [])
            
            if not episodes:
                embed = discord.Embed(
                    title="📚 Episode History",
                    description="No episodes found in this server.",
                    color=0x808080
                )
                await interaction.followup.send(embed=embed)
                return
            
            embed = discord.Embed(
                title=f"📚 Episode History ({len(episodes)} episodes)",
                color=0x7B68EE
            )
            
            for i, episode_data in enumerate(episodes[:10]):
                status_emoji = {
                    "planned": "📝",
                    "active": "🎬", 
                    "completed": "✅",
                    "cancelled": "❌"
                }.get(episode_data.get("status", "planned"), "❓")
                
                duration = episode_data.get("duration_hours", 0)
                interactions = len(episode_data.get("interactions", []))
                
                embed.add_field(
                    name=f"{status_emoji} Episode {episode_data.get('episode_number', i+1)}",
                    value=f"**{episode_data.get('name', 'Untitled')}**\n"
                          f"⏰ {duration:.1f}h | 💬 {interactions} interactions",
                    inline=True
                )
            
            await interaction.followup.send(embed=embed)
        else:
            response = handle_use_case_result(result)
            await interaction.followup.send(**response)
    
    async def _handle_summary(self, interaction, episode_number):
        """Generate episode summary"""
        if not container.ai_service:
            await interaction.followup.send("❌ Episode summaries require AI service (missing API key)")
            return
        
        await interaction.followup.send("📝 Generating episode summary... This may take a moment!")
        
        result = await container.episode_use_case.get_episode_summary(
            str(interaction.guild.id),
            episode_number
        )
        
        if result.success:
            embed = discord.Embed(
                title=f"📝 Episode Summary",
                description=result.message,
                color=0x7B68EE
            )
            
            if result.episode:
                embed.set_footer(text=f"Episode {result.episode.episode_number}: {result.episode.name}")
            
            await interaction.edit_original_response(content=None, embed=embed)
        else:
            response = handle_use_case_result(result)
            await interaction.edit_original_response(**response)


class QuickActionCommands(commands.Cog):
    """Quick action commands for faster gameplay"""
    
    def __init__(self, bot):
        self.bot = bot
    
    @app_commands.command(name="action", description="Take an action in the current episode")
    @app_commands.describe(
        action="What your character does",
        action_type="Type of action (optional)"
    )
    @app_commands.choices(action_type=[
        app_commands.Choice(name="General Action", value="general"),
        app_commands.Choice(name="Combat Action", value="combat"),
        app_commands.Choice(name="Exploration", value="exploration"),
        app_commands.Choice(name="Social Interaction", value="social"),
        app_commands.Choice(name="Magic/Spell", value="magic")
    ])
    async def action(self,
                    interaction: discord.Interaction,
                    action: str,
                    action_type: Optional[str] = "general"):
        """Take an action in the story"""
        
        await interaction.response.defer()
        
        if not container.action_use_case:
            await interaction.followup.send("❌ Action system not available")
            return
        
        if not container.ai_service:
            await interaction.followup.send("❌ Actions require AI service (missing API key)")
            return
        
        from ...application.dto import PlayerActionCommand
        
        command = PlayerActionCommand(
            guild_id=str(interaction.guild.id),
            discord_user_id=str(interaction.user.id),
            action_text=action,
            action_type=action_type
        )
        
        try:
            # Show that we're processing
            await interaction.followup.send(f"🎲 {interaction.user.display_name} attempts: *{action}*\n\n⚡ Processing...")
            
            result = await container.action_use_case.handle_player_action(command)
            
            if result.success and result.dm_response:
                # Create response embed
                embed = discord.Embed(
                    title=f"🎲 Action Result",
                    description=result.dm_response.text,
                    color=0x00FF00
                )
                
                embed.set_author(
                    name=f"{interaction.user.display_name}",
                    icon_url=interaction.user.display_avatar.url
                )
                
                # Add action context
                embed.add_field(
                    name="⚔️ Action Taken",
                    value=action,
                    inline=False
                )
                
                # If it's combat, add special formatting
                if action_type == "combat":
                    embed.color = 0xFF0000
                    embed.title = "⚔️ Combat Action Result"
                
                await interaction.edit_original_response(content=None, embed=embed)
                
                # Try to speak the response if voice is connected
                if container.voice_service:
                    voice_connected = await container.voice_service.is_connected(str(interaction.guild.id))
                    if voice_connected:
                        from ...application.dto import VoiceCommand
                        voice_command = VoiceCommand(
                            guild_id=str(interaction.guild.id),
                            action="speak",
                            text_to_speak=result.dm_response.text
                        )
                        try:
                            await container.voice_use_case.speak_text(voice_command)
                        except:
                            pass  # Don't fail the action if voice fails
            else:
                response = handle_use_case_result(result)
                await interaction.edit_original_response(**response)
                
        except Exception as e:
            await interaction.edit_original_response(content=f"❌ Error processing action: {str(e)}")
    
    @app_commands.command(name="combat", description="Perform a combat action with D&D mechanics")
    @app_commands.describe(
        action_type="Type of combat action",
        target="Target of the action (optional)",
        details="Additional details about the action"
    )
    @app_commands.choices(action_type=[
        app_commands.Choice(name="Attack", value="attack"),
        app_commands.Choice(name="Cast Spell", value="spell"),
        app_commands.Choice(name="Dodge", value="dodge"),
        app_commands.Choice(name="Dash", value="dash"),
        app_commands.Choice(name="Help", value="help"),
        app_commands.Choice(name="Hide", value="hide"),
        app_commands.Choice(name="Search", value="search"),
        app_commands.Choice(name="Use Item", value="item")
    ])
    async def combat_action(self,
                           interaction: discord.Interaction,
                           action_type: str,
                           target: Optional[str] = None,
                           details: Optional[str] = None):
        """Perform a combat action with D&D mechanics"""
        
        await interaction.response.defer()
        
        if not container.action_use_case:
            await interaction.followup.send("❌ Combat system not available")
            return
        
        from ...application.dto import CombatActionCommand
        
        command = CombatActionCommand(
            guild_id=str(interaction.guild.id),
            discord_user_id=str(interaction.user.id),
            action_type=action_type,
            target=target,
            details=details or ""
        )
        
        try:
            # Show combat action
            action_text = f"{action_type}"
            if target:
                action_text += f" against {target}"
            if details:
                action_text += f" ({details})"
            
            await interaction.followup.send(f"⚔️ {interaction.user.display_name} attempts: *{action_text}*\n\n🎲 Rolling dice...")
            
            result = await container.action_use_case.handle_combat_action(command)
            
            if result.success:
                embed = discord.Embed(
                    title="⚔️ Combat Result",
                    description=result.narrative,
                    color=0xFF0000
                )
                
                embed.set_author(
                    name=f"{interaction.user.display_name}",
                    icon_url=interaction.user.display_avatar.url
                )
                
                # Add combat details
                if result.combat_outcome:
                    outcome = result.combat_outcome
                    details_text = f"**Action:** {outcome.get('action', 'Unknown')}"
                    
                    if outcome.get('target'):
                        details_text += f"\n**Target:** {outcome['target']}"
                    
                    if outcome.get('roll_result'):
                        roll_data = outcome['roll_result']
                        if isinstance(roll_data, dict):
                            details_text += f"\n**Roll:** {roll_data.get('attack_roll', 'N/A')}"
                            if roll_data.get('damage_roll'):
                                details_text += f"\n**Damage:** {roll_data['damage_roll']}"
                            if roll_data.get('is_critical'):
                                details_text += "\n**🎯 Critical Hit!**"
                    
                    if outcome.get('effects'):
                        effects = outcome['effects']
                        if effects:
                            details_text += f"\n**Effects:** {', '.join(effects)}"
                    
                    embed.add_field(
                        name="🎲 Combat Details",
                        value=details_text,
                        inline=False
                    )
                
                await interaction.edit_original_response(content=None, embed=embed)
            else:
                response = handle_use_case_result(result)
                await interaction.edit_original_response(**response)
                
        except Exception as e:
            await interaction.edit_original_response(content=f"❌ Error processing combat: {str(e)}")