"""
Combat Service - D&D combat mechanics and calculations
"""
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
from enum import Enum
import random

from ..entities.character import Character


class DamageType(Enum):
    SLASHING = "slashing"
    PIERCING = "piercing"
    BLUDGEONING = "bludgeoning"
    FIRE = "fire"
    COLD = "cold"
    LIGHTNING = "lightning"
    THUNDER = "thunder"
    ACID = "acid"
    POISON = "poison"
    NECROTIC = "necrotic"
    RADIANT = "radiant"
    PSYCHIC = "psychic"
    FORCE = "force"


class AttackType(Enum):
    MELEE_WEAPON = "melee_weapon"
    RANGED_WEAPON = "ranged_weapon"
    SPELL_ATTACK = "spell_attack"
    SAVING_THROW = "saving_throw"


@dataclass
class CombatAction:
    """Represents a combat action"""
    character_name: str
    action_type: str  # attack, spell, move, dodge, etc.
    target: Optional[str] = None
    description: str = ""
    roll_needed: bool = True


@dataclass
class AttackRoll:
    """Result of an attack roll"""
    attack_roll: int
    damage_roll: Optional[int] = None
    is_hit: bool = False
    is_critical: bool = False
    damage_type: DamageType = DamageType.SLASHING
    attack_type: AttackType = AttackType.MELEE_WEAPON


@dataclass
class CombatResult:
    """Result of a combat action"""
    action: CombatAction
    roll_result: Optional[AttackRoll] = None
    damage_dealt: int = 0
    effects: List[str] = None
    narrative: str = ""
    
    def __post_init__(self):
        if self.effects is None:
            self.effects = []


