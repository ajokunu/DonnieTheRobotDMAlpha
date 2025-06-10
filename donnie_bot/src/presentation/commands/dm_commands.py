"""
Dungeon Master specific commands
"""
import discord
from discord.ext import commands
from discord import app_commands
from typing import Optional

from ..dependency_injection import container
from ..discord_bot import handle_use_case_result
from ...application.dto import DMActionCommand, UpdateGuildSettingsCommand


class DMCommands(commands.Cog):
    """Dungeon Master specific commands"""
    
    def __init__(self, bot):
        self.bot = bot
    
    def is_dm_or_admin():
        """Check if user is DM or admin"""
        def predicate(interaction: discord.Interaction) -> bool:
            # Check if user has admin permissions or specific DM role
            if interaction.user.guild_permissions.administrator:
                return True
            
            # Check for DM role (customize role names as needed)
            dm_role_names = ["DM", "Dungeon Master", "Game Master", "GM"]
            user_roles = [role.name for role in interaction.user.roles]
            
            return any(role in dm_role_names for role in user_roles)
        
        return app_commands.check(predicate)
    
    @app_commands.command(name="dm", description="Dungeon Master commands")
    @app_commands.describe(
        action="DM action to perform",
        scene_description="Scene or narration to add",
        setting="Setting to change",
        value="New value for setting"
    )
    @app_commands.choices(action=[
        app_commands.Choice(name="Narrate Scene", value="narrate"),
        app_commands.Choice(name="Set Scene", value="scene"),
        app_commands.Choice(name="Change Settings", value="settings"),
        app_commands.Choice(name="Force End Episode", value="force_end")
    ])
    @is_dm_or_admin()
    async def dm_command(self,
                        interaction: discord.Interaction,
                        action: str,
                        scene_description: Optional[str] = None,
                        setting: Optional[str] = None,
                        value: Optional[str] = None):
        """Main DM command"""
        
        await interaction.response.defer()
        
        try:
            if action == "narrate":
                await self._handle_narrate(interaction, scene_description)
            elif action == "scene":
                await self._handle_set_scene(interaction, scene_description)
            elif action == "settings":
                await self._handle_settings(interaction, setting, value)
            elif action == "force_end":
                await self._handle_force_end(interaction)
            else:
                await interaction.followup.send("❌ Unknown DM action")
                
        except Exception as e:
            await interaction.followup.send(f"❌ Error: {str(e)}")
    
    async def _handle_narrate(self, interaction, scene_description):
        """Handle DM narration"""
        if not scene_description:
            await interaction.followup.send(
                "❌ Scene description is required!\n"
                "Use: `/dm narrate scene_description:\"The ground shakes as...\"`"
            )
            return
        
        if not container.action_use_case:
            await interaction.followup.send("❌ Action system not available")
            return
        
        command = DMActionCommand(
            guild_id=str(interaction.guild.id),
            dm_user_id=str(interaction.user.id),
            scene_description=scene_description,
            action_type="narration"
        )
        
        # Show that we're processing
        await interaction.followup.send(f"🎲 **DM Narration**\n\n*{scene_description}*\n\n⚡ Processing...")
        
        result = await container.action_use_case.handle_dm_action(command)
        
        if result.success and result.dm_response:
            embed = discord.Embed(
                title="🎲 DM Narration",
                description=result.dm_response.text,
                color=0x7B68EE
            )
            
            embed.set_author(
                name=f"DM: {interaction.user.display_name}",
                icon_url=interaction.user.display_avatar.url
            )
            
            embed.add_field(
                name="📝 Scene Set",
                value=scene_description,
                inline=False
            )
            
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
                        pass  # Don't fail if voice fails
        else:
            response = handle_use_case_result(result)
            await interaction.edit_original_response(**response)
    
    async def _handle_set_scene(self, interaction, scene_description):
        """Set current scene without AI processing"""
        if not scene_description:
            await interaction.followup.send("❌ Scene description is required!")
            return
        
        # Just announce the scene change
        embed = discord.Embed(
            title="🎬 Scene Change",
            description=scene_description,
            color=0x7B68EE
        )
        
        embed.set_author(
            name=f"DM: {interaction.user.display_name}",
            icon_url=interaction.user.display_avatar.url
        )
        
        await interaction.followup.send(embed=embed)
        
        # Try to speak it if voice is connected
        if container.voice_service:
            voice_connected = await container.voice_service.is_connected(str(interaction.guild.id))
            if voice_connected:
                from ...application.dto import VoiceCommand
                voice_command = VoiceCommand(
                    guild_id=str(interaction.guild.id),
                    action="speak",
                    text_to_speak=scene_description
                )
                try:
                    await container.voice_use_case.speak_text(voice_command)
                except:
                    pass
    
    async def _handle_settings(self, interaction, setting, value):
        """Handle guild settings changes"""
        if not setting or not value:
            # Show current settings
            embed = discord.Embed(
                title="⚙️ Guild Settings",
                description="Available settings to change:",
                color=0x7B68EE
            )
            
            embed.add_field(
                name="Voice Settings",
                value="`voice_enabled` - Enable/disable voice features (true/false)\n"
                      "`voice_speed` - TTS speed (0.5-2.0)\n"
                      "`voice_quality` - TTS quality (speed/quality/smart)",
                inline=False
            )
            
            embed.add_field(
                name="Usage",
                value="`/dm settings setting:voice_enabled value:true`",
                inline=False
            )
            
            await interaction.followup.send(embed=embed)
            return
        
        # Apply setting change
        settings_dict = {}
        
        if setting == "voice_enabled":
            settings_dict["voice_enabled"] = value.lower() in ("true", "1", "yes", "on")
        elif setting == "voice_speed":
            try:
                speed = float(value)
                if 0.5 <= speed <= 2.0:
                    settings_dict["voice_speed"] = speed
                else:
                    await interaction.followup.send("❌ Voice speed must be between 0.5 and 2.0")
                    return
            except ValueError:
                await interaction.followup.send("❌ Voice speed must be a number")
                return
        elif setting == "voice_quality":
            if value in ["speed", "quality", "smart"]:
                settings_dict["voice_quality"] = value
            else:
                await interaction.followup.send("❌ Voice quality must be 'speed', 'quality', or 'smart'")
                return
        else:
            await interaction.followup.send(f"❌ Unknown setting: {setting}")
            return
        
        # In a real implementation, you'd save these to the guild repository
        embed = discord.Embed(
            title="✅ Setting Updated",
            description=f"**{setting}** = `{value}`",
            color=0x00FF00
        )
        
        await interaction.followup.send(embed=embed)
    
    async def _handle_force_end(self, interaction):
        """Force end current episode (emergency use)"""
        if not container.episode_use_case:
            await interaction.followup.send("❌ Episode system not available")
            return
        
        # Create confirmation view
        view = ForceEndConfirmView(interaction.user.id)
        
        embed = discord.Embed(
            title="⚠️ Force End Episode",
            description="This will immediately end the current episode without proper cleanup.\n\n"
                       "**Use only in emergencies!**\n\n"
                       "Consider using `/episode end` with a summary instead.",
            color=0xFF0000
        )
        
        await interaction.followup.send(embed=embed, view=view)


