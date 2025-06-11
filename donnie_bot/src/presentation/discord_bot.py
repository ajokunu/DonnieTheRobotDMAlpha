"""
Main Discord bot class - UPDATED
"""
import discord
from discord.ext import commands
import logging

from .dependency_injection import container
from .commands import (
    CharacterCommands, PartyCommands, 
    EpisodeCommands, QuickActionCommands,
    DMCommands, QuickDMCommands,
    VoiceCommands, VoiceUtilities
)
from ..infrastructure.config.settings import settings

logger = logging.getLogger(__name__)


class DonnieBot(commands.Bot):
    """Donnie the DM Discord bot"""
    
    def __init__(self):
        # Configure Discord intents
        intents = discord.Intents.default()
        intents.message_content = True
        intents.voice_states = True
        intents.guilds = True
        intents.guild_messages = True
        
        super().__init__(
            command_prefix=settings.discord.command_prefix,
            intents=intents,
            description="🎲 Donnie the DM - Your AI-powered D&D Dungeon Master!",
            help_command=None
        )
        
        self.is_ready = False
        self.dependencies_loaded = False
    
    async def setup_hook(self):
        """Called when the bot is starting up"""
        logger.info("🎲 Setting up Donnie the DM...")
        
        try:
            # Initialize dependencies
            await container.initialize()
            self.dependencies_loaded = True
            
            # Add all command groups
            await self.add_cog(CharacterCommands(self))
            await self.add_cog(PartyCommands(self))
            await self.add_cog(EpisodeCommands(self))
            await self.add_cog(QuickActionCommands(self))
            await self.add_cog(DMCommands(self))
            await self.add_cog(QuickDMCommands(self))
            await self.add_cog(VoiceCommands(self))
            await self.add_cog(VoiceUtilities(self))
            
            # Sync slash commands
            logger.info("🔄 Syncing slash commands...")
            synced = await self.tree.sync()
            logger.info(f"✅ Synced {len(synced)} commands")
            
            logger.info("🎲 Donnie the DM setup completed!")
            
        except Exception as e:
            logger.error(f"❌ Failed to setup bot: {e}")
            raise
    
    async def on_ready(self):
        """Called when the bot is ready"""
        if not self.is_ready:
            logger.info(f"🟢 {self.user} is online and ready!")
            logger.info(f"📊 Connected to {len(self.guilds)} guilds")
            
            activity = discord.Activity(
                type=discord.ActivityType.playing,
                name="D&D | /help for commands"
            )
            await self.change_presence(activity=activity)
            
            self.is_ready = True
    
    async def close(self):
        """Cleanup when bot shuts down"""
        logger.info("🔄 Shutting down Donnie the DM...")
        
        if self.dependencies_loaded:
            await container.cleanup()
        
        await super().close()


# Custom help command
class CustomHelp(commands.Cog):
    """Custom help command"""
    
    def __init__(self, bot):
        self.bot = bot
    
    @discord.app_commands.command(name="help", description="Show help information")
    async def help_command(self, interaction: discord.Interaction):
        """Show comprehensive help"""
        
        embed = discord.Embed(
            title="🎲 Donnie the DM - Command Guide",
            description="Your AI-powered D&D Dungeon Master!",
            color=0x7B68EE
        )
        
        embed.add_field(
            name="👤 Character Commands",
            value="`/character create` - Create a new character\n"
                  "`/character show` - View your character\n"
                  "`/party show` - View all party members",
            inline=False
        )
        
        embed.add_field(
            name="📖 Episode Commands", 
            value="`/episode start` - Start a new episode\n"
                  "`/episode status` - Check episode status\n"
                  "`/action` - Take an action",
            inline=False
        )
        
        embed.add_field(
            name="🎲 DM Commands",
            value="`/dm` - DM narration\n"
                  "`/roll` - Roll dice",
            inline=False
        )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)