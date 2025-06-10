"""
Discord event handlers for messages and interactions
"""
import discord
from discord.ext import commands
import logging
import re
from typing import Optional

from ..dependency_injection import container
from ...application.dto import PlayerActionCommand, VoiceCommand

logger = logging.getLogger(__name__)


class MessageHandlers:
    """Discord message and event handlers"""
    
    def __init__(self, bot):
        self.bot = bot
        self.setup_event_handlers()
    
    def setup_event_handlers(self):
        """Setup all event handlers"""
        
        @self.bot.event
        async def on_message(message):
            """Handle regular messages"""
            await self.handle_message(message)
        
        @self.bot.event
        async def on_message_edit(before, after):
            """Handle message edits"""
            # Don't process edited messages to avoid confusion
            pass
        
        @self.bot.event
        async def on_reaction_add(reaction, user):
            """Handle reaction additions"""
            await self.handle_reaction_add(reaction, user)
    
    async def handle_message(self, message: discord.Message):
        """Handle incoming messages"""
        
        # Ignore bot messages
        if message.author.bot:
            return
        
        # Process commands first
        await self.bot.process_commands(message)
        
        # Check for natural language actions
        if message.guild and not message.content.startswith(('/', '!', '?')):
            await self.handle_natural_action(message)
    
    async def handle_natural_action(self, message: discord.Message):
        """Handle natural language actions in specific channels"""
        
        # Only process in channels named like: rp, roleplay, campaign, episode, game, dnd
        channel_keywords = ['rp', 'roleplay', 'campaign', 'episode', 'game', 'dnd', 'adventure']
        channel_name = message.channel.name.lower()
        
        if not any(keyword in channel_name for keyword in channel_keywords):
            return
        
        # Check if there's an active episode
        if not container.episode_use_case:
            return
        
        current_episode = await container.episode_use_case.episode_service.get_current_episode(str(message.guild.id))
        if not current_episode or not current_episode.is_active():
            return
        
        # Check if user has a character
        if not container.character_use_case:
            return
        
        character_result = await container.character_use_case.get_character(
            str(message.author.id),
            str(message.guild.id)
        )
        
        if not character_result.success:
            return
        
        # Detect action patterns
        action_patterns = [
            r"^I (try to|attempt to|want to|will|am going to|decide to)\s+(.+)",
            r"^(My character|[A-Za-z]+) (tries to|attempts to|wants to|will|goes to|decides to)\s+(.+)",
            r"^(Looking|Searching|Moving|Going|Walking|Running|Climbing|Swimming|Flying)\s+(.+)",
            r"^(Attack|Cast|Use|Drink|Eat|Take|Pick up|Grab|Open|Close|Push|Pull)\s+(.+)"
        ]
        
        action_text = None
        for pattern in action_patterns:
            match = re.match(pattern, message.content, re.IGNORECASE)
            if match:
                if "I " in pattern:
                    action_text = match.group(2)
                else:
                    action_text = match.group(3) if len(match.groups()) >= 3 else match.group(2)
                break
        
        # If no pattern matched, check for quoted actions
        if not action_text:
            quote_pattern = r'^"([^"]+)"'
            match = re.match(quote_pattern, message.content)
            if match:
                action_text = match.group(1)
        
        # If still no action, check for roleplay indicators
        if not action_text and len(message.content) > 10:
            rp_indicators = ['*', '**', '_', '__', '>', '|', '~']
            if any(indicator in message.content for indicator in rp_indicators):
                # This looks like roleplay text, treat as action
                action_text = message.content.strip('*_~>| ')
        
        if not action_text:
            return
        
        # Don't process very short actions
        if len(action_text.strip()) < 3:
            return
        
        # Don't process OOC (out of character) messages
        ooc_patterns = [r'\(\(.*\)\)', r'\[.*\]', r'ooc:', r'//']
        if any(re.search(pattern, message.content, re.IGNORECASE) for pattern in ooc_patterns):
            return
        
        logger.info(f"Processing natural action from {message.author.display_name}: {action_text[:50]}...")
        
        try:
            # Add thinking reaction
            await message.add_reaction('🤔')
            
            # Process the action
            if container.action_use_case and container.ai_service:
                command = PlayerActionCommand(
                    guild_id=str(message.guild.id),
                    discord_user_id=str(message.author.id),
                    action_text=action_text,
                    action_type="natural"
                )
                
                result = await container.action_use_case.handle_player_action(command)
                
                # Remove thinking reaction
                await message.remove_reaction('🤔', self.bot.user)
                
                if result.success and result.dm_response:
                    # Create response
                    response_text = result.dm_response.text
                    
                    # Add success reaction
                    await message.add_reaction('✅')
                    
                    # Send response as reply
                    embed = discord.Embed(
                        description=response_text,
                        color=0x7B68EE
                    )
                    
                    embed.set_author(
                        name=f"DM Response to {message.author.display_name}",
                        icon_url="https://i.imgur.com/dice.png"
                    )
                    
                    # Reference the original message
                    embed.add_field(
                        name="💭 Action",
                        value=f"*{action_text}*",
                        inline=False
                    )
                    
                    response_message = await message.reply(embed=embed, mention_author=False)
                    
                    # Try to speak response if voice is connected
                    if container.voice_service:
                        voice_connected = await container.voice_service.is_connected(str(message.guild.id))
                        if voice_connected:
                            voice_command = VoiceCommand(
                                guild_id=str(message.guild.id),
                                action="speak",
                                text_to_speak=response_text
                            )
                            try:
                                await container.voice_use_case.speak_text(voice_command)
                            except:
                                pass  # Don't fail if voice fails
                else:
                    # Add error reaction
                    await message.add_reaction('❌')
            else:
                # Add confused reaction if AI not available
                await message.remove_reaction('🤔', self.bot.user)
                await message.add_reaction('❓')
                
        except discord.Forbidden:
            # Bot doesn't have permission to add reactions
            pass
        except Exception as e:
            logger.error(f"Error processing natural action: {e}")
            try:
                await message.remove_reaction('🤔', self.bot.user)
                await message.add_reaction('❌')
            except:
                pass
    
    async def handle_reaction_add(self, reaction: discord.Reaction, user: discord.User):
        """Handle reaction additions for special functionality"""
        
        # Ignore bot reactions
        if user.bot:
            return
        
        # Handle dice roll reactions
        if str(reaction.emoji) == '🎲':
            await self.handle_dice_reaction(reaction, user)
        
        # Handle help reactions
        elif str(reaction.emoji) == '❓':
            await self.handle_help_reaction(reaction, user)
    
    async def handle_dice_reaction(self, reaction: discord.Reaction, user: discord.User):
        """Handle dice roll reactions"""
        
        # Only allow in DM/RP channels or by DMs
        channel_keywords = ['rp', 'roleplay', 'campaign', 'episode', 'game', 'dnd', 'dm']
        channel_name = reaction.message.channel.name.lower()
        
        if not any(keyword in channel_name for keyword in channel_keywords):
            return
        
        # Check if user is DM or has permissions
        if not user.guild_permissions.administrator:
            dm_role_names = ["DM", "Dungeon Master", "Game Master", "GM"]
            user_roles = [role.name for role in user.roles] if hasattr(user, 'roles') else []
            
            if not any(role in dm_role_names for role in user_roles):
                return
        
        try:
            # Quick d20 roll
            if container.combat_service:
                roll = container.combat_service.roll_d20()
                
                embed = discord.Embed(
                    title="🎲 Quick Roll",
                    description=f"**{roll}**",
                    color=0x00FF00 if roll >= 15 else 0xFF0000 if roll <= 5 else 0x7B68EE
                )
                
                if roll == 20:
                    embed.add_field(name="🎯", value="**Critical Success!**", inline=False)
                elif roll == 1:
                    embed.add_field(name="💥", value="**Critical Fumble!**", inline=False)
                
                embed.set_footer(text=f"Rolled by {user.display_name}")
                
                await reaction.message.reply(embed=embed, delete_after=30)
        
        except Exception as e:
            logger.error(f"Error handling dice reaction: {e}")
    
    async def handle_help_reaction(self, reaction: discord.Reaction, user: discord.User):
        """Handle help reactions"""
        
        try:
            # Send quick help as ephemeral message
            embed = discord.Embed(
                title="🎲 Quick Help",
                description="**Donnie the DM Commands**",
                color=0x7B68EE
            )
            
            embed.add_field(
                name="🚀 Quick Start",
                value="`/character create` - Make your character\n"
                      "`/episode start` - Begin adventure\n"
                      "`/action` - Take an action",
                inline=False
            )
            
            embed.add_field(
                name="💡 Natural Actions",
                value="In RP channels, just type what your character does!\n"
                      "*Example: \"I search the room for clues\"*",
                inline=False
            )
            
            embed.add_field(
                name="📚 Full Help",
                value="Use `/help` for complete command list",
                inline=False
            )
            
            # Send as DM to avoid channel spam
            try:
                await user.send(embed=embed)
                # React to acknowledge
                await reaction.message.add_reaction('📨')
            except discord.Forbidden:
                # Can't DM user, so reply in channel briefly
                await reaction.message.reply(embed=embed, delete_after=60)
        
        except Exception as e:
            logger.error(f"Error handling help reaction: {e}")


