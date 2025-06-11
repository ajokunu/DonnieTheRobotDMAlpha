"""
Dungeon Master specific commands
"""
import discord
from discord.ext import commands
from discord import app_commands
from typing import Optional

from ..dependency_injection import container
from ..utils import handle_use_case_result


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
    @app_commands.describe(scene_description="Scene or narration to add")
    @is_dm_or_admin()
    async def dm_command(self, interaction: discord.Interaction, scene_description: str):
        """DM narration command"""
        
        await interaction.response.defer()
        
        if not scene_description:
            await interaction.followup.send("❌ Scene description is required!")
            return
        
        # Simple DM narration
        embed = discord.Embed(
            title="🎲 DM Narration",
            description=scene_description,
            color=0x7B68EE
        )
        
        embed.set_author(
            name=f"DM: {interaction.user.display_name}",
            icon_url=interaction.user.display_avatar.url
        )
        
        await interaction.followup.send(embed=embed)


class QuickDMCommands(commands.Cog):
    """Quick DM utility commands"""
    
    def __init__(self, bot):
        self.bot = bot
    
    @app_commands.command(name="roll", description="Roll dice (DM tool)")
    @app_commands.describe(dice="Dice notation (e.g., 1d20, 2d6+3)")
    async def roll_dice(self, interaction: discord.Interaction, dice: str):
        """Roll dice for DM use"""
        
        await interaction.response.defer()
        
        try:
            # Simple dice rolling
            import random
            if "d20" in dice.lower():
                result = random.randint(1, 20)
                embed = discord.Embed(
                    title="🎲 D20 Roll",
                    description=f"**{dice}** → **{result}**",
                    color=0x00FF00 if result >= 15 else 0xFF0000 if result <= 5 else 0x7B68EE
                )
                
                if result == 20:
                    embed.add_field(name="🎯", value="**Critical Success!**", inline=False)
                elif result == 1:
                    embed.add_field(name="💥", value="**Critical Fumble!**", inline=False)
            else:
                # Default d6 for other dice
                result = random.randint(1, 6)
                embed = discord.Embed(
                    title="🎲 Dice Roll",
                    description=f"**{dice}** → **{result}**",
                    color=0x7B68EE
                )
            
            embed.set_footer(text=f"Rolled by {interaction.user.display_name}")
            await interaction.followup.send(embed=embed)
            
        except Exception as e:
            await interaction.followup.send(f"❌ Error rolling dice: {str(e)}")