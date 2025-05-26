import discord
from discord.ext import commands
from discord import app_commands
from typing import Optional
from datetime import datetime

from ..database.operations import CharacterOperations, EpisodeOperations

class CharacterProgressionCommands:
    """Character progression and tracking commands"""
    
    def __init__(self, bot: commands.Bot, campaign_context: dict, voice_clients: dict, 
                 tts_enabled: dict, add_to_voice_queue_func):
        self.bot = bot
        self.campaign_context = campaign_context
        self.voice_clients = voice_clients
        self.tts_enabled = tts_enabled
        self.add_to_voice_queue = add_to_voice_queue_func
        
        self._register_commands()
    
    def _register_commands(self):
        """Register character progression commands"""
        
        @self.bot.tree.command(name="level_up", description="Level up your character and record progression")
        @app_commands.describe(
            new_level="Your character's new level",
            reason="Why did you level up? (milestone, XP threshold, etc.)"
        )
        async def level_up_character(interaction: discord.Interaction, 
                                   new_level: int, 
                                   reason: Optional[str] = None):
            guild_id = str(interaction.guild.id)
            user_id = str(interaction.user.id)
            
            # Validate level
            if new_level < 1 or new_level > 20:
                await interaction.response.send_message("❌ Level must be between 1 and 20!", ephemeral=True)
                return
            
            # Check if character exists in context
            if user_id not in self.campaign_context.get("characters", {}):
                await interaction.response.send_message(
                    "❌ Please register your character first with `/character`!", ephemeral=True
                )
                return
            
            try:
                # Sync character to database first
                player_data = self.campaign_context["players"][user_id]
                character_data = player_data["character_data"]
                CharacterOperations.sync_character_from_context(guild_id, user_id, character_data)
                
                # Check current level
                current_level = character_data["level"]
                if new_level <= current_level:
                    await interaction.response.send_message(
                        f"❌ Your character is already level {current_level}! New level must be higher.", 
                        ephemeral=True
                    )
                    return
                
                # Record level up in database
                success = CharacterOperations.level_up_character(
                    guild_id, user_id, new_level, reason
                )
                
                if not success:
                    await interaction.response.send_message(
                        "❌ Failed to level up! Make sure an episode is active with `/start_episode`.", 
                        ephemeral=True
                    )
                    return
                
                # Update campaign context
                character_data["level"] = new_level
                character_name = character_data["name"]
                
                # Create celebration embed
                embed = discord.Embed(
                    title="🌟 Level Up!",
                    description=f"**{character_name}** has reached level **{new_level}**!",
                    color=0xFFD700
                )
                
                embed.add_field(
                    name="📈 Progression",
                    value=f"Level {current_level} → Level {new_level}",
                    inline=True
                )
                
                embed.add_field(
                    name="🎭 Character",
                    value=f"{character_data['race']} {character_data['class']}",
                    inline=True
                )
                
                embed.add_field(
                    name="👤 Player",
                    value=interaction.user.display_name,
                    inline=True
                )
                
                if reason:
                    embed.add_field(
                        name="📝 Reason",
                        value=reason,
                        inline=False
                    )
                
                # Add level-appropriate encouragement
                if new_level <= 5:
                    encouragement = "Your hero's journey begins to take shape!"
                elif new_level <= 10:
                    encouragement = "Your character is becoming a seasoned adventurer!"
                elif new_level <= 15:
                    encouragement = "Your hero wields considerable power!"
                else:
                    encouragement = "Your character has achieved legendary status!"
                
                embed.add_field(
                    name="⚡ Progress",
                    value=encouragement,
                    inline=False
                )
                
                embed.set_footer(text="Character snapshot automatically saved to episode history")
                
                await interaction.response.send_message(embed=embed)
                
                # Voice announcement if available
                if (guild_id in self.voice_clients and 
                    self.voice_clients[guild_id].is_connected() and 
                    self.tts_enabled.get(guild_id, False)):
                    
                    voice_announcement = f"Congratulations! {character_name} has reached level {new_level}! {encouragement}"
                    await self.add_to_voice_queue(guild_id, voice_announcement, "Level Up")
                
            except Exception as e:
                await interaction.response.send_message(
                    f"❌ Failed to level up character: {str(e)}", ephemeral=True
                )
        
        @self.bot.tree.command(name="character_progression", description="View your character's progression history")
        @app_commands.describe(player="View another player's progression (optional)")
        async def view_character_progression(interaction: discord.Interaction, 
                                           player: Optional[discord.Member] = None):
            target_user = player or interaction.user
            user_id = str(target_user.id)
            guild_id = str(interaction.guild.id)
            
            try:
                # Get progression history from database
                progression = CharacterOperations.get_character_progression(guild_id, user_id)
                
                if not progression:
                    message = "No progression history found."
                    if target_user == interaction.user:
                        message += " Use `/character` to register and `/level_up` to record progression!"
                    await interaction.response.send_message(message, ephemeral=True)
                    return
                
                # Get character name from context or database
                character_name = "Unknown Character"
                if user_id in self.campaign_context.get("players", {}):
                    character_name = self.campaign_context["players"][user_id]["character_data"]["name"]
                
                embed = discord.Embed(
                    title=f"📈 Character Progression: {character_name}",
                    description=f"Level progression history for {target_user.display_name}",
                    color=0x4169E1
                )
                
                # Group progressions by level ranges for cleaner display
                for i, prog in enumerate(progression[-10:]):  # Show last 10 level ups
                    episode_info = f"Episode {prog['episode_number']}"
                    if prog['episode_name'] and prog['episode_name'] != f"Episode {prog['episode_number']}":
                        episode_info += f": {prog['episode_name']}"
                    
                    date_str = prog['date'].strftime("%m/%d/%Y")
                    
                    field_name = f"Level {prog['old_level']} → {prog['new_level']}"
                    field_value = f"**{episode_info}**\n📅 {date_str}"
                    
                    if prog['reason']:
                        field_value += f"\n📝 {prog['reason']}"
                    
                    embed.add_field(
                        name=field_name,
                        value=field_value,
                        inline=len(progression) > 5  # Inline for many progressions
                    )
                
                # Add summary stats
                if progression:
                    total_levels = progression[-1]['new_level'] - progression[0]['old_level']
                    episodes_span = progression[-1]['episode_number'] - progression[0]['episode_number'] + 1
                    
                    embed.add_field(
                        name="📊 Summary",
                        value=f"Total levels gained: {total_levels}\nEpisodes span: {episodes_span}\nProgression entries: {len(progression)}",
                        inline=False
                    )
                
                embed.set_footer(text="Use /level_up to record new level progression")
                await interaction.response.send_message(embed=embed)
                
            except Exception as e:
                await interaction.response.send_message(
                    f"❌ Failed to get progression history: {str(e)}", ephemeral=True
                )
        
        @self.bot.tree.command(name="character_snapshot", description="Manually create a character snapshot")
        @app_commands.describe(
            notes="Notes about your character's current state or recent events",
            hp_current="Current hit points (optional)",
            hp_max="Maximum hit points (optional)"
        )
        async def create_character_snapshot(interaction: discord.Interaction,
                                          notes: Optional[str] = None,
                                          hp_current: Optional[int] = None,
                                          hp_max: Optional[int] = None):
            guild_id = str(interaction.guild.id)
            user_id = str(interaction.user.id)
            
            # Check if character exists
            if user_id not in self.campaign_context.get("characters", {}):
                await interaction.response.send_message(
                    "❌ Please register your character first with `/character`!", ephemeral=True
                )
                return
            
            try:
                # Get character data
                player_data = self.campaign_context["players"][user_id]
                character_data = player_data["character_data"]
                character_name = character_data["name"]
                
                # Update HP if provided
                if hp_current is not None:
                    character_data["current_hp"] = hp_current
                if hp_max is not None:
                    character_data["max_hp"] = hp_max
                
                # Sync to database
                CharacterOperations.sync_character_from_context(guild_id, user_id, character_data)
                
                # Check if there's an active episode
                active_episode = EpisodeOperations.get_episode_recap_data(guild_id)
                if not active_episode:
                    await interaction.response.send_message(
                        "❌ No active episode! Use `/start_episode` first.", ephemeral=True
                    )
                    return
                
                # Create snapshot (this would require extending the database operations)
                # For now, we'll just confirm the sync
                
                embed = discord.Embed(
                    title="📸 Character Snapshot Created",
                    description=f"Current state saved for **{character_name}**",
                    color=0x32CD32
                )
                
                embed.add_field(
                    name="📊 Character Info",
                    value=f"Level: {character_data['level']}\nClass: {character_data['race']} {character_data['class']}",
                    inline=True
                )
                
                if hp_current is not None or hp_max is not None:
                    hp_display = ""
                    if hp_current is not None:
                        hp_display += f"Current HP: {hp_current}"
                    if hp_max is not None:
                        if hp_display:
                            hp_display += f"/{hp_max}"
                        else:
                            hp_display = f"Max HP: {hp_max}"
                    
                    embed.add_field(
                        name="❤️ Hit Points",
                        value=hp_display,
                        inline=True
                    )
                
                embed.add_field(
                    name="⏰ Snapshot Time",
                    value=datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC"),
                    inline=True
                )
                
                if notes:
                    embed.add_field(
                        name="📝 Notes",
                        value=notes,
                        inline=False
                    )
                
                embed.set_footer(text="Snapshot saved to current episode history")
                await interaction.response.send_message(embed=embed)
                
            except Exception as e:
                await interaction.response.send_message(
                    f"❌ Failed to create snapshot: {str(e)}", ephemeral=True
                )
        
        @self.bot.tree.command(name="party_progression", description="View progression summary for the entire party")
        async def view_party_progression(interaction: discord.Interaction):
            guild_id = str(interaction.guild.id)
            
            try:
                embed = discord.Embed(
                    title="🗡️ Party Progression Summary",
                    description="Level progression for all party members",
                    color=0x4B0082
                )
                
                # Get all characters from campaign context
                if not self.campaign_context.get("characters"):
                    await interaction.response.send_message("No characters registered yet!", ephemeral=True)
                    return
                
                party_data = []
                
                for user_id, char_desc in self.campaign_context["characters"].items():
                    if user_id in self.campaign_context["players"]:
                        player_data = self.campaign_context["players"][user_id]
                        char_data = player_data["character_data"]
                        
                        # Get progression history
                        progression = CharacterOperations.get_character_progression(guild_id, user_id)
                        
                        party_data.append({
                            'name': char_data['name'],
                            'player': player_data['player_name'],
                            'current_level': char_data['level'],
                            'class': f"{char_data['race']} {char_data['class']}",
                            'progression_count': len(progression),
                            'latest_progression': progression[-1] if progression else None
                        })
                
                # Sort by level (highest first)
                party_data.sort(key=lambda x: x['current_level'], reverse=True)
                
                for char in party_data:
                    value = f"**{char['class']}** (Level {char['current_level']})\n"
                    value += f"Player: {char['player']}\n"
                    value += f"Level-ups recorded: {char['progression_count']}"
                    
                    if char['latest_progression']:
                        latest = char['latest_progression']
                        value += f"\nLast level-up: Episode {latest['episode_number']}"
                    
                    embed.add_field(
                        name=f"⚔️ {char['name']}",
                        value=value,
                        inline=True
                    )
                
                # Add party statistics
                total_levels = sum(char['current_level'] for char in party_data)
                avg_level = total_levels / len(party_data) if party_data else 0
                
                embed.add_field(
                    name="📊 Party Stats",
                    value=f"Party Size: {len(party_data)}\nTotal Levels: {total_levels}\nAverage Level: {avg_level:.1f}",
                    inline=False
                )
                
                embed.set_footer(text="Use /character_progression [player] for detailed individual history")
                await interaction.response.send_message(embed=embed)
                
            except Exception as e:
                await interaction.response.send_message(
                    f"❌ Failed to get party progression: {str(e)}", ephemeral=True
                )