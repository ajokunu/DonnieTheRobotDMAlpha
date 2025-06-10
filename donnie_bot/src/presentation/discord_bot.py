"""
Main Discord bot class
"""
import discord
from discord.ext import commands
import logging
from typing import Optional

from .dependency_injection import container
from .commands import CharacterCommands, EpisodeCommands, DMCommands, VoiceCommands
from .events import MessageHandlers
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
            help_command=None  # We'll create a custom help command
        )
        
        # Track initialization status
        self.is_ready = False
        self.dependencies_loaded = False
    
    async def setup_hook(self):
        """Called when the bot is starting up"""
        logger.info("🎲 Setting up Donnie the DM...")
        
        try:
            # Initialize dependencies
            await container.initialize()
            self.dependencies_loaded = True
            
            # Register voice service with Discord bot
            if container.voice_service:
                # The voice service needs access to the bot for actual voice connections
                container.voice_service.bot = self
            
            # Add command groups
            await self.add_cog(CharacterCommands(self))
            await self.add_cog(EpisodeCommands(self))
            await self.add_cog(DMCommands(self))
            await self.add_cog(VoiceCommands(self))
            
            # Add event handlers
            message_handlers = MessageHandlers(self)
            
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
            logger.info(f"👥 Serving {len(set(member for guild in self.guilds for member in guild.members))} users")
            
            # Set bot status
            activity = discord.Activity(
                type=discord.ActivityType.playing,
                name="D&D | /help for commands"
            )
            await self.change_presence(activity=activity)
            
            self.is_ready = True
    
    async def on_guild_join(self, guild):
        """Called when bot joins a new guild"""
        logger.info(f"📥 Joined new guild: {guild.name} (ID: {guild.id})")
        
        # Send welcome message to system channel or first text channel
        welcome_channel = guild.system_channel
        if not welcome_channel:
            # Find first text channel bot can send to
            for channel in guild.text_channels:
                if channel.permissions_for(guild.me).send_messages:
                    welcome_channel = channel
                    break
        
        if welcome_channel:
            embed = discord.Embed(
                title="🎲 Welcome to Donnie the DM!",
                description="I'm your AI-powered D&D Dungeon Master!",
                color=0x7B68EE
            )
            embed.add_field(
                name="🚀 Getting Started",
                value="• Use `/character create` to make your first character\n"
                      "• Use `/episode start` to begin your adventure\n"
                      "• Use `/help` to see all available commands",
                inline=False
            )
            embed.add_field(
                name="🎯 Features",
                value="• AI-powered story generation\n"
                      "• D&D combat mechanics\n"
                      "• Character management\n"
                      "• Voice narration (optional)",
                inline=False
            )
            embed.set_footer(text="Happy adventuring! 🗡️⚔️🛡️")
            
            try:
                await welcome_channel.send(embed=embed)
            except discord.Forbidden:
                logger.warning(f"Cannot send welcome message to {guild.name} - no permissions")
    
    async def on_guild_remove(self, guild):
        """Called when bot leaves a guild"""
        logger.info(f"📤 Left guild: {guild.name} (ID: {guild.id})")
    
    async def on_voice_state_update(self, member, before, after):
        """Handle voice state changes for voice service integration"""
        if member == self.user:
            # Bot's voice state changed
            if before.channel and not after.channel:
                # Bot was disconnected from voice
                if container.voice_service and hasattr(container.voice_service, 'unregister_voice_client'):
                    container.voice_service.unregister_voice_client(str(member.guild.id))
                logger.info(f"🔇 Disconnected from voice in {member.guild.name}")
    
    async def on_error(self, event, *args, **kwargs):
        """Handle general bot errors"""
        logger.error(f"❌ Bot error in event {event}", exc_info=True)
    
    async def on_command_error(self, ctx, error):
        """Handle command errors"""
        if isinstance(error, commands.CommandNotFound):
            return  # Ignore unknown commands
        
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("❌ You don't have permission to use this command.")
            return
        
        if isinstance(error, commands.BotMissingPermissions):
            await ctx.send("❌ I don't have the required permissions to do that.")
            return
        
        if isinstance(error, commands.CommandOnCooldown):
            await ctx.send(f"⏰ Command is on cooldown. Try again in {error.retry_after:.1f} seconds.")
            return
        
        logger.error(f"❌ Command error: {error}", exc_info=True)
        await ctx.send("❌ Something went wrong processing that command.")
    
    async def close(self):
        """Cleanup when bot shuts down"""
        logger.info("🔄 Shutting down Donnie the DM...")
        
        # Cleanup dependencies
        if self.dependencies_loaded:
            await container.cleanup()
        
        await super().close()
        logger.info("👋 Donnie the DM has shut down")


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
        
        # Character commands
        embed.add_field(
            name="👤 Character Commands",
            value="`/character create` - Create a new character\n"
                  "`/character show` - View your character\n"
                  "`/character levelup` - Level up your character\n"
                  "`/character heal` - Heal your character\n"
                  "`/character delete` - Delete your character",
            inline=False
        )
        
        # Episode commands
        embed.add_field(
            name="📖 Episode Commands",
            value="`/episode start` - Start a new episode\n"
                  "`/episode continue` - Continue current episode\n"
                  "`/episode end` - End current episode\n"
                  "`/episode status` - Check episode status\n"
                  "`/episode history` - View episode history",
            inline=False
        )
        
        # Action commands
        embed.add_field(
            name="⚔️ Action Commands",
            value="`/action` - Take an action in the story\n"
                  "`/combat` - Perform a combat action\n"
                  "`/dm narrate` - DM narration (DM only)",
            inline=False
        )
        
        # Voice commands
        embed.add_field(
            name="🔊 Voice Commands",
            value="`/voice join` - Join your voice channel\n"
                  "`/voice leave` - Leave voice channel\n"
                  "`/voice speak` - Speak text aloud\n"
                  "`/voice status` - Check voice status",
            inline=False
        )
        
        # Party commands
        embed.add_field(
            name="👥 Party Commands",
            value="`/party show` - View all party members\n"
                  "`/party health` - Party health summary",
            inline=False
        )
        
        embed.set_footer(text="Use slash commands (/) to interact with Donnie!")
        
        await interaction.response.send_message(embed=embed, ephemeral=True)


