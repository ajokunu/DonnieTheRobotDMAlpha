"""
Character management Discord commands
"""
import discord
from discord.ext import commands
from discord import app_commands
from typing import Optional

from ..dependency_injection import container
from ..discord_bot import handle_use_case_result, create_character_embed
from ...application.dto import (
    CreateCharacterCommand, GenerateCharacterCommand, LevelUpCommand,
    HealCommand, DamageCommand
)
from ...domain.entities import Race, CharacterClass


class CharacterCommands(commands.Cog):
    """Character management commands"""
    
    def __init__(self, bot):
        self.bot = bot
    
    @app_commands.command(name="character", description="Character management commands")
    @app_commands.describe(
        action="What to do with your character",
        name="Character name (for create)",
        description="Character description for AI generation (for generate)",
        race="Character race (for create)",
        character_class="Character class (for create)",
        background="Character background (for create)",
        level="New level (for levelup)",
        amount="Amount to heal/damage"
    )
    @app_commands.choices(action=[
        app_commands.Choice(name="Create Character", value="create"),
        app_commands.Choice(name="Generate Character (AI)", value="generate"),
        app_commands.Choice(name="Show Character", value="show"),
        app_commands.Choice(name="Level Up", value="levelup"),
        app_commands.Choice(name="Heal", value="heal"),
        app_commands.Choice(name="Take Damage", value="damage"),
        app_commands.Choice(name="Delete Character", value="delete")
    ])
    @app_commands.choices(race=[
        app_commands.Choice(name=race.value, value=race.value) for race in Race
    ])
    @app_commands.choices(character_class=[
        app_commands.Choice(name=cls.value, value=cls.value) for cls in CharacterClass
    ])
    async def character(self, 
                       interaction: discord.Interaction,
                       action: str,
                       name: Optional[str] = None,
                       description: Optional[str] = None,
                       race: Optional[str] = None,
                       character_class: Optional[str] = None,
                       background: Optional[str] = None,
                       level: Optional[int] = None,
                       amount: Optional[int] = None):
        """Main character command"""
        
        await interaction.response.defer()
        
        if not container.character_use_case:
            await interaction.followup.send("❌ Character system not available")
            return
        
        try:
            if action == "create":
                await self._handle_create(interaction, name, race, character_class, background)
            elif action == "generate":
                await self._handle_generate(interaction, description)
            elif action == "show":
                await self._handle_show(interaction)
            elif action == "levelup":
                await self._handle_levelup(interaction, level)
            elif action == "heal":
                await self._handle_heal(interaction, amount)
            elif action == "damage":
                await self._handle_damage(interaction, amount)
            elif action == "delete":
                await self._handle_delete(interaction)
            else:
                await interaction.followup.send("❌ Unknown action")
                
        except Exception as e:
            await interaction.followup.send(f"❌ Error: {str(e)}")
    
    async def _handle_create(self, interaction, name, race, character_class, background):
        """Handle character creation"""
        if not all([name, race, character_class]):
            await interaction.followup.send(
                "❌ Missing required fields for character creation!\n"
                "Use: `/character create name:YourName race:Human character_class:Fighter`"
            )
            return
        
        command = CreateCharacterCommand(
            name=name,
            player_name=interaction.user.display_name,
            discord_user_id=str(interaction.user.id),
            guild_id=str(interaction.guild.id),
            race=Race(race),
            character_class=CharacterClass(character_class),
            background=background or ""
        )
        
        result = await container.character_use_case.create_character(command)
        
        if result.success:
            embed = create_character_embed(result.character)
            embed.set_author(
                name=f"Character Created!",
                icon_url=interaction.user.display_avatar.url
            )
            await interaction.followup.send(embed=embed)
        else:
            response = handle_use_case_result(result)
            await interaction.followup.send(**response)
    
    async def _handle_generate(self, interaction, description):
        """Handle AI character generation"""
        if not description:
            await interaction.followup.send(
                "❌ Please provide a character description!\n"
                "Example: `/character generate description:\"A brave knight from the northern kingdoms\"`"
            )
            return
        
        if not container.ai_service:
            await interaction.followup.send("❌ AI character generation not available (missing API key)")
            return
        
        # Show typing indicator for AI generation
        await interaction.followup.send("🎲 Generating character with AI... This may take a moment!")
        
        command = GenerateCharacterCommand(
            description=description,
            player_name=interaction.user.display_name,
            discord_user_id=str(interaction.user.id),
            guild_id=str(interaction.guild.id)
        )
        
        result = await container.character_use_case.generate_character(command)
        
        if result.success:
            embed = create_character_embed(result.character)
            embed.set_author(
                name="AI Generated Character!",
                icon_url=interaction.user.display_avatar.url
            )
            embed.add_field(
                name="🤖 AI Description",
                value=f"*Based on: {description}*",
                inline=False
            )
            await interaction.edit_original_response(content=None, embed=embed)
        else:
            response = handle_use_case_result(result)
            await interaction.edit_original_response(**response)
    
    async def _handle_show(self, interaction):
        """Show character information"""
        result = await container.character_use_case.get_character(
            str(interaction.user.id),
            str(interaction.guild.id)
        )
        
        if result.success:
            embed = create_character_embed(result.character)
            embed.set_author(
                name=f"{interaction.user.display_name}'s Character",
                icon_url=interaction.user.display_avatar.url
            )
            await interaction.followup.send(embed=embed)
        else:
            response = handle_use_case_result(result)
            await interaction.followup.send(**response)
    
    async def _handle_levelup(self, interaction, level):
        """Handle character level up"""
        if not level or level < 1 or level > 20:
            await interaction.followup.send("❌ Please specify a valid level (1-20)")
            return
        
        command = LevelUpCommand(
            discord_user_id=str(interaction.user.id),
            guild_id=str(interaction.guild.id),
            new_level=level
        )
        
        result = await container.character_use_case.level_up_character(command)
        
        if result.success:
            embed = create_character_embed(result.character)
            embed.set_author(
                name="Level Up!",
                icon_url="https://i.imgur.com/P8hWzP6.png"  # Level up icon
            )
            embed.color = 0xFFD700  # Gold color for level up
            await interaction.followup.send(embed=embed)
        else:
            response = handle_use_case_result(result)
            await interaction.followup.send(**response)
    
    async def _handle_heal(self, interaction, amount):
        """Handle character healing"""
        if not amount or amount < 1:
            await interaction.followup.send("❌ Please specify a positive healing amount")
            return
        
        command = HealCommand(
            discord_user_id=str(interaction.user.id),
            guild_id=str(interaction.guild.id),
            amount=amount
        )
        
        result = await container.character_use_case.heal_character(command)
        
        if result.success:
            embed = discord.Embed(
                title="💚 Healing",
                description=result.message,
                color=0x00FF00
            )
            embed.set_author(
                name=f"{interaction.user.display_name}",
                icon_url=interaction.user.display_avatar.url
            )
            await interaction.followup.send(embed=embed)
        else:
            response = handle_use_case_result(result)
            await interaction.followup.send(**response)
    
    async def _handle_damage(self, interaction, amount):
        """Handle character damage"""
        if not amount or amount < 1:
            await interaction.followup.send("❌ Please specify a positive damage amount")
            return
        
        command = DamageCommand(
            discord_user_id=str(interaction.user.id),
            guild_id=str(interaction.guild.id),
            amount=amount
        )
        
        result = await container.character_use_case.damage_character(command)
        
        if result.success:
            color = 0xFF0000 if not result.is_alive else 0xFF8C00
            embed = discord.Embed(
                title="💔 Damage Taken",
                description=result.message,
                color=color
            )
            embed.set_author(
                name=f"{interaction.user.display_name}",
                icon_url=interaction.user.display_avatar.url
            )
            
            if not result.is_alive:
                embed.add_field(
                    name="💀 Death Saves",
                    value="Your character is unconscious!\nMake death saving throws on your turn.",
                    inline=False
                )
            
            await interaction.followup.send(embed=embed)
        else:
            response = handle_use_case_result(result)
            await interaction.followup.send(**response)
    
    async def _handle_delete(self, interaction):
        """Handle character deletion with confirmation"""
        # First, get the character to show what will be deleted
        char_result = await container.character_use_case.get_character(
            str(interaction.user.id),
            str(interaction.guild.id)
        )
        
        if not char_result.success:
            response = handle_use_case_result(char_result)
            await interaction.followup.send(**response)
            return
        
        # Create confirmation view
        view = CharacterDeleteView(
            user_id=interaction.user.id,
            character_name=char_result.character.name
        )
        
        embed = discord.Embed(
            title="⚠️ Delete Character",
            description=f"Are you sure you want to delete **{char_result.character.name}**?\n\n"
                       f"This action cannot be undone!",
            color=0xFF0000
        )
        
        await interaction.followup.send(embed=embed, view=view)


