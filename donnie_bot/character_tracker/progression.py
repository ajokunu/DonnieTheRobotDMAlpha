# character_tracker/progression.py
# UPDATE: Replace your existing progression.py with this enhanced version

import discord
from discord.ext import commands
from discord import app_commands
from typing import Optional, Dict, Any, Callable, List
import asyncio
from datetime import datetime

# Import our database operations
try:
    from database.operations import CharacterOperations, EpisodeOperations, DatabaseOperationError
    DATABASE_AVAILABLE = True
except ImportError:
    DATABASE_AVAILABLE = False
    # Create fallback classes
    class CharacterOperations:
        @staticmethod
        def record_character_progression(*args, **kwargs): return None
        @staticmethod
        def get_character_progression_history(*args, **kwargs): return []
        @staticmethod
        def create_character_snapshot(*args, **kwargs): return None
    
    class EpisodeOperations:
        @staticmethod
        def get_current_episode(*args, **kwargs): return None

class CharacterProgressionCommands:
    """Enhanced Character Progression with Database Integration"""
    
    def __init__(self, bot: commands.Bot, campaign_context: Dict, voice_clients: Dict,
                 tts_enabled: Dict, add_to_voice_queue_func: Callable,
                 character_operations=None, episode_operations=None):
        self.bot = bot
        self.campaign_context = campaign_context
        self.voice_clients = voice_clients
        self.tts_enabled = tts_enabled
        self.add_to_voice_queue = add_to_voice_queue_func
        
        # Store database operations classes
        self.character_ops = character_operations or CharacterOperations
        self.episode_ops = episode_operations or EpisodeOperations
        
        # Register commands
        self._register_commands()
        
        print(f"✅ Character Progression initialized (Database: {'✅' if DATABASE_AVAILABLE else '❌'})")
    
    def _register_commands(self):
        """Register all character progression commands"""
        
        @self.bot.tree.command(name="level_up", description="Level up your character with progression tracking")
        @app_commands.describe(
            new_level="Your character's new level (1-20)",
            reason="Why are you leveling up? (milestone, XP, etc.)"
        )
        async def level_up(interaction: discord.Interaction, new_level: int, reason: Optional[str] = None):
            await self._level_up_command(interaction, new_level, reason)
        
        @self.bot.tree.command(name="character_progression", description="View character level progression history")
        @app_commands.describe(player="View another player's progression (optional)")
        async def character_progression(interaction: discord.Interaction, player: Optional[discord.Member] = None):
            await self._character_progression_command(interaction, player)
        
        @self.bot.tree.command(name="party_progression", description="View entire party's progression across episodes")
        async def party_progression(interaction: discord.Interaction):
            await self._party_progression_command(interaction)
        
        @self.bot.tree.command(name="character_snapshot", description="Create a manual character snapshot")
        @app_commands.describe(notes="Optional notes about this snapshot")
        async def character_snapshot(interaction: discord.Interaction, notes: Optional[str] = None):
            await self._character_snapshot_command(interaction, notes)
    
    async def _level_up_command(self, interaction: discord.Interaction, new_level: int, reason: Optional[str]):
        """Handle character level up with database tracking"""
        user_id = str(interaction.user.id)
        
        # Validate level
        if new_level < 1 or new_level > 20:
            embed = discord.Embed(
                title="❌ Invalid Level",
                description="Character level must be between 1 and 20!",
                color=0xFF6B6B
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        # Check if character is registered
        if user_id not in self.campaign_context["players"]:
            embed = discord.Embed(
                title="🎭 Character Not Registered",
                description="Please register your character first using `/character`!",
                color=0xFF6B6B
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        # Get character data
        player_data = self.campaign_context["players"][user_id]
        char_data = player_data["character_data"]
        character_name = char_data["name"]
        old_level = char_data.get("level", 1)
        
        # Check if this is actually a level up
        if new_level <= old_level:
            embed = discord.Embed(
                title="⚠️ Not a Level Up",
                description=f"{character_name} is already level {old_level}. New level must be higher!",
                color=0xFFD700
            )
            embed.add_field(
                name="💡 Tip",
                value="Use `/update_character` if you need to correct your current level.",
                inline=False
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        # Get current episode for tracking
        episode_id = None
        episode_number = None
        if DATABASE_AVAILABLE:
            try:
                guild_id = str(interaction.guild.id)
                current_episode = self.episode_ops.get_current_episode(guild_id)
                if current_episode:
                    episode_id = current_episode.id
                    episode_number = current_episode.episode_number
            except Exception as e:
                print(f"Error getting current episode for level up: {e}")
        
        # Update character data
        char_data["level"] = new_level
        
        # Rebuild character description for Claude
        character_description = f"""
NAME: {char_data['name']}
PLAYER: {player_data['player_name']} (Discord ID: {user_id})
RACE & CLASS: {char_data['race']} {char_data['class']} (Level {char_data['level']})
BACKGROUND: {char_data['background']}
ABILITY SCORES: {char_data['stats']}
EQUIPMENT: {char_data['equipment']}
SPELLS: {char_data['spells']}
AFFILIATIONS: {char_data['affiliations']}
PERSONALITY: {char_data['personality']}
"""
        
        # Update stored data
        self.campaign_context["characters"][user_id] = character_description
        self.campaign_context["players"][user_id]["character_description"] = character_description
        
        # Record progression in database
        if DATABASE_AVAILABLE:
            try:
                progression = self.character_ops.record_character_progression(
                    user_id=user_id,
                    character_name=character_name,
                    new_level=new_level,
                    old_level=old_level,
                    progression_type="level_up",
                    reason=reason or "Character advancement",
                    episode_id=episode_id,
                    experience_gained=0  # Could be enhanced to track XP
                )
                
                # Create level-up snapshot
                self.character_ops.create_character_snapshot(
                    episode_id=episode_id,
                    user_id=user_id,
                    character_name=character_name,
                    character_data=char_data,
                    snapshot_type="level_up",
                    notes=f"Level {old_level} → {new_level}: {reason or 'Character advancement'}"
                )
                
                print(f"✅ Recorded level up: {character_name} {old_level} → {new_level}")
                
            except Exception as e:
                print(f"Error recording progression: {e}")
        
        # Create celebration embed
        embed = discord.Embed(
            title=f"🎉 {character_name} Levels Up!",
            description=f"**Level {old_level} → Level {new_level}**",
            color=0xFFD700
        )
        
        # Calculate level difference for extra celebration
        level_gain = new_level - old_level
        if level_gain > 1:
            embed.description = f"**{level_gain} Level Jump!** Level {old_level} → Level {new_level}"
        
        embed.add_field(
            name=f"⚔️ {char_data['race']} {char_data['class']}",
            value=f"**Player:** {player_data['player_name']}\n**Background:** {char_data['background']}",
            inline=False
        )
        
        if reason:
            embed.add_field(
                name="📈 Advancement Reason",
                value=reason,
                inline=False
            )
        
        if episode_number:
            embed.add_field(
                name="📺 Episode Progress", 
                value=f"Level gained during Episode {episode_number}",
                inline=True
            )
        
        if DATABASE_AVAILABLE:
            embed.add_field(
                name="💾 Progress Tracked",
                value="✅ Progression recorded\n✅ Character snapshot saved",
                inline=True
            )
        
        # Add level milestone messages
        milestone_messages = {
            5: "🎯 Tier 1 Complete! Ready for greater challenges!",
            10: "⚡ Tier 2 Achieved! True heroism begins!",
            15: "🌟 Tier 3 Reached! Legendary adventures await!",
            20: "👑 Maximum Level! You are now a legend!"
        }
        
        if new_level in milestone_messages:
            embed.add_field(
                name="🏆 Milestone Achievement",
                value=milestone_messages[new_level],
                inline=False
            )
        
        embed.set_footer(text=f"Level up recorded • {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        
        await interaction.response.send_message(embed=embed)
        
        # Voice celebration
        voice_will_speak = (interaction.guild.id in self.voice_clients and 
                           self.voice_clients[interaction.guild.id].is_connected() and 
                           self.tts_enabled.get(interaction.guild.id, False))
        
        if voice_will_speak:
            celebration_msg = f"Congratulations, {character_name}! You have advanced to level {new_level}! "
            
            if level_gain > 1:
                celebration_msg += f"An incredible {level_gain} level advancement! "
            
            if new_level in milestone_messages:
                celebration_msg += milestone_messages[new_level].replace("🎯 ", "").replace("⚡ ", "").replace("🌟 ", "").replace("👑 ", "")
            else:
                celebration_msg += "Your growing power will serve you well in the challenges ahead!"
            
            await self.add_to_voice_queue(interaction.guild.id, celebration_msg, "Level Up")
    
    async def _character_progression_command(self, interaction: discord.Interaction, player: Optional[discord.Member]):
        """View character progression history"""
        target_user = player or interaction.user
        user_id = str(target_user.id)
        
        # Check if character exists
        if user_id not in self.campaign_context["players"]:
            embed = discord.Embed(
                title="🎭 Character Not Found",
                description=f"No character registered for {target_user.display_name}.",
                color=0xFF6B6B
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        char_data = self.campaign_context["players"][user_id]["character_data"]
        character_name = char_data["name"]
        
        embed = discord.Embed(
            title=f"📈 {character_name}'s Progression",
            description=f"Character advancement history for {target_user.display_name}",
            color=0x4169E1
        )
        
        # Current stats
        embed.add_field(
            name="📊 Current Status",
            value=f"**Level:** {char_data['level']}\n**Class:** {char_data['race']} {char_data['class']}\n**Background:** {char_data['background']}",
            inline=False
        )
        
        # Database progression history
        if DATABASE_AVAILABLE:
            try:
                progressions = self.character_ops.get_character_progression_history(user_id)
                
                if progressions:
                    history_text = []
                    for prog in progressions[-5:]:  # Last 5 progressions
                        level_change = f"Level {prog.old_level} → {prog.new_level}" if prog.old_level else f"Level {prog.new_level}"
                        date_str = prog.timestamp.strftime("%Y-%m-%d") if prog.timestamp else "Unknown"
                        history_text.append(f"**{date_str}:** {level_change}\n*{prog.reason or 'No reason given'}*")
                    
                    embed.add_field(
                        name="📜 Recent Progression History",
                        value="\n\n".join(history_text) if history_text else "No progression recorded yet",
                        inline=False
                    )
                    
                    if len(progressions) > 5:
                        embed.set_footer(text=f"Showing last 5 of {len(progressions)} progression records")
                else:
                    embed.add_field(
                        name="📜 Progression History",
                        value="No level progressions recorded yet.",
                        inline=False
                    )
                    
            except Exception as e:
                embed.add_field(
                    name="⚠️ Database Error",
                    value=f"Could not load progression history: {str(e)}",
                    inline=False
                )
        else:
            embed.add_field(
                name="💾 Database Required",
                value="Progression tracking requires database functionality.",
                inline=False
            )
        
        await interaction.response.send_message(embed=embed)
    
    async def _party_progression_command(self, interaction: discord.Interaction):
        """View entire party progression"""
        if not self.campaign_context.get("players"):
            embed = discord.Embed(
                title="🎭 No Party Members",
                description="No characters have been registered yet!",
                color=0xFF6B6B
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        embed = discord.Embed(
            title="🗡️ Party Progression Overview",
            description="Character advancement across all party members",
            color=0x8A2BE2
        )
        
        # Current party levels
        party_info = []
        total_levels = 0
        for user_id, player_data in self.campaign_context["players"].items():
            char_data = player_data["character_data"]
            level = char_data.get("level", 1)
            total_levels += level
            party_info.append(f"**{char_data['name']}** (Level {level}) - {player_data['player_name']}")
        
        avg_level = total_levels / len(self.campaign_context["players"])
        
        embed.add_field(
            name="🎭 Current Party",
            value="\n".join(party_info),
            inline=False
        )
        
        embed.add_field(
            name="📊 Party Stats",
            value=f"**Average Level:** {avg_level:.1f}\n**Total Levels:** {total_levels}\n**Party Size:** {len(self.campaign_context['players'])}",
            inline=True
        )
        
        # Episode-based progression (if database available)
        if DATABASE_AVAILABLE:
            try:
                guild_id = str(interaction.guild.id)
                current_episode = self.episode_ops.get_current_episode(guild_id)
                
                if current_episode:
                    embed.add_field(
                        name="📺 Current Episode",
                        value=f"Episode {current_episode.episode_number}: {current_episode.name}",
                        inline=True
                    )
                
            except Exception as e:
                print(f"Error getting episode info: {e}")
        
        await interaction.response.send_message(embed=embed)
    
    async def _character_snapshot_command(self, interaction: discord.Interaction, notes: Optional[str]):
        """Create manual character snapshot"""
        user_id = str(interaction.user.id)
        
        # Check if character exists
        if user_id not in self.campaign_context["players"]:
            embed = discord.Embed(
                title="🎭 Character Not Registered",
                description="Please register your character first using `/character`!",
                color=0xFF6B6B
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        char_data = self.campaign_context["players"][user_id]["character_data"]
        character_name = char_data["name"]
        
        # Get current episode
        episode_id = None
        if DATABASE_AVAILABLE:
            try:
                guild_id = str(interaction.guild.id)
                current_episode = self.episode_ops.get_current_episode(guild_id)
                if current_episode:
                    episode_id = current_episode.id
            except Exception as e:
                print(f"Error getting episode for snapshot: {e}")
        
        # Create snapshot
        if DATABASE_AVAILABLE:
            try:
                snapshot = self.character_ops.create_character_snapshot(
                    episode_id=episode_id,
                    user_id=user_id,
                    character_name=character_name,
                    character_data=char_data,
                    snapshot_type="manual",
                    notes=notes or "Manual snapshot"
                )
                
                embed = discord.Embed(
                    title="📸 Character Snapshot Created",
                    description=f"Snapshot saved for **{character_name}**",
                    color=0x32CD32
                )
                
                embed.add_field(
                    name="📊 Captured State",
                    value=f"**Level:** {char_data['level']}\n**Class:** {char_data['race']} {char_data['class']}",
                    inline=True
                )
                
                if notes:
                    embed.add_field(
                        name="📝 Notes",
                        value=notes,
                        inline=False
                    )
                
                embed.set_footer(text=f"Snapshot ID: {snapshot.id}")
                
            except Exception as e:
                embed = discord.Embed(
                    title="❌ Snapshot Failed",
                    description=f"Could not create snapshot: {str(e)}",
                    color=0xFF6B6B
                )
        else:
            embed = discord.Embed(
                title="💾 Database Required",
                description="Character snapshots require database functionality.",
                color=0xFFD700
            )
        
        await interaction.response.send_message(embed=embed)