class ErrorHandler:
    """Error handling for Discord events"""
    
    def __init__(self, bot):
        self.bot = bot
        self.setup_error_handlers()
    
    def setup_error_handlers(self):
        """Setup error event handlers"""
        
        @self.bot.event
        async def on_app_command_error(interaction: discord.Interaction, error: discord.app_commands.AppCommandError):
            """Handle application command errors"""
            await self.handle_app_command_error(interaction, error)
    
    async def handle_app_command_error(self, interaction: discord.Interaction, error: discord.app_commands.AppCommandError):
        """Handle application command errors"""
        
        error_message = "❌ Something went wrong."
        
        if isinstance(error, discord.app_commands.CommandOnCooldown):
            error_message = f"⏰ Command is on cooldown. Try again in {error.retry_after:.1f} seconds."
        
        elif isinstance(error, discord.app_commands.MissingPermissions):
            error_message = "❌ You don't have permission to use this command."
        
        elif isinstance(error, discord.app_commands.BotMissingPermissions):
            error_message = "❌ I don't have the required permissions to do that."
        
        elif isinstance(error, discord.app_commands.CheckFailure):
            error_message = "❌ You don't have permission to use this command."
        
        elif isinstance(error, discord.app_commands.CommandNotFound):
            error_message = "❌ Command not found."
        
        else:
            # Log unexpected errors
            logger.error(f"Unexpected app command error: {error}", exc_info=True)
            error_message = f"❌ An unexpected error occurred: {str(error)}"
        
        try:
            if interaction.response.is_done():
                await interaction.followup.send(error_message, ephemeral=True)
            else:
                await interaction.response.send_message(error_message, ephemeral=True)
        except:
            # If we can't respond, log it
            logger.error(f"Failed to send error message to user: {error_message}")


