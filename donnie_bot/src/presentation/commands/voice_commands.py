"""
Voice and audio Discord commands
"""
import discord
from discord.ext import commands
from discord import app_commands
from typing import Optional

from ..dependency_injection import container
from ..discord_bot import handle_use_case_result
from ...application.dto import VoiceCommand
from ...domain.interfaces.voice_service import VoiceConfig


class VoiceCommands(commands.Cog):
    """Voice and audio commands"""
    
    def __init__(self, bot):
        self.bot = bot
    
    @app_commands.command(name="voice", description="Voice and audio commands")
    @app_commands.describe(
        action="Voice action to perform",
        text="Text to speak (for speak action)",
        voice_id="Voice to use (for speak action)",
        speed="Speech speed multiplier (0.5-2.0)"
    )
    @app_commands.choices(action=[
        app_commands.Choice(name="Join Voice Channel", value="join"),
        app_commands.Choice(name="Leave Voice Channel", value="leave"),
        app_commands.Choice(name="Speak Text", value="speak"),
        app_commands.Choice(name="Voice Status", value="status"),
        app_commands.Choice(name="List Voices", value="voices"),
        app_commands.Choice(name="Voice Settings", value="settings")
    ])
    async def voice(self,
                   interaction: discord.Interaction,
                   action: str,
                   text: Optional[str] = None,
                   voice_id: Optional[str] = None,
                   speed: Optional[float] = None):
        """Main voice command"""
        
        await interaction.response.defer()
        
        if not container.voice_use_case:
            await interaction.followup.send("❌ Voice system not available")
            return
        
        try:
            if action == "join":
                await self._handle_join(interaction)
            elif action == "leave":
                await self._handle_leave(interaction)
            elif action == "speak":
                await self._handle_speak(interaction, text, voice_id, speed)
            elif action == "status":
                await self._handle_status(interaction)
            elif action == "voices":
                await self._handle_list_voices(interaction)
            elif action == "settings":
                await self._handle_settings(interaction, voice_id, speed)
            else:
                await interaction.followup.send("❌ Unknown voice action")
                
        except Exception as e:
            await interaction.followup.send(f"❌ Error: {str(e)}")
    
    async def _handle_join(self, interaction):
        """Handle joining voice channel"""
        # Check if user is in a voice channel
        if not interaction.user.voice or not interaction.user.voice.channel:
            await interaction.followup.send("❌ You need to be in a voice channel first!")
            return
        
        user_channel = interaction.user.voice.channel
        
        # Check bot permissions
        bot_member = interaction.guild.get_member(self.bot.user.id)
        if not user_channel.permissions_for(bot_member).connect:
            await interaction.followup.send("❌ I don't have permission to join that voice channel!")
            return
        
        try:
            # Connect to voice channel
            voice_client = await user_channel.connect()
            
            # Register with voice service
            if container.voice_service and hasattr(container.voice_service, 'register_voice_client'):
                container.voice_service.register_voice_client(str(interaction.guild.id), voice_client)
            
            embed = discord.Embed(
                title="🔊 Voice Connected",
                description=f"Joined **{user_channel.name}**\n\nReady for audio responses!",
                color=0x00FF00
            )
            
            embed.add_field(
                name="💡 Tip",
                value="Use `/voice speak` to test TTS or actions will automatically be spoken!",
                inline=False
            )
            
            await interaction.followup.send(embed=embed)
            
        except discord.ClientException as e:
            if "already connected" in str(e):
                await interaction.followup.send("🔊 Already connected to a voice channel!")
            else:
                await interaction.followup.send(f"❌ Failed to connect to voice: {str(e)}")
        except Exception as e:
            await interaction.followup.send(f"❌ Error joining voice: {str(e)}")
    
    async def _handle_leave(self, interaction):
        """Handle leaving voice channel"""
        command = VoiceCommand(
            guild_id=str(interaction.guild.id),
            action="leave"
        )
        
        # Also disconnect Discord voice client
        voice_client = interaction.guild.voice_client
        if voice_client:
            await voice_client.disconnect()
            
            # Unregister from voice service
            if container.voice_service and hasattr(container.voice_service, 'unregister_voice_client'):
                container.voice_service.unregister_voice_client(str(interaction.guild.id))
        
        result = await container.voice_use_case.leave_voice_channel(command)
        
        if result.success:
            embed = discord.Embed(
                title="🔇 Voice Disconnected",
                description="Left voice channel",
                color=0x808080
            )
            await interaction.followup.send(embed=embed)
        else:
            response = handle_use_case_result(result)
            await interaction.followup.send(**response)
    
    async def _handle_speak(self, interaction, text, voice_id, speed):
        """Handle text-to-speech"""
        if not text:
            await interaction.followup.send(
                "❌ Please provide text to speak!\n"
                "Use: `/voice speak text:\"Hello adventurers!\"`"
            )
            return
        
        # Check if connected to voice
        voice_client = interaction.guild.voice_client
        if not voice_client or not voice_client.is_connected():
            await interaction.followup.send(
                "❌ Not connected to voice channel!\n"
                "Use `/voice join` first."
            )
            return
        
        # Create voice config
        voice_config = VoiceConfig(
            voice_id=voice_id or "default",
            speed=speed or 1.25
        )
        
        command = VoiceCommand(
            guild_id=str(interaction.guild.id),
            action="speak",
            text_to_speak=text,
            voice_config=voice_config
        )
        
        await interaction.followup.send(f"🗣️ Speaking: *{text[:100]}{'...' if len(text) > 100 else ''}*")
        
        result = await container.voice_use_case.speak_text(command)
        
        if result.success:
            embed = discord.Embed(
                title="🗣️ Text Spoken",
                description=f"Successfully spoke: *{text[:200]}{'...' if len(text) > 200 else ''}*",
                color=0x00FF00
            )
            
            if voice_config.voice_id != "default":
                embed.add_field(name="🎭 Voice", value=voice_config.voice_id, inline=True)
            if voice_config.speed != 1.0:
                embed.add_field(name="⚡ Speed", value=f"{voice_config.speed}x", inline=True)
            
            await interaction.edit_original_response(embed=embed)
        else:
            response = handle_use_case_result(result)
            await interaction.edit_original_response(**response)
    
    async def _handle_status(self, interaction):
        """Show voice status"""
        result = await container.voice_use_case.get_voice_status(str(interaction.guild.id))
        
        voice_client = interaction.guild.voice_client
        
        embed = discord.Embed(
            title="🔊 Voice Status",
            color=0x00FF00 if result.is_connected else 0x808080
        )
        
        if voice_client and voice_client.is_connected():
            embed.add_field(
                name="📡 Connection",
                value=f"✅ Connected to **{voice_client.channel.name}**",
                inline=False
            )
            
            embed.add_field(
                name="👥 Channel Members",
                value=f"{len(voice_client.channel.members)} members",
                inline=True
            )
            
            if voice_client.is_playing():
                embed.add_field(
                    name="🎵 Status",
                    value="🎵 Currently playing audio",
                    inline=True
                )
            else:
                embed.add_field(
                    name="🎵 Status",
                    value="🔇 Ready for audio",
                    inline=True
                )
        else:
            embed.add_field(
                name="📡 Connection",
                value="❌ Not connected to voice",
                inline=False
            )
            
            embed.add_field(
                name="💡 Tip",
                value="Use `/voice join` to connect to your voice channel",
                inline=False
            )
        
        await interaction.followup.send(embed=embed)
    
    async def _handle_list_voices(self, interaction):
        """List available TTS voices"""
        result = await container.voice_use_case.list_available_voices()
        
        if result.success:
            voices = result.metadata.get("voices", [])
            
            embed = discord.Embed(
                title="🎭 Available Voices",
                description="Use these voice IDs with `/voice speak`",
                color=0x7B68EE
            )
            
            # Group voices for better display
            if voices:
                voice_list = "\n".join([f"• `{voice}`" for voice in voices])
                embed.add_field(
                    name="🔊 Voice Options",
                    value=voice_list,
                    inline=False
                )
            else:
                embed.add_field(
                    name="ℹ️ Default Only",
                    value="Only default voice available",
                    inline=False
                )
            
            embed.add_field(
                name="💡 Usage",
                value="`/voice speak text:\"Hello!\" voice_id:default`",
                inline=False
            )
            
            await interaction.followup.send(embed=embed)
        else:
            response = handle_use_case_result(result)
            await interaction.followup.send(**response)
    
    async def _handle_settings(self, interaction, voice_id, speed):
        """Handle voice settings change"""
        if not voice_id and not speed:
            # Show current settings
            embed = discord.Embed(
                title="⚙️ Voice Settings",
                description="Configure your voice preferences",
                color=0x7B68EE
            )
            
            embed.add_field(
                name="🎭 Voice Options",
                value="Use `/voice voices` to see available voices",
                inline=False
            )
            
            embed.add_field(
                name="⚡ Speed Control",
                value="Set speed between 0.5x and 2.0x\n"
                      "• 0.5x = Very slow\n"
                      "• 1.0x = Normal speed\n"
                      "• 1.5x = Fast\n"
                      "• 2.0x = Very fast",
                inline=False
            )
            
            embed.add_field(
                name="💡 Example",
                value="`/voice settings voice_id:narrator speed:1.2`",
                inline=False
            )
            
            await interaction.followup.send(embed=embed)
            return
        
        # Validate settings
        if speed and (speed < 0.5 or speed > 2.0):
            await interaction.followup.send("❌ Speed must be between 0.5 and 2.0")
            return
        
        # Create voice config
        voice_config = VoiceConfig(
            voice_id=voice_id or "default",
            speed=speed or 1.25
        )
        
        command = VoiceCommand(
            guild_id=str(interaction.guild.id),
            action="change_settings",
            voice_config=voice_config
        )
        
        result = await container.voice_use_case.change_voice_settings(command)
        
        if result.success:
            embed = discord.Embed(
                title="✅ Voice Settings Updated",
                color=0x00FF00
            )
            
            if voice_id:
                embed.add_field(name="🎭 Voice", value=voice_id, inline=True)
            if speed:
                embed.add_field(name="⚡ Speed", value=f"{speed}x", inline=True)
            
            embed.add_field(
                name="💡 Test It",
                value="Use `/voice speak` to test your new settings!",
                inline=False
            )
            
            await interaction.followup.send(embed=embed)
        else:
            response = handle_use_case_result(result)
            await interaction.followup.send(**response)


# Voice utility functions
class VoiceUtilities(commands.Cog):
    """Voice utility commands"""
    
    def __init__(self, bot):
        self.bot = bot
    
    @app_commands.command(name="speak", description="Quick text-to-speech command")
    @app_commands.describe(text="Text to speak aloud")
    async def quick_speak(self, interaction: discord.Interaction, text: str):
        """Quick TTS command"""
        
        # Check if connected to voice
        if not interaction.guild.voice_client or not interaction.guild.voice_client.is_connected():
            await interaction.response.send_message(
                "❌ Not connected to voice! Use `/voice join` first.",
                ephemeral=True
            )
            return
        
        await interaction.response.defer()
        
        command = VoiceCommand(
            guild_id=str(interaction.guild.id),
            action="speak",
            text_to_speak=text
        )
        
        result = await container.voice_use_case.speak_text(command)
        
        if result.success:
            await interaction.followup.send(f"🗣️ Speaking: *{text}*")
        else:
            response = handle_use_case_result(result)
            await interaction.followup.send(**response)