class CharacterDeleteView(discord.ui.View):
    """Confirmation view for character deletion"""
    
    def __init__(self, user_id: int, character_name: str):
        super().__init__(timeout=30.0)
        self.user_id = user_id
        self.character_name = character_name
    
    @discord.ui.button(label="Yes, Delete", style=discord.ButtonStyle.danger, emoji="🗑️")
    async def confirm_delete(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Only the character owner can delete it", ephemeral=True)
            return
        
        result = await container.character_use_case.delete_character(
            str(interaction.user.id),
            str(interaction.guild.id)
        )
        
        self.clear_items()
        
        if result.success:
            embed = discord.Embed(
                title="🗑️ Character Deleted",
                description=f"**{self.character_name}** has been deleted.",
                color=0x808080
            )
        else:
            embed = discord.Embed(
                title="❌ Deletion Failed",
                description=result.error,
                color=0xFF0000
            )
        
        await interaction.response.edit_message(embed=embed, view=self)
    
    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary, emoji="❌")
    async def cancel_delete(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Only the character owner can cancel", ephemeral=True)
            return
        
        self.clear_items()
        
        embed = discord.Embed(
            title="✅ Cancelled",
            description=f"**{self.character_name}** is safe!",
            color=0x00FF00
        )
        
        await interaction.response.edit_message(embed=embed, view=self)
    
    async def on_timeout(self):
        """Handle timeout"""
        self.clear_items()
        # Note: Can't edit message on timeout without interaction


# Party commands as separate group
class PartyCommands(commands.Cog):
    """Party management commands"""
    
    def __init__(self, bot):
        self.bot = bot
    
    @app_commands.command(name="party", description="View party information")
    @app_commands.describe(action="What party information to show")
    @app_commands.choices(action=[
        app_commands.Choice(name="Show All Members", value="show"),
        app_commands.Choice(name="Health Summary", value="health")
    ])
    async def party(self, interaction: discord.Interaction, action: str = "show"):
        """Party information commands"""
        
        await interaction.response.defer()
        
        if not container.character_use_case:
            await interaction.followup.send("❌ Character system not available")
            return
        
        result = await container.character_use_case.get_party(str(interaction.guild.id))
        
        if not result.success:
            response = handle_use_case_result(result)
            await interaction.followup.send(**response)
            return
        
        if not result.party_members:
            embed = discord.Embed(
                title="👥 Party",
                description="No characters found in this server.\nUse `/character create` to make your first character!",
                color=0x808080
            )
            await interaction.followup.send(embed=embed)
            return
        
        if action == "health":
            await self._show_party_health(interaction, result)
        else:
            await self._show_party_members(interaction, result)
    
    async def _show_party_members(self, interaction, result):
        """Show all party members"""
        embed = discord.Embed(
            title=f"👥 Party ({len(result.party_members)} members)",
            description=f"Average Level: {result.party_level:.1f}",
            color=0x7B68EE
        )
        
        for character in result.party_members:
            health_emoji = "💚" if character.current_hp == character.max_hp else "💛" if character.current_hp > character.max_hp // 2 else "❤️" if character.current_hp > 0 else "💀"
            
            embed.add_field(
                name=f"{health_emoji} {character.name}",
                value=f"Level {character.level} {character.race.value} {character.character_class.value}\n"
                      f"HP: {character.current_hp}/{character.max_hp} | {character.get_health_status()}",
                inline=True
            )
        
        await interaction.followup.send(embed=embed)
    
    async def _show_party_health(self, interaction, result):
        """Show party health summary"""
        health_summary = result.health_summary
        
        embed = discord.Embed(
            title="💚 Party Health Summary",
            color=0x00FF00
        )
        
        # Health distribution
        total = health_summary["total_characters"]
        embed.add_field(
            name="📊 Health Distribution",
            value=f"💚 Healthy: {health_summary['healthy']}/{total}\n"
                  f"💛 Wounded: {health_summary['wounded']}/{total}\n"
                  f"❤️ Critical: {health_summary['critical']}/{total}\n"
                  f"💀 Unconscious: {health_summary['unconscious']}/{total}",
            inline=False
        )
        
        # Individual status
        status_lines = []
        for character in result.party_members:
            status_emoji = "💚" if character.current_hp == character.max_hp else "💛" if character.current_hp > character.max_hp // 2 else "❤️" if character.current_hp > 0 else "💀"
            hp_percentage = int((character.current_hp / character.max_hp) * 100) if character.max_hp > 0 else 0
            status_lines.append(f"{status_emoji} **{character.name}**: {character.current_hp}/{character.max_hp} HP ({hp_percentage}%)")
        
        if status_lines:
            embed.add_field(
                name="👥 Individual Status",
                value="\n".join(status_lines),
                inline=False
            )
        
        await interaction.followup.send(embed=embed)