# Auto-moderation for gaming channels
class GameChannelModerator:
    """Moderate gaming channels for better RP experience"""
    
    def __init__(self, bot):
        self.bot = bot
        self.setup_moderation()
    
    def setup_moderation(self):
        """Setup moderation handlers"""
        
        @self.bot.event
        async def on_message(message):
            """Moderate messages in RP channels"""
            await self.moderate_rp_channel(message)
    
    async def moderate_rp_channel(self, message: discord.Message):
        """Moderate roleplay channels"""
        
        # Skip bot messages
        if message.author.bot:
            return
        
        # Check if this is an RP channel
        rp_keywords = ['rp', 'roleplay', 'campaign', 'episode', 'game', 'dnd', 'adventure', 'ic']
        channel_name = message.channel.name.lower()
        
        if not any(keyword in channel_name for keyword in rp_keywords):
            return
        
        # Check for spam (same message repeated)
        if len(message.content) > 0:
            # Get recent messages from same user
            recent_messages = []
            async for msg in message.channel.history(limit=5, before=message):
                if msg.author == message.author:
                    recent_messages.append(msg.content)
                if len(recent_messages) >= 3:
                    break
            
            # Check for repetition
            if recent_messages and all(content == message.content for content in recent_messages):
                try:
                    await message.delete()
                    warning = await message.channel.send(
                        f"⚠️ {message.author.mention}, please avoid repeating the same message in RP channels.",
                        delete_after=10
                    )
                except discord.Forbidden:
                    pass  # Bot doesn't have delete permissions
        
        # Auto-react to good RP
        rp_quality_indicators = [
            '"',  # Dialogue
            '*',  # Action descriptions  
            'rolls',  # Dice references
            'attempts to',  # Action attempts
            'tries to',
            'looks around',
            'searches',
            'says',
            'whispers',
            'shouts'
        ]
        
        if any(indicator in message.content.lower() for indicator in rp_quality_indicators):
            try:
                # Random chance to react positively
                import random
                if random.random() < 0.3:  # 30% chance
                    reactions = ['👍', '🎭', '⚔️', '🎲', '✨']
                    await message.add_reaction(random.choice(reactions))
            except:
                pass  # Don't fail if can't react