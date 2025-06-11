"""
Presentation layer utilities - shared functions
"""
import discord
from typing import Dict, Any

from ..application.dto import CommandResult


def handle_use_case_result(result: CommandResult, success_message: str = None) -> Dict[str, Any]:
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