class CombatService:
    """Service for D&D combat mechanics and calculations"""
    
    def __init__(self):
        self.advantage_situations = {
            "flanking", "hidden", "prone_target", "stunned_target", 
            "paralyzed_target", "unconscious_target", "restrained_target"
        }
        
        self.disadvantage_situations = {
            "prone_attacker", "blinded", "poisoned", "frightened",
            "restrained_attacker", "underwater_melee"
        }
    
    def roll_d20(self, advantage: bool = False, disadvantage: bool = False) -> int:
        """Roll a d20 with advantage/disadvantage"""
        if advantage and disadvantage:
            # Cancel out
            return random.randint(1, 20)
        elif advantage:
            return max(random.randint(1, 20), random.randint(1, 20))
        elif disadvantage:
            return min(random.randint(1, 20), random.randint(1, 20))
        else:
            return random.randint(1, 20)
    
    def roll_damage(self, dice_notation: str) -> int:
        """Roll damage from dice notation (e.g., '2d6+3')"""
        try:
            # Parse dice notation like "2d6+3" or "1d8"
            if '+' in dice_notation:
                dice_part, modifier = dice_notation.split('+')
                modifier = int(modifier)
            elif '-' in dice_notation:
                dice_part, neg_modifier = dice_notation.split('-')
                modifier = -int(neg_modifier)
            else:
                dice_part = dice_notation
                modifier = 0
            
            # Parse dice (e.g., "2d6")
            num_dice, die_size = dice_part.split('d')
            num_dice = int(num_dice)
            die_size = int(die_size)
            
            # Roll dice
            total = sum(random.randint(1, die_size) for _ in range(num_dice))
            return max(1, total + modifier)  # Minimum 1 damage
            
        except (ValueError, AttributeError):
            # Default to 1d4 if parsing fails
            return random.randint(1, 4)
    
    def calculate_attack_bonus(self, character: Character, attack_type: AttackType) -> int:
        """Calculate attack bonus for a character"""
        proficiency_bonus = (character.level - 1) // 4 + 2  # D&D proficiency progression
        
        if attack_type == AttackType.MELEE_WEAPON:
            ability_mod = character.ability_scores.get_modifier("strength")
        elif attack_type == AttackType.RANGED_WEAPON:
            ability_mod = character.ability_scores.get_modifier("dexterity")
        elif attack_type == AttackType.SPELL_ATTACK:
            # Use spellcasting modifier based on class
            spellcasting_ability = self._get_spellcasting_ability(character)
            ability_mod = character.ability_scores.get_modifier(spellcasting_ability)
        else:
            ability_mod = 0
        
        return ability_mod + proficiency_bonus
    
    def calculate_armor_class(self, character: Character) -> int:
        """Calculate Armor Class (simplified)"""
        # Base AC (assuming no armor for simplicity)
        base_ac = 10 + character.ability_scores.get_modifier("dexterity")
        
        # Could add armor bonuses here based on equipment
        armor_bonus = 0  # TODO: Calculate from equipment
        
        return base_ac + armor_bonus
    
    def make_attack_roll(self, 
                        attacker: Character,
                        target_ac: int,
                        attack_type: AttackType = AttackType.MELEE_WEAPON,
                        advantage: bool = False,
                        disadvantage: bool = False) -> AttackRoll:
        """Make an attack roll against a target"""
        
        # Roll d20
        d20_roll = self.roll_d20(advantage, disadvantage)
        
        # Calculate attack bonus
        attack_bonus = self.calculate_attack_bonus(attacker, attack_type)
        
        # Total attack roll
        total_roll = d20_roll + attack_bonus
        
        # Check for hit
        is_hit = total_roll >= target_ac or d20_roll == 20
        is_critical = d20_roll == 20
        
        # Roll damage if hit
        damage_roll = None
        if is_hit:
            damage_dice = self._get_weapon_damage(attacker, attack_type)
            damage_roll = self.roll_damage(damage_dice)
            
            # Double damage on critical hit
            if is_critical:
                damage_roll *= 2
        
        return AttackRoll(
            attack_roll=total_roll,
            damage_roll=damage_roll,
            is_hit=is_hit,
            is_critical=is_critical,
            attack_type=attack_type
        )
    
    def make_saving_throw(self, 
                         character: Character,
                         save_type: str,  # "strength", "dexterity", etc.
                         dc: int,
                         advantage: bool = False,
                         disadvantage: bool = False) -> Tuple[int, bool]:
        """Make a saving throw"""
        
        # Roll d20
        d20_roll = self.roll_d20(advantage, disadvantage)
        
        # Get ability modifier
        ability_mod = character.ability_scores.get_modifier(save_type)
        
        # Add proficiency if proficient (simplified - assume proficient in primary saves)
        proficiency_bonus = (character.level - 1) // 4 + 2
        save_proficiencies = self._get_save_proficiencies(character)
        
        if save_type in save_proficiencies:
            total_bonus = ability_mod + proficiency_bonus
        else:
            total_bonus = ability_mod
        
        total_roll = d20_roll + total_bonus
        success = total_roll >= dc
        
        return total_roll, success
    
    def calculate_initiative(self, character: Character) -> int:
        """Calculate initiative roll"""
        dex_mod = character.ability_scores.get_modifier("dexterity")
        return random.randint(1, 20) + dex_mod
    
    def resolve_combat_action(self, 
                            action: CombatAction,
                            attacker: Character,
                            target: Optional[Character] = None,
                            combat_conditions: Dict[str, bool] = None) -> CombatResult:
        """Resolve a complete combat action"""
        
        if combat_conditions is None:
            combat_conditions = {}
        
        result = CombatResult(action=action)
        
        # Handle different action types
        if action.action_type.lower() in ["attack", "melee", "ranged"]:
            if not target:
                result.narrative = f"{action.character_name} attacks but has no target!"
                return result
            
            # Determine attack type
            attack_type = AttackType.MELEE_WEAPON if "melee" in action.action_type.lower() else AttackType.RANGED_WEAPON
            
            # Check for advantage/disadvantage
            advantage = any(condition in combat_conditions for condition in self.advantage_situations)
            disadvantage = any(condition in combat_conditions for condition in self.disadvantage_situations)
            
            # Make attack roll
            target_ac = self.calculate_armor_class(target)
            attack_result = self.make_attack_roll(attacker, target_ac, attack_type, advantage, disadvantage)
            
            result.roll_result = attack_result
            
            if attack_result.is_hit:
                result.damage_dealt = attack_result.damage_roll
                result.narrative = self._generate_attack_narrative(attacker, target, attack_result)
                
                if attack_result.is_critical:
                    result.effects.append("Critical Hit!")
            else:
                result.narrative = f"{attacker.name} attacks {target.name} but misses!"
        
        elif action.action_type.lower() == "spell":
            result.narrative = f"{attacker.name} casts a spell! {action.description}"
            # TODO: Implement spell resolution
        
        elif action.action_type.lower() == "dodge":
            result.narrative = f"{attacker.name} takes the Dodge action, gaining advantage on Dexterity saving throws!"
            result.effects.append("Dodging - attackers have disadvantage")
        
        elif action.action_type.lower() == "dash":
            result.narrative = f"{attacker.name} dashes, doubling their movement speed!"
            result.effects.append("Dashing - doubled movement")
        
        else:
            result.narrative = f"{attacker.name} performs a {action.action_type}: {action.description}"
        
        return result
    
    def _get_spellcasting_ability(self, character: Character) -> str:
        """Get primary spellcasting ability for character class"""
        from ..entities.character import CharacterClass
        
        spellcasting_abilities = {
            CharacterClass.WIZARD: "intelligence",
            CharacterClass.SORCERER: "charisma", 
            CharacterClass.WARLOCK: "charisma",
            CharacterClass.BARD: "charisma",
            CharacterClass.CLERIC: "wisdom",
            CharacterClass.DRUID: "wisdom",
            CharacterClass.RANGER: "wisdom",
            CharacterClass.PALADIN: "charisma"
        }
        
        return spellcasting_abilities.get(character.character_class, "intelligence")
    
    def _get_save_proficiencies(self, character: Character) -> List[str]:
        """Get saving throw proficiencies for character class"""
        from ..entities.character import CharacterClass
        
        save_proficiencies = {
            CharacterClass.BARBARIAN: ["strength", "constitution"],
            CharacterClass.BARD: ["dexterity", "charisma"],
            CharacterClass.CLERIC: ["wisdom", "charisma"],
            CharacterClass.DRUID: ["intelligence", "wisdom"],
            CharacterClass.FIGHTER: ["strength", "constitution"],
            CharacterClass.MONK: ["strength", "dexterity"],
            CharacterClass.PALADIN: ["wisdom", "charisma"],
            CharacterClass.RANGER: ["strength", "dexterity"],
            CharacterClass.ROGUE: ["dexterity", "intelligence"],
            CharacterClass.SORCERER: ["constitution", "charisma"],
            CharacterClass.WARLOCK: ["wisdom", "charisma"],
            CharacterClass.WIZARD: ["intelligence", "wisdom"]
        }
        
        return save_proficiencies.get(character.character_class, [])
    
    def _get_weapon_damage(self, character: Character, attack_type: AttackType) -> str:
        """Get weapon damage dice for character (simplified)"""
        # Simplified weapon damage based on class and type
        if attack_type == AttackType.MELEE_WEAPON:
            # Add strength modifier
            str_mod = character.ability_scores.get_modifier("strength")
            return f"1d8+{str_mod}" if str_mod > 0 else "1d8"
        elif attack_type == AttackType.RANGED_WEAPON:
            # Add dex modifier  
            dex_mod = character.ability_scores.get_modifier("dexterity")
            return f"1d6+{dex_mod}" if dex_mod > 0 else "1d6"
        else:
            return "1d6"  # Spell damage varies widely
    
    def _generate_attack_narrative(self, attacker: Character, target: Character, attack_result: AttackRoll) -> str:
        """Generate narrative text for an attack"""
        if attack_result.is_critical:
            return f"🎯 {attacker.name} scores a critical hit against {target.name} for {attack_result.damage_roll} damage!"
        elif attack_result.damage_roll and attack_result.damage_roll >= 8:
            return f"⚔️ {attacker.name} strikes {target.name} hard for {attack_result.damage_roll} damage!"
        elif attack_result.is_hit:
            return f"⚔️ {attacker.name} hits {target.name} for {attack_result.damage_roll} damage."
        else:
            return f"❌ {attacker.name} swings at {target.name} but misses!"