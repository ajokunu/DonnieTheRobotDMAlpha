# character_system/dnd5e_2024.py
"""
D&D 5th Edition 2024 Character System
Complete implementation following 2024 Player's Handbook rules
"""

import discord
from discord import app_commands
from discord.ext import commands
import random
from typing import Optional, Dict, List, Any

from .species_2024 import SPECIES_2024
from .backgrounds_2024 import BACKGROUNDS_2024
from .classes_2024 import CLASSES_2024, get_class_spell_slots_2024

class DnD5e2024CharacterSystem:
    """Complete D&D 5e 2024 character management system"""
    
    def __init__(self, bot, campaign_context, claude_client):
        self.bot = bot
        self.campaign_context = campaign_context
        self.claude_client = claude_client
        self.setup_commands()
    
    def setup_commands(self):
        """Register all character-related commands"""
        
        # Main character registration
        @self.bot.tree.command(name="character", description="Register your character for D&D 5e 2024 campaign")
        @app_commands.describe(
            name="Your character's name",
            species="Character species (Human, Elf, Dwarf, etc.) - 2024 terminology",
            character_class="Character class (Fighter, Wizard, Rogue, etc.)",
            level="Character level (1-20)",
            background="Character background (Acolyte, Criminal, Folk Hero, etc.)",
            strength="Strength score (8-20)",
            dexterity="Dexterity score (8-20)",
            constitution="Constitution score (8-20)",
            intelligence="Intelligence score (8-20)",
            wisdom="Wisdom score (8-20)",
            charisma="Charisma score (8-20)"
        )
        async def register_character_2024(interaction: discord.Interaction, 
                               name: str,
                               species: str,
                               character_class: str,
                               level: int,
                               background: Optional[str] = None,
                               strength: Optional[int] = None,
                               dexterity: Optional[int] = None,
                               constitution: Optional[int] = None,
                               intelligence: Optional[int] = None,
                               wisdom: Optional[int] = None,
                               charisma: Optional[int] = None):
            await self._register_character(interaction, name, species, character_class, level,
                                         background, strength, dexterity, constitution,
                                         intelligence, wisdom, charisma)
        
        # Character details
        @self.bot.tree.command(name="character_details", description="Set personality, appearance, and roleplay details")
        @app_commands.describe(
            personality="Character personality traits",
            ideals="What drives your character",
            bonds="Important connections and relationships",
            flaws="Character weaknesses or quirks",
            backstory="Character's background story",
            appearance="Physical appearance description"
        )
        async def character_details(interaction: discord.Interaction,
                                  personality: Optional[str] = None,
                                  ideals: Optional[str] = None,
                                  bonds: Optional[str] = None,
                                  flaws: Optional[str] = None,
                                  backstory: Optional[str] = None,
                                  appearance: Optional[str] = None):
            await self._set_character_details(interaction, personality, ideals, bonds, flaws, backstory, appearance)
        
        # HP Management
        @self.bot.tree.command(name="manage_hp", description="Manage hit points (damage, healing, rests)")
        @app_commands.describe(
            action="What to do with HP",
            amount="Amount of HP to change",
            temporary="Temporary HP to add (optional)"
        )
        @app_commands.choices(action=[
            app_commands.Choice(name="Take Damage", value="damage"),
            app_commands.Choice(name="Heal", value="heal"),
            app_commands.Choice(name="Set Current HP", value="set"),
            app_commands.Choice(name="Add Temporary HP", value="temp"),
            app_commands.Choice(name="Long Rest", value="long_rest"),
            app_commands.Choice(name="Short Rest", value="short_rest")
        ])
        async def manage_hp(interaction: discord.Interaction, action: str, amount: Optional[int] = None, temporary: Optional[int] = None):
            await self._manage_hp(interaction, action, amount, temporary)
        
        # Spell Slot Management
        @self.bot.tree.command(name="manage_spell_slots", description="Manage spell slots (2024 rules)")
        @app_commands.describe(
            action="What to do with spell slots",
            spell_level="Spell slot level (1-9)",
            amount="Number of slots to use/restore"
        )
        @app_commands.choices(action=[
            app_commands.Choice(name="Use Spell Slot", value="use"),
            app_commands.Choice(name="Restore Spell Slot", value="restore"),
            app_commands.Choice(name="Long Rest (Restore All)", value="long_rest"),
            app_commands.Choice(name="View Spell Slots", value="view")
        ])
        async def manage_spell_slots(interaction: discord.Interaction, action: str, 
                                   spell_level: Optional[int] = None, amount: Optional[int] = 1):
            await self._manage_spell_slots(interaction, action, spell_level, amount)
        
        # Ability Checks
        @self.bot.tree.command(name="ability_check", description="Make an ability check or skill check (2024 rules)")
        @app_commands.describe(
            ability="Which ability to use",
            skill="Specific skill (optional)",
            test_type="Normal, Advantage, or Disadvantage",
            modifier="Additional modifier to add"
        )
        @app_commands.choices(
            ability=[
                app_commands.Choice(name="Strength", value="strength"),
                app_commands.Choice(name="Dexterity", value="dexterity"),
                app_commands.Choice(name="Constitution", value="constitution"),
                app_commands.Choice(name="Intelligence", value="intelligence"),
                app_commands.Choice(name="Wisdom", value="wisdom"),
                app_commands.Choice(name="Charisma", value="charisma")
            ],
            skill=[
                app_commands.Choice(name="Athletics", value="athletics"),
                app_commands.Choice(name="Acrobatics", value="acrobatics"),
                app_commands.Choice(name="Sleight of Hand", value="sleight_of_hand"),
                app_commands.Choice(name="Stealth", value="stealth"),
                app_commands.Choice(name="Arcana", value="arcana"),
                app_commands.Choice(name="History", value="history"),
                app_commands.Choice(name="Investigation", value="investigation"),
                app_commands.Choice(name="Nature", value="nature"),
                app_commands.Choice(name="Religion", value="religion"),
                app_commands.Choice(name="Animal Handling", value="animal_handling"),
                app_commands.Choice(name="Insight", value="insight"),
                app_commands.Choice(name="Medicine", value="medicine"),
                app_commands.Choice(name="Perception", value="perception"),
                app_commands.Choice(name="Survival", value="survival"),
                app_commands.Choice(name="Deception", value="deception"),
                app_commands.Choice(name="Intimidation", value="intimidation"),
                app_commands.Choice(name="Performance", value="performance"),
                app_commands.Choice(name="Persuasion", value="persuasion")
            ],
            test_type=[
                app_commands.Choice(name="Normal", value="normal"),
                app_commands.Choice(name="Advantage", value="advantage"),
                app_commands.Choice(name="Disadvantage", value="disadvantage")
            ]
        )
        async def ability_check(interaction: discord.Interaction, ability: str, 
                              skill: Optional[str] = None, test_type: Optional[str] = "normal",
                              modifier: Optional[int] = 0):
            await self._ability_check(interaction, ability, skill, test_type, modifier)
        
        # Saving Throws
        @self.bot.tree.command(name="saving_throw", description="Make a saving throw (2024 rules)")
        @app_commands.describe(
            ability="Which saving throw to make",
            test_type="Normal, Advantage, or Disadvantage",
            modifier="Additional modifier to add"
        )
        @app_commands.choices(
            ability=[
                app_commands.Choice(name="Strength", value="strength"),
                app_commands.Choice(name="Dexterity", value="dexterity"),
                app_commands.Choice(name="Constitution", value="constitution"),
                app_commands.Choice(name="Intelligence", value="intelligence"),
                app_commands.Choice(name="Wisdom", value="wisdom"),
                app_commands.Choice(name="Charisma", value="charisma")
            ],
            test_type=[
                app_commands.Choice(name="Normal", value="normal"),
                app_commands.Choice(name="Advantage", value="advantage"),
                app_commands.Choice(name="Disadvantage", value="disadvantage")
            ]
        )
        async def saving_throw(interaction: discord.Interaction, ability: str,
                             test_type: Optional[str] = "normal", modifier: Optional[int] = 0):
            await self._saving_throw(interaction, ability, test_type, modifier)
        
        # Character Sheet Display
        @self.bot.tree.command(name="character_sheet_2024", description="View complete D&D 5e 2024 character sheet")
        @app_commands.describe(player="View another player's character (optional)")
        async def character_sheet_2024(interaction: discord.Interaction, player: Optional[discord.Member] = None):
            await self._view_character_sheet_2024(interaction, player)

    # === HELPER METHODS ===
    
    @staticmethod
    def calculate_proficiency_bonus(level: int) -> int:
        """Calculate proficiency bonus based on 2024 rules"""
        return 2 + ((level - 1) // 4)
    
    @staticmethod
    def calculate_ability_modifier(score: int) -> int:
        """Calculate ability modifier from score"""
        return (score - 10) // 2
    
    def get_species_traits(self, species: str) -> List[str]:
        """Get species traits for 2024 rules"""
        species_data = SPECIES_2024.get(species.lower(), {})
        traits_dict = species_data.get("traits", {})
        return list(traits_dict.keys())
    
    def get_class_features(self, character_class: str, level: int) -> List[str]:
        """Get class features for specific level (2024 rules)"""
        class_data = CLASSES_2024.get(character_class.lower(), {})
        features_dict = class_data.get("features", {})
        
        features = []
        for feature_level in sorted(features_dict.keys()):
            if level >= feature_level:
                features.extend(features_dict[feature_level])
        
        return features
    
    def get_saving_throw_proficiencies(self, character_class: str) -> Dict[str, bool]:
        """Get saving throw proficiencies based on 2024 class data"""
        class_data = CLASSES_2024.get(character_class.lower(), {})
        proficient_saves = class_data.get("saving_throw_proficiencies", [])
        
        saves = {
            "strength": False, "dexterity": False, "constitution": False,
            "intelligence": False, "wisdom": False, "charisma": False
        }
        
        for save in proficient_saves:
            saves[save.lower()] = True
        
        return saves
    
    def get_skill_proficiencies(self, background: str) -> Dict[str, bool]:
        """Get skill proficiencies from background (2024 rules)"""
        background_data = BACKGROUNDS_2024.get(background.lower().replace(" ", "_"), {})
        granted_skills = background_data.get("skill_proficiencies", [])
        
        skills = {
            "athletics": False, "acrobatics": False, "sleight_of_hand": False, "stealth": False,
            "arcana": False, "history": False, "investigation": False, "nature": False, "religion": False,
            "animal_handling": False, "insight": False, "medicine": False, "perception": False, "survival": False,
            "deception": False, "intimidation": False, "performance": False, "persuasion": False
        }
        
        for skill in granted_skills:
            skill_key = skill.lower().replace(" ", "_")
            if skill_key in skills:
                skills[skill_key] = True
        
        return skills
    
    # === COMMAND IMPLEMENTATIONS ===
    
    async def _register_character(self, interaction, name, species, character_class, level,
                                background, strength, dexterity, constitution, intelligence, wisdom, charisma):
        """Register a character with 2024 rules"""
        user_id = str(interaction.user.id)
        player_name = interaction.user.display_name
        
        # Set guild_id in campaign context if not set
        if self.campaign_context["guild_id"] is None:
            self.campaign_context["guild_id"] = str(interaction.guild.id)
        
        # Validate inputs
        if level < 1 or level > 20:
            await interaction.response.send_message("❌ Character level must be between 1 and 20!", ephemeral=True)
            return
        
        # Handle ability scores
        ability_scores = {
            "strength": strength or 10,
            "dexterity": dexterity or 10, 
            "constitution": constitution or 10,
            "intelligence": intelligence or 10,
            "wisdom": wisdom or 10,
            "charisma": charisma or 10
        }
        
        # Validate ability scores
        for ability, score in ability_scores.items():
            if score < 3 or score > 20:
                await interaction.response.send_message(f"❌ {ability.title()} score must be between 3 and 20!", ephemeral=True)
                return
        
        # Build 2024 character profile
        character_profile = self._create_2024_character_profile(
            name, species, character_class, level, background or "Folk Hero",
            ability_scores, player_name, user_id
        )
        
        # Store character data
        character_description = self._create_character_description_2024(character_profile)
        self.campaign_context["characters"][user_id] = character_description
        self.campaign_context["players"][user_id] = {
            "user_id": user_id,
            "player_name": player_name,
            "character_data": character_profile,
            "character_description": character_description
        }
        
        # Create response embed
        embed = self._create_registration_embed_2024(character_profile, player_name)
        await interaction.response.send_message(embed=embed)
    
    def _create_2024_character_profile(self, name, species, character_class, level, background, 
                                     ability_scores, player_name, user_id):
        """Create complete 2024 character profile"""
        class_data = CLASSES_2024.get(character_class.lower(), {})
        species_data = SPECIES_2024.get(species.lower(), {})
        
        # Calculate derived stats
        con_mod = self.calculate_ability_modifier(ability_scores["constitution"])
        proficiency_bonus = self.calculate_proficiency_bonus(level)
        
        # Calculate HP (2024 rules)
        hit_die = class_data.get("hit_die", 8)
        max_hp = hit_die + con_mod  # 1st level
        if level > 1:
            # Average HP gain per level after 1st
            avg_hp_per_level = (hit_die // 2) + 1 + con_mod
            max_hp += avg_hp_per_level * (level - 1)
        
        # Get spellcasting ability
        spellcasting_ability = class_data.get("spellcasting_ability", None)
        
        # Calculate spell save DC and attack bonus
        spell_save_dc = 8
        spell_attack_bonus = 0
        if spellcasting_ability:
            spell_mod = self.calculate_ability_modifier(ability_scores[spellcasting_ability])
            spell_save_dc = 8 + proficiency_bonus + spell_mod
            spell_attack_bonus = proficiency_bonus + spell_mod
        
        return {
            # === BASIC INFO ===
            "name": name,
            "species": species,  # 2024 terminology
            "class": character_class,
            "level": level,
            "background": background,
            "player_name": player_name,
            "discord_user_id": user_id,
            
            # === ABILITY SCORES ===
            "ability_scores": ability_scores,
            
            # === DERIVED STATS ===
            "proficiency_bonus": proficiency_bonus,
            "armor_class": 10 + self.calculate_ability_modifier(ability_scores["dexterity"]),
            "hit_points": {
                "maximum": max_hp,
                "current": max_hp,
                "temporary": 0
            },
            "hit_dice": f"{level}d{hit_die}",
            "speed": species_data.get("speed", 30),
            
            # === PROFICIENCIES ===
            "saving_throws": self.get_saving_throw_proficiencies(character_class),
            "skills": self.get_skill_proficiencies(background),
            "armor_proficiencies": class_data.get("armor_proficiencies", []),
            "weapon_proficiencies": class_data.get("weapon_proficiencies", []),
            
            # === SPELLCASTING (2024 rules) ===
            "spellcasting": {
                "ability": spellcasting_ability,
                "spell_save_dc": spell_save_dc,
                "spell_attack_bonus": spell_attack_bonus,
                "spell_slots": get_class_spell_slots_2024(character_class, level),
                "ritual_casting": class_data.get("ritual_casting", False)
            },
            
            # === FEATURES & TRAITS ===
            "species_traits": self.get_species_traits(species),
            "class_features": self.get_class_features(character_class, level),
            "background_feature": self._get_background_feature_2024(background),
            
            # === EQUIPMENT ===
            "equipment": {
                "armor": class_data.get("equipment", {}).get("armor", "None"),
                "weapons": class_data.get("equipment", {}).get("weapons", []),
                "tools": class_data.get("equipment", {}).get("tools", []),
                "other": class_data.get("equipment", {}).get("other", "Adventurer's Pack"),
                "money": {"cp": 0, "sp": 0, "ep": 0, "gp": 0, "pp": 0}
            },
            
            # === LANGUAGES ===
            "languages": species_data.get("languages", ["Common"]),
            
            # === ROLEPLAY ===
            "personality": "To be determined",
            "ideals": "",
            "bonds": "",
            "flaws": "",
            "backstory": "",
            "appearance": "",
            
            # === TRACKING ===
            "spell_slots_used": {"1st": 0, "2nd": 0, "3rd": 0, "4th": 0, "5th": 0, "6th": 0, "7th": 0, "8th": 0, "9th": 0},
            "inspiration": False,  # 2024 Inspiration mechanic
            "exhaustion_level": 0  # 2024 Exhaustion levels (0-6)
        }
    
    def _get_background_feature_2024(self, background):
        """Get background feature based on 2024 rules"""
        background_data = BACKGROUNDS_2024.get(background.lower().replace(" ", "_"), {})
        return background_data.get("feature", "Background Feature")
    
    def _create_character_description_2024(self, character_profile):
        """Create formatted character description for Claude AI (2024 format)"""
        cp = character_profile
        
        # Calculate ability modifiers
        ability_mods = {}
        for ability, score in cp["ability_scores"].items():
            ability_mods[ability] = self.calculate_ability_modifier(score)
        
        return f"""
D&D 5E 2024 CHARACTER: {cp['name']}
PLAYER: {cp['player_name']} (Discord ID: {cp['discord_user_id']})
SPECIES & CLASS: {cp['species']} {cp['class']} (Level {cp['level']})
BACKGROUND: {cp['background']}

ABILITY SCORES (2024):
STR {cp['ability_scores']['strength']} ({ability_mods['strength']:+d})
DEX {cp['ability_scores']['dexterity']} ({ability_mods['dexterity']:+d})
CON {cp['ability_scores']['constitution']} ({ability_mods['constitution']:+d})
INT {cp['ability_scores']['intelligence']} ({ability_mods['intelligence']:+d})
WIS {cp['ability_scores']['wisdom']} ({ability_mods['wisdom']:+d})
CHA {cp['ability_scores']['charisma']} ({ability_mods['charisma']:+d})

COMBAT STATS (2024):
AC: {cp['armor_class']} | HP: {cp['hit_points']['current']}/{cp['hit_points']['maximum']} | Speed: {cp['speed']} ft
Hit Dice: {cp['hit_dice']} | Proficiency Bonus: +{cp['proficiency_bonus']}

PROFICIENCIES (2024):
Saving Throws: {', '.join([save.title() for save, prof in cp['saving_throws'].items() if prof])}
Skills: {', '.join([skill.replace('_', ' ').title() for skill, prof in cp['skills'].items() if prof])}

SPELLCASTING (2024):
{f"Ability: {cp['spellcasting']['ability'].title()}" if cp['spellcasting']['ability'] else "Non-spellcaster"}
{f"Spell Save DC: {cp['spellcasting']['spell_save_dc']}" if cp['spellcasting']['ability'] else ""}
{f"Spell Attack: +{cp['spellcasting']['spell_attack_bonus']}" if cp['spellcasting']['ability'] else ""}

FEATURES & TRAITS (2024):
Species Traits: {', '.join(cp['species_traits']) if cp['species_traits'] else 'Standard'}
Class Features: {', '.join(cp['class_features']) if cp['class_features'] else 'Standard'}
Background Feature: {cp['background_feature']}

PERSONALITY & ROLEPLAY:
Personality: {cp['personality']}
Backstory: {cp['backstory'] if cp['backstory'] else 'To be developed'}
"""
    
    def _create_registration_embed_2024(self, character_profile, player_name):
        """Create character registration embed for 2024"""
        cp = character_profile
        
        embed = discord.Embed(
            title="🎭 D&D 5e 2024 Character Registered!",
            description=f"**{cp['species']} {cp['class']}** (Level {cp['level']})\n*{cp['background']}*",
            color=0x32CD32
        )
        
        # Ability scores with modifiers
        abilities = []
        for ability, score in cp["ability_scores"].items():
            modifier = self.calculate_ability_modifier(score)
            abilities.append(f"{ability[:3].upper()} {score} ({modifier:+d})")
        
        embed.add_field(
            name="📊 Ability Scores (2024)", 
            value=" | ".join(abilities[:3]) + "\n" + " | ".join(abilities[3:]),
            inline=False
        )
        
        # Combat stats
        embed.add_field(
            name="⚔️ Combat Stats",
            value=f"**AC:** {cp['armor_class']} | **HP:** {cp['hit_points']['maximum']} | **Speed:** {cp['speed']} ft\n**Proficiency:** +{cp['proficiency_bonus']} | **Hit Dice:** {cp['hit_dice']}",
            inline=False
        )
        
        # Spellcasting (if applicable)
        if cp['spellcasting']['ability']:
            embed.add_field(
                name="✨ Spellcasting (2024)",
                value=f"**Ability:** {cp['spellcasting']['ability'].title()}\n**Save DC:** {cp['spellcasting']['spell_save_dc']} | **Attack:** +{cp['spellcasting']['spell_attack_bonus']}",
                inline=True
            )
        
        # Species traits
        if cp['species_traits']:
            traits_text = ', '.join(cp['species_traits'][:3])  # Show first 3
            if len(cp['species_traits']) > 3:
                traits_text += f" + {len(cp['species_traits']) - 3} more"
            embed.add_field(name=f"🧬 {cp['species'].title()} Traits", value=traits_text, inline=True)
        
        embed.add_field(
            name="⚡ Next Steps (2024)",
            value="Use `/character_details` for personality & appearance\nUse `/character_sheet_2024` for complete sheet\nStart playing with `/action`!",
            inline=False
        )
        
        embed.set_footer(text=f"D&D 5e 2024 Rules • Player: {player_name}")
        return embed
    
    # Additional command implementations...
    async def _set_character_details(self, interaction, personality, ideals, bonds, flaws, backstory, appearance):
        """Set character roleplay details"""
        user_id = str(interaction.user.id)
        
        if user_id not in self.campaign_context["characters"]:
            await interaction.response.send_message("❌ No character registered! Use `/character` first.", ephemeral=True)
            return
        
        char_data = self.campaign_context["players"][user_id]["character_data"]
        updates = []
        
        if personality:
            char_data["personality"] = personality
            updates.append("Personality")
        if ideals:
            char_data["ideals"] = ideals
            updates.append("Ideals")
        if bonds:
            char_data["bonds"] = bonds
            updates.append("Bonds")
        if flaws:
            char_data["flaws"] = flaws
            updates.append("Flaws")
        if backstory:
            char_data["backstory"] = backstory
            updates.append("Backstory")
        if appearance:
            char_data["appearance"] = appearance
            updates.append("Appearance")
        
        if not updates:
            await interaction.response.send_message("❌ Please provide at least one detail to update!", ephemeral=True)
            return
        
        # Update character description
        character_description = self._create_character_description_2024(char_data)
        self.campaign_context["characters"][user_id] = character_description
        self.campaign_context["players"][user_id]["character_description"] = character_description
        
        embed = discord.Embed(
            title=f"✅ {char_data['name']} Details Updated!",
            description=f"Updated: {', '.join(updates)}",
            color=0x32CD32
        )
        
        await interaction.response.send_message(embed=embed)

    async def _manage_hp(self, interaction, action, amount, temporary):
        """Manage hit points with 2024 rules"""
        user_id = str(interaction.user.id)
        
        if user_id not in self.campaign_context["characters"]:
            await interaction.response.send_message("❌ No character registered!", ephemeral=True)
            return
        
        char_data = self.campaign_context["players"][user_id]["character_data"]
        hp = char_data["hit_points"]
        
        old_hp = hp["current"]
        
        if action == "damage":
            if amount is None:
                await interaction.response.send_message("❌ Please specify damage amount!", ephemeral=True)
                return
            
            # Apply damage (temp HP first, then regular HP)
            remaining_damage = amount
            if hp["temporary"] > 0:
                temp_damage = min(remaining_damage, hp["temporary"])
                hp["temporary"] -= temp_damage
                remaining_damage -= temp_damage
            
            if remaining_damage > 0:
                hp["current"] = max(0, hp["current"] - remaining_damage)
        
        elif action == "heal":
            if amount is None:
                await interaction.response.send_message("❌ Please specify heal amount!", ephemeral=True)
                return
            hp["current"] = min(hp["maximum"], hp["current"] + amount)
        
        elif action == "set":
            if amount is None:
                await interaction.response.send_message("❌ Please specify HP amount!", ephemeral=True)
                return
            hp["current"] = max(0, min(hp["maximum"], amount))
        
        elif action == "temp":
            if temporary is None:
                await interaction.response.send_message("❌ Please specify temporary HP amount!", ephemeral=True)
                return
            hp["temporary"] = max(hp["temporary"], temporary)  # Temp HP doesn't stack
        
        elif action == "long_rest":
            hp["current"] = hp["maximum"]
            hp["temporary"] = 0
            # Also restore spell slots
            char_data["spell_slots_used"] = {"1st": 0, "2nd": 0, "3rd": 0, "4th": 0, "5th": 0, "6th": 0, "7th": 0, "8th": 0, "9th": 0}
        
        elif action == "short_rest":
            # 2024 short rest rules
            if amount is None:
                amount = max(1, char_data["level"] // 2)  # Default to half hit dice
            
            hit_die = int(char_data["hit_dice"].split('d')[1])
            con_mod = self.calculate_ability_modifier(char_data["ability_scores"]["constitution"])
            
            # Roll hit dice for healing
            healing = 0
            for _ in range(min(amount, char_data["level"])):
                healing += random.randint(1, hit_die) + con_mod
            
            hp["current"] = min(hp["maximum"], hp["current"] + healing)
            amount = healing  # For display purposes
        
        # Update character description
        character_description = self._create_character_description_2024(char_data)
        self.campaign_context["characters"][user_id] = character_description
        self.campaign_context["players"][user_id]["character_description"] = character_description
        
        # Create response
        embed = discord.Embed(
            title=f"💖 {char_data['name']} - HP Updated",
            color=0x32CD32 if hp["current"] > old_hp else 0xFF6B6B if hp["current"] < old_hp else 0xFFD700
        )
        
        hp_display = f"{hp['current']}/{hp['maximum']}"
        if hp["temporary"] > 0:
            hp_display += f" (+{hp['temporary']} temp)"
        
        embed.add_field(name="Current HP", value=hp_display, inline=True)
        
        if action == "damage":
            embed.add_field(name="Damage Taken", value=f"{amount} damage", inline=True)
        elif action == "heal":
            embed.add_field(name="Healing", value=f"Healed {amount} HP", inline=True)
        elif action == "short_rest":
            embed.add_field(name="Short Rest", value=f"Healed {amount} HP from hit dice", inline=True)
        elif action == "long_rest":
            embed.add_field(name="Long Rest", value="Fully healed! All spell slots restored!", inline=True)
        
        await interaction.response.send_message(embed=embed)

    async def _manage_spell_slots(self, interaction, action, spell_level, amount):
        """Manage spell slots with 2024 progression"""
        user_id = str(interaction.user.id)
        
        if user_id not in self.campaign_context["characters"]:
            await interaction.response.send_message("❌ No character registered!", ephemeral=True)
            return
        
        char_data = self.campaign_context["players"][user_id]["character_data"]
        
        if not char_data["spellcasting"]["ability"]:
            await interaction.response.send_message("❌ Your character is not a spellcaster!", ephemeral=True)
            return
        
        spell_slots = char_data["spellcasting"]["spell_slots"]
        spell_slots_used = char_data["spell_slots_used"]
        
        if action == "view":
            embed = discord.Embed(
                title=f"✨ {char_data['name']} - Spell Slots (2024)",
                color=0x9932CC
            )
            
            slot_display = []
            for level in ["1st", "2nd", "3rd", "4th", "5th", "6th", "7th", "8th", "9th"]:
                total = spell_slots[level]
                used = spell_slots_used[level]
                if total > 0:
                    available = total - used
                    slot_emoji = "🔵" if available == total else "🟡" if available > 0 else "🔴"
                    slot_display.append(f"{slot_emoji} **{level}:** {available}/{total}")
            
            if slot_display:
                embed.add_field(name="Available Spell Slots", value="\n".join(slot_display), inline=False)
            else:
                embed.add_field(name="Spell Slots", value="No spell slots available", inline=False)
            
            embed.add_field(
                name="Spellcasting Info (2024)",
                value=f"**Ability:** {char_data['spellcasting']['ability'].title()}\n**Save DC:** {char_data['spellcasting']['spell_save_dc']}\n**Attack Bonus:** +{char_data['spellcasting']['spell_attack_bonus']}",
                inline=False
            )
            
            await interaction.response.send_message(embed=embed)
            return
        
        if spell_level is None or spell_level < 1 or spell_level > 9:
            await interaction.response.send_message("❌ Please specify a valid spell level (1-9)!", ephemeral=True)
            return
        
        level_key = ["1st", "2nd", "3rd", "4th", "5th", "6th", "7th", "8th", "9th"][spell_level - 1]
        
        if action == "long_rest":
            # Restore all spell slots
            for level in spell_slots_used:
                spell_slots_used[level] = 0
            
            embed = discord.Embed(
                title=f"✨ {char_data['name']} - Long Rest",
                description="All spell slots restored!",
                color=0x32CD32
            )
        
        elif action == "use":
            total_slots = spell_slots[level_key]
            used_slots = spell_slots_used[level_key]
            
            if total_slots == 0:
                await interaction.response.send_message(f"❌ You don't have any {level_key} level spell slots!", ephemeral=True)
                return
            
            if used_slots + amount > total_slots:
                await interaction.response.send_message(f"❌ You don't have {amount} {level_key} level spell slots available!", ephemeral=True)
                return
            
            spell_slots_used[level_key] += amount
            available = total_slots - spell_slots_used[level_key]
            
            embed = discord.Embed(
                title=f"✨ {char_data['name']} - Spell Cast",
                description=f"Used {amount} {level_key} level spell slot{'s' if amount > 1 else ''}",
                color=0xFF6B6B
            )
            embed.add_field(name=f"{level_key.title()} Level Slots", value=f"{available}/{total_slots} remaining", inline=True)
        
        elif action == "restore":
            used_slots = spell_slots_used[level_key]
            
            if used_slots == 0:
                await interaction.response.send_message(f"❌ You haven't used any {level_key} level spell slots!", ephemeral=True)
                return
            
            restore_amount = min(amount, used_slots)
            spell_slots_used[level_key] -= restore_amount
            available = spell_slots[level_key] - spell_slots_used[level_key]
            
            embed = discord.Embed(
                title=f"✨ {char_data['name']} - Spell Slots Restored",
                description=f"Restored {restore_amount} {level_key} level spell slot{'s' if restore_amount > 1 else ''}",
                color=0x32CD32
            )
            embed.add_field(name=f"{level_key.title()} Level Slots", value=f"{available}/{spell_slots[level_key]} available", inline=True)
        
        # Update character description
        character_description = self._create_character_description_2024(char_data)
        self.campaign_context["characters"][user_id] = character_description
        self.campaign_context["players"][user_id]["character_description"] = character_description
        
        await interaction.response.send_message(embed=embed)

    async def _ability_check(self, interaction, ability, skill, test_type, modifier):
        """Make ability check with 2024 rules"""
        user_id = str(interaction.user.id)
        
        if user_id not in self.campaign_context["characters"]:
            await interaction.response.send_message("❌ No character registered!", ephemeral=True)
            return
        
        char_data = self.campaign_context["players"][user_id]["character_data"]
        ability_scores = char_data["ability_scores"]
        
        # Calculate base modifier
        base_modifier = self.calculate_ability_modifier(ability_scores[ability])
        
        # Add proficiency if applicable
        proficiency_bonus = char_data["proficiency_bonus"]
        total_modifier = base_modifier + modifier
        
        check_name = ability.title()
        
        if skill:
            # Check if proficient in skill
            if char_data["skills"].get(skill, False):
                total_modifier += proficiency_bonus
            
            skill_name = skill.replace("_", " ").title()
            check_name = f"{skill_name} ({ability.title()})"
        
        # Roll dice with 2024 advantage/disadvantage rules
        if test_type == "advantage":
            roll1 = random.randint(1, 20)
            roll2 = random.randint(1, 20)
            roll = max(roll1, roll2)
            roll_text = f"{roll1}, {roll2} → **{roll}** (advantage)"
        elif test_type == "disadvantage":
            roll1 = random.randint(1, 20)
            roll2 = random.randint(1, 20)
            roll = min(roll1, roll2)
            roll_text = f"{roll1}, {roll2} → **{roll}** (disadvantage)"
        else:
            roll = random.randint(1, 20)
            roll_text = f"**{roll}**"
        
        total = roll + total_modifier
        
        # Create response
        embed = discord.Embed(
            title=f"🎲 {char_data['name']} - {check_name} (2024)",
            color=0x32CD32 if roll == 20 else 0xFF6B6B if roll == 1 else 0x4169E1
        )
        
        modifier_text = f"{total_modifier:+d}" if total_modifier != 0 else "+0"
        embed.add_field(name="Roll", value=roll_text, inline=True)
        embed.add_field(name="Modifier", value=modifier_text, inline=True)
        embed.add_field(name="Total", value=f"**{total}**", inline=True)
        
        # Add special results
        if roll == 20:
            embed.add_field(name="🎯 Natural 20!", value="Critical success!", inline=False)
        elif roll == 1:
            embed.add_field(name="💥 Natural 1!", value="Critical failure!", inline=False)
        
        await interaction.response.send_message(embed=embed)

    async def _saving_throw(self, interaction, ability, test_type, modifier):
        """Make saving throw with 2024 rules"""
        user_id = str(interaction.user.id)
        
        if user_id not in self.campaign_context["characters"]:
            await interaction.response.send_message("❌ No character registered!", ephemeral=True)
            return
        
        char_data = self.campaign_context["players"][user_id]["character_data"]
        ability_scores = char_data["ability_scores"]
        saving_throws = char_data["saving_throws"]
        
        # Calculate modifier
        base_modifier = self.calculate_ability_modifier(ability_scores[ability])
        total_modifier = base_modifier + modifier
        
        # Add proficiency if proficient
        proficiency_bonus = char_data["proficiency_bonus"]
        if saving_throws.get(ability, False):
            total_modifier += proficiency_bonus
        
        # Roll dice
        if test_type == "advantage":
            roll1 = random.randint(1, 20)
            roll2 = random.randint(1, 20)
            roll = max(roll1, roll2)
            roll_text = f"{roll1}, {roll2} → **{roll}** (advantage)"
        elif test_type == "disadvantage":
            roll1 = random.randint(1, 20)
            roll2 = random.randint(1, 20)
            roll = min(roll1, roll2)
            roll_text = f"{roll1}, {roll2} → **{roll}** (disadvantage)"
        else:
            roll = random.randint(1, 20)
            roll_text = f"**{roll}**"
        
        total = roll + total_modifier
        
        # Create response
        embed = discord.Embed(
            title=f"🛡️ {char_data['name']} - {ability.title()} Save (2024)",
            color=0x32CD32 if roll == 20 else 0xFF6B6B if roll == 1 else 0x4169E1
        )
        
        modifier_text = f"{total_modifier:+d}" if total_modifier != 0 else "+0"
        embed.add_field(name="Roll", value=roll_text, inline=True)
        embed.add_field(name="Modifier", value=modifier_text, inline=True)
        embed.add_field(name="Total", value=f"**{total}**", inline=True)
        
        # Add special results
        if roll == 20:
            embed.add_field(name="🎯 Natural 20!", value="Critical success!", inline=False)
        elif roll == 1:
            embed.add_field(name="💥 Natural 1!", value="Critical failure!", inline=False)
        
        await interaction.response.send_message(embed=embed)

    async def _view_character_sheet_2024(self, interaction, player):
        """View complete 2024 character sheet"""
        target_user = player or interaction.user
        user_id = str(target_user.id)
        
        if user_id not in self.campaign_context["characters"]:
            embed = discord.Embed(
                title="❌ Character Not Found",
                description=f"No character registered for {target_user.display_name}. Use `/character` to register!",
                color=0xFF6B6B
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        # Get character data
        char_data = self.campaign_context["players"][user_id]["character_data"]
        
        # Create main character sheet embed
        embed = discord.Embed(
            title=f"📜 D&D 5e 2024 Character Sheet: {char_data['name']}",
            description=f"**{char_data['species']} {char_data['class']}** (Level {char_data['level']})\n*{char_data['background']}*",
            color=0x4169E1
        )
        
        # Basic Info
        embed.add_field(name="👤 Player", value=target_user.display_name, inline=True)
        embed.add_field(name="⭐ Proficiency Bonus", value=f"+{char_data['proficiency_bonus']}", inline=True)
        embed.add_field(name="🎯 Hit Dice", value=char_data['hit_dice'], inline=True)
        
        # Ability Scores with modifiers
        abilities = []
        for ability, score in char_data["ability_scores"].items():
            modifier = self.calculate_ability_modifier(score)
            save_prof = "✓" if char_data["saving_throws"].get(ability, False) else ""
            abilities.append(f"**{ability[:3].upper()}** {score} ({modifier:+d}){save_prof}")
        
        embed.add_field(
            name="📊 Ability Scores & Saves (2024)", 
            value="\n".join(abilities), 
            inline=True
        )
        
        # Combat Stats
        hp = char_data["hit_points"]
        hp_display = f"{hp['current']}/{hp['maximum']}"
        if hp["temporary"] > 0:
            hp_display += f" (+{hp['temporary']} temp)"
        
        combat_stats = [
            f"**AC:** {char_data['armor_class']}",
            f"**HP:** {hp_display}",
            f"**Speed:** {char_data['speed']} ft"
        ]
        
        embed.add_field(name="⚔️ Combat Stats", value="\n".join(combat_stats), inline=True)
        
        # Skills (only show proficient ones)
        proficient_skills = []
        for skill, is_proficient in char_data["skills"].items():
            if is_proficient:
                skill_name = skill.replace("_", " ").title()
                skill_abilities = {
                    "athletics": "strength",
                    "acrobatics": "dexterity", "sleight_of_hand": "dexterity", "stealth": "dexterity",
                    "arcana": "intelligence", "history": "intelligence", "investigation": "intelligence", 
                    "nature": "intelligence", "religion": "intelligence",
                    "animal_handling": "wisdom", "insight": "wisdom", "medicine": "wisdom", 
                    "perception": "wisdom", "survival": "wisdom",
                    "deception": "charisma", "intimidation": "charisma", "performance": "charisma", 
                    "persuasion": "charisma"
                }
                
                ability = skill_abilities.get(skill, "intelligence")
                ability_mod = self.calculate_ability_modifier(char_data["ability_scores"][ability])
                skill_bonus = ability_mod + char_data["proficiency_bonus"]
                proficient_skills.append(f"{skill_name} +{skill_bonus}")
        
        if proficient_skills:
            embed.add_field(name="🎯 Proficient Skills", value="\n".join(proficient_skills), inline=True)
        
        # Spellcasting (if applicable)
        if char_data["spellcasting"]["ability"]:
            spell_slots = char_data["spellcasting"]["spell_slots"]
            spell_slots_used = char_data["spell_slots_used"]
            
            slot_display = []
            for level in ["1st", "2nd", "3rd", "4th", "5th"]:  # Show first 5 levels
                total = spell_slots[level]
                used = spell_slots_used[level]
                if total > 0:
                    available = total - used
                    slot_display.append(f"{level}: {available}/{total}")
            
            if slot_display:
                embed.add_field(name="✨ Spell Slots (2024)", value="\n".join(slot_display), inline=True)
        
        embed.set_footer(text="D&D 5e 2024 Rules • Use commands to manage HP, spells, and make rolls!")
        await interaction.response.send_message(embed=embed)