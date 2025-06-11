"""
Voice and audio Discord commands
"""
import discord
from discord.ext import commands
from discord import app_commands
from typing import Optional

from ..dependency_injection import container
from ..utils import handle_use_case_result


class VoiceCommands(commands.Cog):
    """Voice and audio commands"""
    
    def __init__(self, bot):
        self.bot = bot
    
    @app_commands.command(name="voice", description="Voice and audio commands")
    @app_commands.describe(
        action="Voice action to perform",
        text="Text to speak (for speak action)"
    )
    @app_commands.choices(action=[
        app_commands.Choice(name="Join Voice Channel", value="join"),
        app_commands.Choice(name="Leave Voice Channel", value="leave"),
        app_commands.Choice(name="Speak Text", value="speak"),
        app_commands.Choice(name="Voice Status", value="status")
    ])
    async def voice(self,
                   interaction: discord.Interaction,
                   action: str,
                   text: Optional[str] = None):
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
                await self._handle_speak(interaction, text)
            elif action == "status":
                await self._handle_status(interaction)
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
        
        await interaction.followup.send("🔊 Voice features coming soon!")
    
    async def _handle_leave(self, interaction):
        """Handle leaving voice channel"""
        await interaction.followup.send("🔇 Voice features coming soon!")
    
    async def _handle_speak(self, interaction, text):
        """Handle text-to-speech"""
        if not text:
            await interaction.followup.send("❌ Please provide text to speak!")
            return
        
        await interaction.followup.send(f"🗣️ Voice TTS coming soon!\nText: *{text}*")
    
    async def _handle_status(self, interaction):
        """Show voice status"""
        embed = discord.Embed(
            title="🔊 Voice Status",
            description="Voice features are not yet implemented",
            color=0x808080
        )
        await interaction.followup.send(embed=embed)


class VoiceUtilities(commands.Cog):
    """Voice utility commands"""
    
    def __init__(self, bot):
        self.bot = bot
    
    @app_commands.command(name="speak", description="Quick text-to-speech command")
    @app_commands.describe(text="Text to speak aloud")
    async def quick_speak(self, interaction: discord.Interaction, text: str):
        """Quick TTS command"""
        await interaction.response.send_message(f"🗣️ TTS coming soon!\nText: *{text}*", ephemeral=True)