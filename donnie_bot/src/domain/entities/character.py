"""
Character domain entity - Pure D&D business logic
No external dependencies!
"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from enum import Enum

class CharacterClass(Enum):
    FIGHTER = "Fighter"
    WIZARD = "Wizard"
    ROGUE = "Rogue"
    CLERIC = "Cleric"
    RANGER = "Ranger"
    PALADIN = "Paladin"
    BARBARIAN = "Barbarian"
    BARD = "Bard"
    DRUID = "Druid"
    MONK = "Monk"
    SORCERER = "Sorcerer"
    WARLOCK = "Warlock"

class Race(Enum):
    HUMAN = "Human"
    ELF = "Elf"
    DWARF = "Dwarf"
    HALFLING = "Halfling"
    DRAGONBORN = "Dragonborn"
    GNOME = "Gnome"
    HALF_ELF = "Half-Elf"
    HALF_ORC = "Half-Orc"
    TIEFLING = "Tiefling"

@dataclass
class AbilityScores:
    strength: int = 10
    dexterity: int = 10
    constitution: int = 10
    intelligence: int = 10
    wisdom: int = 10
    charisma: int = 10
    
    def get_modifier(self, ability: str) -> int:
        """Calculate D&D ability modifier"""
        score = getattr(self, ability.lower())
        return (score - 10) // 2
    
    def validate_scores(self) -> bool:
        """Ensure all ability scores are valid (3-20)"""
        for score in [self.strength, self.dexterity, self.constitution, 
                     self.intelligence, self.wisdom, self.charisma]:
            if not (3 <= score <= 20):
                return False
        return True

@dataclass
class Character:
    """Pure character entity with D&D business logic"""
    
    # Core Identity
    name: str
    player_name: str
    discord_user_id: str
    
    # D&D Mechanics
    race: Race
    character_class: CharacterClass
    level: int = 1
    background: str = ""
    
    # Game Stats
    ability_scores: AbilityScores = field(default_factory=AbilityScores)
    current_hp: Optional[int] = None
    max_hp: Optional[int] = None
    
    # Character Details
    equipment: List[str] = field(default_factory=list)
    spells: List[str] = field(default_factory=list)
    affiliations: List[str] = field(default_factory=list)
    personality_traits: List[str] = field(default_factory=list)
    
    # Metadata
    created_at: Optional[str] = None
    last_updated: Optional[str] = None
    
    def __post_init__(self):
        """Validate character data after creation"""
        if not self.ability_scores.validate_scores():
            raise ValueError("Invalid ability scores")
        
        if not (1 <= self.level <= 20):
            raise ValueError("Level must be between 1-20")
        
        if not self.name.strip():
            raise ValueError("Character name cannot be empty")
        
        # Set HP if not provided
        if self.max_hp is None:
            self.max_hp = self.calculate_max_hp()
        if self.current_hp is None:
            self.current_hp = self.max_hp
    
    def calculate_max_hp(self) -> int:
        """Calculate max HP based on class and level"""
        # Hit die by class
        hit_dice = {
            CharacterClass.BARBARIAN: 12,
            CharacterClass.FIGHTER: 10,
            CharacterClass.PALADIN: 10,
            CharacterClass.RANGER: 10,
            CharacterClass.BARD: 8,
            CharacterClass.CLERIC: 8,
            CharacterClass.DRUID: 8,
            CharacterClass.MONK: 8,
            CharacterClass.ROGUE: 8,
            CharacterClass.WARLOCK: 8,
            CharacterClass.SORCERER: 6,
            CharacterClass.WIZARD: 6,
        }
        
        base_hp = hit_dice[self.character_class]
        con_modifier = self.ability_scores.get_modifier("constitution")
        
        # First level: max hit die + con mod
        # Subsequent levels: average hit die + con mod
        if self.level == 1:
            return base_hp + con_modifier
        else:
            avg_per_level = (base_hp // 2) + 1 + con_modifier
            return base_hp + con_modifier + (avg_per_level * (self.level - 1))
    
    def get_initiative_modifier(self) -> int:
        """Get initiative modifier (dex mod)"""
        return self.ability_scores.get_modifier("dexterity")
    
    def level_up(self, new_level: int) -> bool:
        """Level up character with validation"""
        if new_level <= self.level or new_level > 20:
            return False
        
        old_max_hp = self.max_hp
        self.level = new_level
        self.max_hp = self.calculate_max_hp()
        
        # Increase current HP by the difference
        hp_increase = self.max_hp - old_max_hp
        self.current_hp += hp_increase
        
        return True
    
    def heal(self, amount: int) -> int:
        """Heal character, return actual amount healed"""
        if amount <= 0:
            return 0
        
        old_hp = self.current_hp
        self.current_hp = min(self.current_hp + amount, self.max_hp)
        return self.current_hp - old_hp
    
    def take_damage(self, amount: int) -> bool:
        """Take damage, return True if still alive"""
        if amount <= 0:
            return True
        
        self.current_hp = max(0, self.current_hp - amount)
        return self.current_hp > 0
    
    def is_alive(self) -> bool:
        """Check if character is alive"""
        return self.current_hp > 0
    
    def is_conscious(self) -> bool:
        """Check if character is conscious (>0 HP)"""
        return self.current_hp > 0
    
    def get_health_status(self) -> str:
        """Get descriptive health status"""
        if self.current_hp <= 0:
            return "Unconscious"
        
        hp_percentage = self.current_hp / self.max_hp
        if hp_percentage >= 0.9:
            return "Healthy"
        elif hp_percentage >= 0.7:
            return "Slightly Wounded"
        elif hp_percentage >= 0.5:
            return "Wounded"
        elif hp_percentage >= 0.25:
            return "Badly Wounded"
        else:
            return "Critically Wounded"
    
    def can_cast_spells(self) -> bool:
        """Check if this class can cast spells"""
        spellcaster_classes = {
            CharacterClass.WIZARD, CharacterClass.SORCERER, CharacterClass.CLERIC,
            CharacterClass.DRUID, CharacterClass.BARD, CharacterClass.WARLOCK,
            CharacterClass.PALADIN, CharacterClass.RANGER
        }
        return self.character_class in spellcaster_classes
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization"""
        return {
            "name": self.name,
            "player_name": self.player_name,
            "discord_user_id": self.discord_user_id,
            "race": self.race.value,
            "character_class": self.character_class.value,
            "level": self.level,
            "background": self.background,
            "ability_scores": {
                "strength": self.ability_scores.strength,
                "dexterity": self.ability_scores.dexterity,
                "constitution": self.ability_scores.constitution,
                "intelligence": self.ability_scores.intelligence,
                "wisdom": self.ability_scores.wisdom,
                "charisma": self.ability_scores.charisma,
            },
            "current_hp": self.current_hp,
            "max_hp": self.max_hp,
            "equipment": self.equipment,
            "spells": self.spells,
            "affiliations": self.affiliations,
            "personality_traits": self.personality_traits,
            "created_at": self.created_at,
            "last_updated": self.last_updated,
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> "Character":
        """Create character from dictionary"""
        ability_scores = AbilityScores(**data.get("ability_scores", {}))
        
        return cls(
            name=data["name"],
            player_name=data["player_name"],
            discord_user_id=data["discord_user_id"],
            race=Race(data["race"]),
            character_class=CharacterClass(data["character_class"]),
            level=data["level"],
            background=data.get("background", ""),
            ability_scores=ability_scores,
            current_hp=data.get("current_hp"),
            max_hp=data.get("max_hp"),
            equipment=data.get("equipment", []),
            spells=data.get("spells", []),
            affiliations=data.get("affiliations", []),
            personality_traits=data.get("personality_traits", []),
            created_at=data.get("created_at"),
            last_updated=data.get("last_updated"),
        )