# Error handling utilities
def handle_use_case_result(result, success_message: str = None):
    """Convert use case result to Discord response"""
    if result.success:
        return {
            "content": success_message or result.message,
            "embed": None
        }
    else:
        error_embed = discord.Embed(
            title="❌ Error",
            description=result.error,
            color=0xFF0000
        )
        return {
            "content": None,
            "embed": error_embed
        }


def create_character_embed(character) -> discord.Embed:
    """Create a Discord embed for a character"""
    embed = discord.Embed(
        title=f"👤 {character.name}",
        description=f"Level {character.level} {character.race.value} {character.character_class.value}",
        color=0x00FF00 if character.is_alive() else 0xFF0000
    )
    
    # Basic stats
    embed.add_field(
        name="💚 Health",
        value=f"{character.current_hp}/{character.max_hp} HP\n*{character.get_health_status()}*",
        inline=True
    )
    
    embed.add_field(
        name="⚡ Initiative",
        value=f"+{character.get_initiative_modifier()}",
        inline=True
    )
    
    embed.add_field(
        name="🎭 Background",
        value=character.background[:100] + "..." if len(character.background) > 100 else character.background or "None",
        inline=False
    )
    
    # Ability scores
    abilities = []
    for ability in ["strength", "dexterity", "constitution", "intelligence", "wisdom", "charisma"]:
        score = getattr(character.ability_scores, ability)
        modifier = character.ability_scores.get_modifier(ability)
        sign = "+" if modifier >= 0 else ""
        abilities.append(f"**{ability.title()}:** {score} ({sign}{modifier})")
    
    embed.add_field(
        name="📊 Ability Scores",
        value="\n".join(abilities),
        inline=False
    )
    
    # Equipment
    if character.equipment:
        equipment_text = ", ".join(character.equipment[:5])
        if len(character.equipment) > 5:
            equipment_text += f" *(and {len(character.equipment) - 5} more)*"
        embed.add_field(
            name="🎒 Equipment",
            value=equipment_text,
            inline=False
        )
    
    embed.set_footer(text=f"Player: {character.player_name}")
    
    return embed


def create_episode_embed(episode) -> discord.Embed:
    """Create a Discord embed for an episode"""
    status_colors = {
        "planned": 0xFFFF00,
        "active": 0x00FF00, 
        "completed": 0x0000FF,
        "cancelled": 0xFF0000
    }
    
    embed = discord.Embed(
        title=f"📖 Episode {episode.episode_number}: {episode.name}",
        description=episode.opening_scene[:200] + "..." if len(episode.opening_scene) > 200 else episode.opening_scene,
        color=status_colors.get(episode.status.value, 0x808080)
    )
    
    # Status and stats
    embed.add_field(
        name="📊 Status",
        value=f"**{episode.status.value.title()}**\n"
              f"Duration: {episode.get_duration_hours():.1f} hours\n"
              f"Interactions: {episode.get_interaction_count()}",
        inline=True
    )
    
    embed.add_field(
        name="👥 Characters",
        value=f"{episode.get_character_count()} active",
        inline=True
    )
    
    # Recent interaction
    if episode.interactions:
        recent = episode.interactions[-1]
        embed.add_field(
            name="💬 Latest",
            value=f"**{recent.character_name}:** {recent.player_action[:100]}..." if len(recent.player_action) > 100 else recent.player_action,
            inline=False
        )
    
    return embed