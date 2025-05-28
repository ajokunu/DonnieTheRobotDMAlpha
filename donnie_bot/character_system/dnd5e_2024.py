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





    async def _view_character_sheet_2024(self, interaction, player):
        """View complete 2024 character sheet with ALL values displayed"""
        try:
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
            
            # Get character data with comprehensive PDF data if available
            player_data = self.campaign_context["players"][user_id]
            char_data = player_data.get("character_data", {})
            comprehensive_data = player_data.get("comprehensive_data", {})
            
            # Use comprehensive data if available (from PDF), otherwise use legacy data
            if comprehensive_data:
                await self._display_comprehensive_character_sheet(interaction, target_user, comprehensive_data)
            else:
                await self._display_legacy_character_sheet(interaction, target_user, char_data)
                
        except Exception as e:
            print(f"CRITICAL ERROR in _view_character_sheet_2024: {e}")
            import traceback
            traceback.print_exc()
            
            # Emergency fallback
            embed = discord.Embed(
                title="❌ Error Loading Character Sheet",
                description="There was an error loading the character sheet. Please try again.",
                color=0xFF6B6B
            )
            
            try:
                await interaction.response.send_message(embed=embed, ephemeral=True)
            except:
                await interaction.followup.send(embed=embed, ephemeral=True)

    async def _display_comprehensive_character_sheet(self, interaction, target_user, comprehensive_data):
        """Display complete character sheet using comprehensive PDF data"""
        
        # Create main embed with character header
        embed = discord.Embed(
            title=f"📜 {comprehensive_data.get('name', 'Unknown Character')}",
            description=f"**{comprehensive_data.get('race', 'Unknown')} {comprehensive_data.get('class', 'Unknown')}** • Level {comprehensive_data.get('level', 1)}",
            color=0x4169E1
        )
        
        # === BASIC INFORMATION ===
        basic_info = []
        basic_info.append(f"**Background:** {comprehensive_data.get('background', 'Unknown')}")
        basic_info.append(f"**Alignment:** {comprehensive_data.get('alignment', 'Unknown')}")
        basic_info.append(f"**Experience:** {comprehensive_data.get('experience_points', 0)} XP")
        basic_info.append(f"**Player:** {target_user.display_name}")
        
        embed.add_field(
            name="📋 Basic Information",
            value="\n".join(basic_info),
            inline=False
        )
        
        # === ABILITY SCORES ===
        abilities = comprehensive_data.get('ability_scores', {})
        modifiers = comprehensive_data.get('ability_modifiers', {})
        
        ability_display = []
        for ability in ['strength', 'dexterity', 'constitution', 'intelligence', 'wisdom', 'charisma']:
            score = abilities.get(ability, 10)
            modifier = modifiers.get(ability, '+0')
            ability_display.append(f"**{ability[:3].upper()}** {score} ({modifier})")
        
        # Format in two columns like the PDF
        embed.add_field(
            name="📊 Ability Scores",
            value=f"{ability_display[0]}   {ability_display[1]}\n{ability_display[2]}   {ability_display[3]}\n{ability_display[4]}   {ability_display[5]}",
            inline=True
        )
        
        # === COMBAT STATS ===
        combat = comprehensive_data.get('combat_stats', {})
        
        combat_info = []
        combat_info.append(f"**Armor Class:** {combat.get('armor_class', 10)}")
        combat_info.append(f"**Initiative:** {combat.get('initiative', '+0')}")
        combat_info.append(f"**Speed:** {combat.get('speed', '30 ft')}")
        combat_info.append(f"**Hit Point Maximum:** {combat.get('hit_point_maximum', 8)}")
        combat_info.append(f"**Current Hit Points:** {combat.get('current_hit_points', 8)}")
        if combat.get('temporary_hit_points', 0) > 0:
            combat_info.append(f"**Temporary HP:** {combat.get('temporary_hit_points', 0)}")
        combat_info.append(f"**Hit Dice:** {combat.get('hit_dice', '1d8')}")
        
        embed.add_field(
            name="⚔️ Combat Stats",
            value="\n".join(combat_info),
            inline=True
        )
        
        # === PROFICIENCIES ===
        prof = comprehensive_data.get('proficiencies', {})
        
        prof_info = []
        prof_info.append(f"**Proficiency Bonus:** {prof.get('proficiency_bonus', '+2')}")
        
        saving_throws = prof.get('saving_throws', [])
        if saving_throws:
            prof_info.append(f"**Saving Throws:** {', '.join(saving_throws)}")
        
        skills = prof.get('skills', [])
        if skills:
            # Limit skills display to prevent overflow
            skills_display = ', '.join(skills[:8])
            if len(skills) > 8:
                skills_display += f" (+{len(skills) - 8} more)"
            prof_info.append(f"**Skills:** {skills_display}")
        
        languages = prof.get('languages', [])
        if languages:
            prof_info.append(f"**Languages:** {', '.join(languages)}")
        
        embed.add_field(
            name="🎯 Proficiencies",
            value="\n".join(prof_info),
            inline=False
        )
        
        # === EQUIPMENT ===
        equipment = comprehensive_data.get('equipment', {})
        
        equip_sections = []
        
        weapons = equipment.get('weapons', [])
        if weapons:
            weapons_text = ', '.join(weapons[:5])  # Show first 5 weapons
            if len(weapons) > 5:
                weapons_text += f" (+{len(weapons) - 5} more)"
            equip_sections.append(f"**Weapons:** {weapons_text}")
        
        armor = equipment.get('armor', [])
        if armor:
            equip_sections.append(f"**Armor:** {', '.join(armor)}")
        
        items = equipment.get('items', [])
        if items:
            items_text = ', '.join(items[:8])  # Show first 8 items
            if len(items) > 8:
                items_text += f" (+{len(items) - 8} more)"
            equip_sections.append(f"**Items:** {items_text}")
        
        treasure = equipment.get('treasure', [])
        if treasure:
            equip_sections.append(f"**Treasure:** {', '.join(treasure)}")
        
        if equip_sections:
            embed.add_field(
                name="🎒 Equipment",
                value="\n".join(equip_sections),
                inline=False
            )
        
        # Send first embed
        await interaction.response.send_message(embed=embed)
        
        # === SPELLCASTING (Second Embed) ===
        spellcasting = comprehensive_data.get('spellcasting', {})
        if spellcasting.get('spellcasting_class'):
            spell_embed = discord.Embed(
                title=f"✨ {comprehensive_data.get('name', 'Character')} - Spellcasting",
                color=0x9932CC
            )
            
            spell_info = []
            spell_info.append(f"**Spellcasting Class:** {spellcasting.get('spellcasting_class')}")
            spell_info.append(f"**Spellcasting Ability:** {spellcasting.get('spellcasting_ability', 'Unknown')}")
            spell_info.append(f"**Spell Save DC:** {spellcasting.get('spell_save_dc', 8)}")
            spell_info.append(f"**Spell Attack Bonus:** {spellcasting.get('spell_attack_bonus', '+0')}")
            
            spell_embed.add_field(
                name="🎭 Spellcasting Info",
                value="\n".join(spell_info),
                inline=False
            )
            
            # Spell Slots
            spell_slots = spellcasting.get('spell_slots', {})
            slot_info = []
            for level in range(1, 10):
                level_key = f"level_{level}"
                if level_key in spell_slots:
                    slot_data = spell_slots[level_key]
                    total = slot_data.get('total', 0)
                    expended = slot_data.get('expended', 0)
                    if total > 0:
                        available = total - expended
                        slot_emoji = "🔵" if available == total else "🟡" if available > 0 else "🔴"
                        slot_info.append(f"{slot_emoji} **Level {level}:** {available}/{total}")
            
            if slot_info:
                spell_embed.add_field(
                    name="🔮 Spell Slots",
                    value="\n".join(slot_info),
                    inline=True
                )
            
            # Cantrips
            cantrips = spellcasting.get('cantrips', [])
            if cantrips:
                cantrips_text = ', '.join(cantrips)
                spell_embed.add_field(
                    name="🌟 Cantrips",
                    value=cantrips_text,
                    inline=False
                )
            
            # Known Spells by Level
            spells_known = spellcasting.get('spells_known', {})
            for level in range(1, 10):
                level_key = f"level_{level}"
                if level_key in spells_known and spells_known[level_key]:
                    spells_list = spells_known[level_key]
                    spells_text = ', '.join(spells_list)
                    spell_embed.add_field(
                        name=f"📖 Level {level} Spells",
                        value=spells_text,
                        inline=False
                    )
            
            await interaction.followup.send(embed=spell_embed)
        
        # === FEATURES & TRAITS (Third Embed) ===
        features = comprehensive_data.get('features_and_traits', {})
        
        feature_embed = discord.Embed(
            title=f"🌟 {comprehensive_data.get('name', 'Character')} - Features & Traits",
            color=0x32CD32
        )
        
        racial_traits = features.get('racial_traits', [])
        if racial_traits:
            feature_embed.add_field(
                name=f"🧬 {comprehensive_data.get('race', 'Racial')} Traits",
                value=', '.join(racial_traits),
                inline=False
            )
        
        class_features = features.get('class_features', [])
        if class_features:
            feature_embed.add_field(
                name=f"⚡ {comprehensive_data.get('class', 'Class')} Features",
                value=', '.join(class_features),
                inline=False
            )
        
        background_features = features.get('background_features', [])
        if background_features:
            feature_embed.add_field(
                name=f"📚 {comprehensive_data.get('background', 'Background')} Features",
                value=', '.join(background_features),
                inline=False
            )
        
        feats = features.get('feats', [])
        if feats:
            feature_embed.add_field(
                name="🏆 Feats",
                value=', '.join(feats),
                inline=False
            )
        
        other_features = features.get('other_features', [])
        if other_features:
            feature_embed.add_field(
                name="🔮 Other Features",
                value=', '.join(other_features),
                inline=False
            )
        
        # Only send if there are features to show
        if any([racial_traits, class_features, background_features, feats, other_features]):
            await interaction.followup.send(embed=feature_embed)
        
        # === PERSONALITY & ROLEPLAY (Fourth Embed) ===
        personality = comprehensive_data.get('personality', {})
        physical = comprehensive_data.get('physical_description', {})
        affiliations = comprehensive_data.get('affiliations', {})
        
        rp_embed = discord.Embed(
            title=f"🎭 {comprehensive_data.get('name', 'Character')} - Personality & Background",
            color=0xFF69B4
        )
        
        # Personality Traits
        personality_traits = personality.get('personality_traits', [])
        if personality_traits:
            rp_embed.add_field(
                name="😊 Personality Traits",
                value='\n'.join([f"• {trait}" for trait in personality_traits]),
                inline=False
            )
        
        # Ideals
        ideals = personality.get('ideals', [])
        if ideals:
            rp_embed.add_field(
                name="💡 Ideals",
                value='\n'.join([f"• {ideal}" for ideal in ideals]),
                inline=False
            )
        
        # Bonds
        bonds = personality.get('bonds', [])
        if bonds:
            rp_embed.add_field(
                name="🔗 Bonds",
                value='\n'.join([f"• {bond}" for bond in bonds]),
                inline=False
            )
        
        # Flaws
        flaws = personality.get('flaws', [])
        if flaws:
            rp_embed.add_field(
                name="💔 Flaws",
                value='\n'.join([f"• {flaw}" for flaw in flaws]),
                inline=False
            )
        
        # Physical Description
        physical_desc = []
        if physical.get('age'):
            physical_desc.append(f"**Age:** {physical['age']}")
        if physical.get('height'):
            physical_desc.append(f"**Height:** {physical['height']}")
        if physical.get('weight'):
            physical_desc.append(f"**Weight:** {physical['weight']}")
        if physical.get('eyes'):
            physical_desc.append(f"**Eyes:** {physical['eyes']}")
        if physical.get('skin'):
            physical_desc.append(f"**Skin:** {physical['skin']}")
        if physical.get('hair'):
            physical_desc.append(f"**Hair:** {physical['hair']}")
        
        if physical_desc:
            rp_embed.add_field(
                name="👁️ Physical Description",
                value='\n'.join(physical_desc),
                inline=True
            )
        
        if physical.get('appearance'):
            rp_embed.add_field(
                name="🖼️ Appearance",
                value=physical['appearance'],
                inline=False
            )
        
        # Backstory
        if personality.get('backstory'):
            backstory = personality['backstory']
            if len(backstory) > 1024:
                backstory = backstory[:1021] + "..."
            rp_embed.add_field(
                name="📖 Backstory",
                value=backstory,
                inline=False
            )
        
        # Affiliations
        org_info = []
        organizations = affiliations.get('organizations', [])
        if organizations:
            org_info.append(f"**Organizations:** {', '.join(organizations)}")
        
        allies = affiliations.get('allies', [])
        if allies:
            org_info.append(f"**Allies:** {', '.join(allies)}")
        
        enemies = affiliations.get('enemies', [])
        if enemies:
            org_info.append(f"**Enemies:** {', '.join(enemies)}")
        
        if org_info:
            rp_embed.add_field(
                name="🏛️ Affiliations",
                value='\n'.join(org_info),
                inline=False
            )
        
        # Additional Notes
        if comprehensive_data.get('additional_notes'):
            notes = comprehensive_data['additional_notes']
            if len(notes) > 1024:
                notes = notes[:1021] + "..."
            rp_embed.add_field(
                name="📝 Additional Notes",
                value=notes,
                inline=False
            )
        
        # Only send if there's personality/roleplay info to show
        if any([personality_traits, ideals, bonds, flaws, physical_desc, personality.get('backstory'), 
                organizations, allies, enemies, comprehensive_data.get('additional_notes')]):
            await interaction.followup.send(embed=rp_embed)
        
        # Final embed with footer
        footer_embed = discord.Embed(
            title="",
            description="**D&D 5e 2024 Rules** • Use `/roll` for dice and let the DM manage combat mechanics!",
            color=0x4169E1
        )
        footer_embed.set_footer(text="📄 Character data parsed from PDF upload")
        
        await interaction.followup.send(embed=footer_embed)

    async def _display_legacy_character_sheet(self, interaction, target_user, char_data):
        """Display character sheet using legacy format data"""
        
        # Safely get basic character info
        name = char_data.get('name', 'Unknown Character')
        species = char_data.get('species', char_data.get('race', 'Unknown'))
        char_class = char_data.get('class', 'Unknown')
        level = char_data.get('level', 1)
        background = char_data.get('background', 'Unknown')
        
        # Create main character sheet embed
        embed = discord.Embed(
            title=f"📜 D&D 5e 2024 Character Sheet: {name}",
            description=f"**{species} {char_class}** (Level {level})\n*{background}*",
            color=0x4169E1
        )
        
        # Basic Info - Safe access
        embed.add_field(name="👤 Player", value=target_user.display_name, inline=True)
        
        # Proficiency Bonus - Calculate if missing
        prof_bonus = char_data.get('proficiency_bonus', self.calculate_proficiency_bonus(level))
        embed.add_field(name="⭐ Proficiency Bonus", value=f"+{prof_bonus}", inline=True)
        
        # Hit Dice - Safe construction
        hit_dice = char_data.get('hit_dice', f"{level}d8")
        embed.add_field(name="🎯 Hit Dice", value=hit_dice, inline=True)
        
        # Ability Scores with error handling
        try:
            ability_scores = char_data.get('ability_scores', {})
            if not ability_scores:
                # Try alternative structures
                ability_scores = {
                    'strength': char_data.get('strength', 10),
                    'dexterity': char_data.get('dexterity', 10),
                    'constitution': char_data.get('constitution', 10),
                    'intelligence': char_data.get('intelligence', 10),
                    'wisdom': char_data.get('wisdom', 10),
                    'charisma': char_data.get('charisma', 10)
                }
            
            abilities = []
            saving_throws = char_data.get("saving_throws", {})
            
            for ability in ['strength', 'dexterity', 'constitution', 'intelligence', 'wisdom', 'charisma']:
                score = ability_scores.get(ability, 10)
                if isinstance(score, str):
                    try:
                        score = int(score)
                    except:
                        score = 10
                
                modifier = self.calculate_ability_modifier(score)
                save_prof = "✓" if saving_throws.get(ability, False) else ""
                abilities.append(f"**{ability[:3].upper()}** {score} ({modifier:+d}){save_prof}")
            
            embed.add_field(
                name="📊 Ability Scores & Saves (2024)", 
                value="\n".join(abilities), 
                inline=True
            )
        except Exception as e:
            print(f"Error processing ability scores: {e}")
            embed.add_field(name="📊 Ability Scores", value="Error loading ability scores", inline=True)
        
        # Combat Stats - Safe access with defaults
        try:
            # Handle different HP structures
            hp_data = char_data.get("hit_points", {})
            if isinstance(hp_data, dict):
                hp_current = hp_data.get('current', hp_data.get('maximum', level * 8))
                hp_max = hp_data.get('maximum', level * 8)
                hp_temp = hp_data.get('temporary', 0)
            else:
                # Handle simple HP structure
                hp_current = char_data.get('hp_current', char_data.get('hp', level * 8))
                hp_max = char_data.get('hp_max', char_data.get('hp', level * 8))
                hp_temp = char_data.get('hp_temp', 0)
            
            hp_display = f"{hp_current}/{hp_max}"
            if hp_temp > 0:
                hp_display += f" (+{hp_temp} temp)"
            
            ac = char_data.get('armor_class', char_data.get('ac', 10))
            speed = char_data.get('speed', 30)
            
            combat_stats = [
                f"**AC:** {ac}",
                f"**HP:** {hp_display}",
                f"**Speed:** {speed} ft"
            ]
            
            embed.add_field(name="⚔️ Combat Stats", value="\n".join(combat_stats), inline=True)
        except Exception as e:
            print(f"Error processing combat stats: {e}")
            embed.add_field(name="⚔️ Combat Stats", value="Error loading combat stats", inline=True)
        
        # Equipment - Safe processing
        try:
            equipment = char_data.get("equipment", "")
            if equipment and equipment != "Basic adventuring gear":
                embed.add_field(name="⚔️ Equipment", value=equipment[:400], inline=False)
        except Exception as e:
            print(f"Error processing equipment: {e}")
        
        # Personality (if available)
        try:
            personality = char_data.get("personality", "")
            if personality and personality != "To be determined":
                embed.add_field(name="🎭 Personality", value=personality[:300], inline=False)
        except Exception as e:
            print(f"Error processing personality: {e}")
        
        embed.set_footer(text="D&D 5e 2024 Rules • Use commands to manage HP, spells, and make rolls!")
        await interaction.response.send_message(embed=embed)