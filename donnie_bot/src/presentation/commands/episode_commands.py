"""
Episode management Discord commands
"""
import discord
from discord.ext import commands
from discord import app_commands
from typing import Optional

from ..dependency_injection import container
from ..utils import handle_use_case_result, create_episode_embed
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
            await interaction.followup.send(embed=embed)
        else:
            response = handle_use_case_result(result)
            await interaction.followup.send(**response)
    
    async def _handle_continue(self, interaction):
        """Handle continuing current episode"""
        result = await container.episode_use_case.continue_episode(str(interaction.guild.id))
        
        if result.success:
            embed = create_episode_embed(result.episode)
            embed.set_author(name="📖 Episode Continued")
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
            embed.set_author(name="🏁 Episode Ended")
            await interaction.followup.send(embed=embed)
        else:
            response = handle_use_case_result(result)
            await interaction.followup.send(**response)
    
    async def _handle_status(self, interaction):
        """Show current episode status"""
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
        await interaction.followup.send(embed=embed)
    
    async def _handle_history(self, interaction):
        """Show episode history"""
        result = await container.episode_use_case.get_episode_history(str(interaction.guild.id), limit=10)
        
        if result.success:
            await interaction.followup.send("📚 Episode history feature coming soon!")
        else:
            response = handle_use_case_result(result)
            await interaction.followup.send(**response)
    
    async def _handle_summary(self, interaction, episode_number):
        """Generate episode summary"""
        await interaction.followup.send("📝 Episode summary feature coming soon!")


class QuickActionCommands(commands.Cog):
    """Quick action commands for faster gameplay"""
    
    def __init__(self, bot):
        self.bot = bot
    
    @app_commands.command(name="action", description="Take an action in the current episode")
    @app_commands.describe(action="What your character does")
    async def action(self, interaction: discord.Interaction, action: str):
        """Take an action in the story"""
        
        await interaction.response.defer()
        
        if not container.action_use_case:
            await interaction.followup.send("❌ Action system not available")
            return
        
        if not container.ai_service:
            await interaction.followup.send("❌ Actions require AI service (missing API key)")
            return
        
        await interaction.followup.send(f"🎲 {interaction.user.display_name} attempts: *{action}*\n\n⚡ Processing...")
        
        # For now, just acknowledge the action
        embed = discord.Embed(
            title="🎲 Action Received",
            description=f"Action processing will be implemented soon!\n\nYour action: *{action}*",
            color=0x7B68EE
        )
        
        await interaction.edit_original_response(content=None, embed=embed)