class ForceEndConfirmView(discord.ui.View):
    """Confirmation view for force ending episode"""
    
    def __init__(self, user_id: int):
        super().__init__(timeout=30.0)
        self.user_id = user_id
    
    @discord.ui.button(label="Force End Episode", style=discord.ButtonStyle.danger, emoji="⚠️")
    async def confirm_force_end(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Only the DM who initiated this can confirm", ephemeral=True)
            return
        
        from ...application.dto import EndEpisodeCommand
        
        command = EndEpisodeCommand(
            guild_id=str(interaction.guild.id),
            summary="Episode force-ended by DM",
            dm_user_id=str(interaction.user.id)
        )
        
        result = await container.episode_use_case.end_episode(command)
        
        self.clear_items()
        
        if result.success:
            embed = discord.Embed(
                title="⚠️ Episode Force-Ended",
                description="The current episode has been force-ended.",
                color=0xFF8C00
            )
        else:
            embed = discord.Embed(
                title="❌ Force End Failed",
                description=result.error,
                color=0xFF0000
            )
        
        await interaction.response.edit_message(embed=embed, view=self)
    
    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary, emoji="❌")
    async def cancel_force_end(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Only the DM who initiated this can cancel", ephemeral=True)
            return
        
        self.clear_items()
        
        embed = discord.Embed(
            title="✅ Cancelled",
            description="Force end cancelled. Episode continues.",
            color=0x00FF00
        )
        
        await interaction.response.edit_message(embed=embed, view=self)


# Quick DM utilities
class QuickDMCommands(commands.Cog):
    """Quick DM utility commands"""
    
    def __init__(self, bot):
        self.bot = bot
    
    @app_commands.command(name="roll", description="Roll dice (DM tool)")
    @app_commands.describe(
        dice="Dice notation (e.g., 1d20, 2d6+3, 1d20+5)",
        description="What you're rolling for (optional)"
    )
    async def roll_dice(self,
                       interaction: discord.Interaction,
                       dice: str,
                       description: Optional[str] = None):
        """Roll dice for DM use"""
        
        await interaction.response.defer()
        
        try:
            # Use combat service for dice rolling
            if container.combat_service:
                if "d20" in dice.lower():
                    # Handle d20 rolls
                    modifier = 0
                    if "+" in dice:
                        parts = dice.split("+")
                        modifier = int(parts[1]) if len(parts) > 1 else 0
                    elif "-" in dice:
                        parts = dice.split("-")
                        modifier = -int(parts[1]) if len(parts) > 1 else 0
                    
                    roll = container.combat_service.roll_d20()
                    total = roll + modifier
                    
                    embed = discord.Embed(
                        title="🎲 Dice Roll",
                        description=f"**{dice}**",
                        color=0x7B68EE
                    )
                    
                    embed.add_field(
                        name="Result",
                        value=f"🎲 {roll} + {modifier} = **{total}**" if modifier != 0 else f"🎲 **{roll}**",
                        inline=False
                    )
                    
                    if description:
                        embed.add_field(
                            name="Rolling for",
                            value=description,
                            inline=False
                        )
                    
                    # Critical/fumble indication
                    if roll == 20:
                        embed.add_field(name="🎯", value="**Critical Success!**", inline=False)
                        embed.color = 0x00FF00
                    elif roll == 1:
                        embed.add_field(name="💥", value="**Critical Fumble!**", inline=False)
                        embed.color = 0xFF0000
                    
                    embed.set_footer(text=f"Rolled by {interaction.user.display_name}")
                    
                else:
                    # Handle other dice (damage, etc.)
                    result = container.combat_service.roll_damage(dice)
                    
                    embed = discord.Embed(
                        title="🎲 Dice Roll",
                        description=f"**{dice}**",
                        color=0x7B68EE
                    )
                    
                    embed.add_field(
                        name="Result",
                        value=f"🎲 **{result}**",
                        inline=False
                    )
                    
                    if description:
                        embed.add_field(
                            name="Rolling for",
                            value=description,
                            inline=False
                        )
                    
                    embed.set_footer(text=f"Rolled by {interaction.user.display_name}")
            else:
                # Fallback simple rolling
                import random
                if "d20" in dice.lower():
                    result = random.randint(1, 20)
                elif "d6" in dice.lower():
                    result = random.randint(1, 6)
                else:
                    result = random.randint(1, 20)  # Default
                
                embed = discord.Embed(
                    title="🎲 Simple Roll",
                    description=f"**{dice}** → **{result}**",
                    color=0x7B68EE
                )
            
            await interaction.followup.send(embed=embed)
            
        except Exception as e:
            await interaction.followup.send(f"❌ Error rolling dice: {str(e)}")