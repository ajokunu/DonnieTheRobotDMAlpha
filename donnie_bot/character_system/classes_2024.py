# character_system/classes_2024.py
"""
D&D 5e 2024 Classes Data
Complete class definitions following 2024 Player's Handbook
"""

CLASSES_2024 = {
    "barbarian": {
        "hit_die": 12,
        "primary_abilities": ["Strength"],
        "saving_throw_proficiencies": ["Strength", "Constitution"],
        "armor_proficiencies": ["Light Armor", "Medium Armor", "Shields"],
        "weapon_proficiencies": ["Simple Weapons", "Martial Weapons"],
        "skill_proficiencies": {
            "choose": 2,
            "from": ["Animal Handling", "Athletics", "Intimidation", "Nature", "Perception", "Survival"]
        },
        "equipment": {
            "armor": "Leather Armor",
            "weapons": ["Greataxe", "2 Handaxes", "4 Javelins"],
            "tools": [],
            "other": "Explorer's Pack"
        },
        "spellcasting": False,
        "features": {
            1: ["Rage", "Unarmored Defense"],
            2: ["Danger Sense", "Reckless Attack"],
            3: ["Primal Knowledge", "Primal Path"],
            4: ["Ability Score Improvement"],
            5: ["Extra Attack", "Fast Movement"]
        }
    },
    "bard": {
        "hit_die": 8,
        "primary_abilities": ["Charisma"],
        "saving_throw_proficiencies": ["Dexterity", "Charisma"],
        "armor_proficiencies": ["Light Armor"],
        "weapon_proficiencies": ["Simple Weapons", "Hand Crossbows", "Longswords", "Rapiers", "Shortswords"],
        "tool_proficiencies": ["Three Musical Instruments"],
        "skill_proficiencies": {
            "choose": 3,
            "from": "Any three skills of your choice"
        },
        "equipment": {
            "armor": "Leather Armor",
            "weapons": ["Rapier", "Dagger", "Simple Weapon"],
            "tools": ["Musical Instrument"],
            "other": "Entertainer's Pack"
        },
        "spellcasting": True,
        "spellcasting_ability": "Charisma",
        "ritual_casting": True,
        "features": {
            1: ["Bardic Inspiration", "Spellcasting"],
            2: ["Expertise", "Jack of All Trades"],
            3: ["Bard College"],
            4: ["Ability Score Improvement"],
            5: ["Bardic Inspiration Improvement", "Font of Inspiration"]
        }
    },
    "cleric": {
        "hit_die": 8,
        "primary_abilities": ["Wisdom"],
        "saving_throw_proficiencies": ["Wisdom", "Charisma"],
        "armor_proficiencies": ["Light Armor", "Medium Armor", "Shields"],
        "weapon_proficiencies": ["Simple Weapons"],
        "skill_proficiencies": {
            "choose": 2,
            "from": ["History", "Insight", "Medicine", "Persuasion", "Religion"]
        },
        "equipment": {
            "armor": "Scale Mail",
            "weapons": ["Mace", "Light Crossbow"],
            "tools": [],
            "other": "Priest's Pack"
        },
        "spellcasting": True,
        "spellcasting_ability": "Wisdom",
        "ritual_casting": True,
        "features": {
            1: ["Divine Domain", "Spellcasting"],
            2: ["Channel Divinity", "Domain Feature"],
            3: [],
            4: ["Ability Score Improvement"],
            5: ["Destroy Undead"]
        }
    },
    "druid": {
        "hit_die": 8,
        "primary_abilities": ["Wisdom"],
        "saving_throw_proficiencies": ["Intelligence", "Wisdom"],
        "armor_proficiencies": ["Light Armor", "Medium Armor", "Shields (non-metal)"],
        "weapon_proficiencies": ["Clubs", "Daggers", "Darts", "Javelins", "Maces", "Quarterstaffs", "Scimitars", "Sickles", "Slings", "Spears"],
        "skill_proficiencies": {
            "choose": 2,
            "from": ["Arcana", "Animal Handling", "Insight", "Medicine", "Nature", "Perception", "Religion", "Survival"]
        },
        "equipment": {
            "armor": "Leather Armor",
            "weapons": ["Scimitar", "Shield", "Dart"],
            "tools": [],
            "other": "Explorer's Pack"
        },
        "spellcasting": True,
        "spellcasting_ability": "Wisdom",
        "ritual_casting": True,
        "features": {
            1: ["Druidcraft", "Spellcasting"],
            2: ["Wild Shape", "Wild Companion", "Druid Circle"],
            3: [],
            4: ["Ability Score Improvement"],
            5: []
        }
    },
    "fighter": {
        "hit_die": 10,
        "primary_abilities": ["Strength", "Dexterity"],
        "saving_throw_proficiencies": ["Strength", "Constitution"],
        "armor_proficiencies": ["All Armor", "Shields"],
        "weapon_proficiencies": ["Simple Weapons", "Martial Weapons"],
        "skill_proficiencies": {
            "choose": 2,
            "from": ["Acrobatics", "Animal Handling", "Athletics", "History", "Insight", "Intimidation", "Perception", "Survival"]
        },
        "equipment": {
            "armor": "Chain Mail",
            "weapons": ["Longsword", "Shield", "Light Crossbow"],
            "tools": [],
            "other": "Dungeoneer's Pack"
        },
        "spellcasting": False,
        "features": {
            1: ["Fighting Style", "Second Wind"],
            2: ["Action Surge"],
            3: ["Martial Archetype"],
            4: ["Ability Score Improvement"],
            5: ["Extra Attack"]
        }
    },
    "monk": {
        "hit_die": 8,
        "primary_abilities": ["Dexterity", "Wisdom"],
        "saving_throw_proficiencies": ["Strength", "Dexterity"],
        "armor_proficiencies": [],
        "weapon_proficiencies": ["Simple Weapons", "Shortswords"],
        "skill_proficiencies": {
            "choose": 2,
            "from": ["Acrobatics", "Athletics", "History", "Insight", "Religion", "Stealth"]
        },
        "equipment": {
            "armor": "Unarmored Defense",
            "weapons": ["Shortsword", "Simple Weapon"],
            "tools": [],
            "other": "Dungeoneer's Pack"
        },
        "spellcasting": False,
        "features": {
            1: ["Unarmored Defense", "Martial Arts"],
            2: ["Ki", "Unarmored Movement"],
            3: ["Monastic Tradition", "Deflect Missiles"],
            4: ["Ability Score Improvement"],
            5: ["Extra Attack", "Stunning Strike"]
        }
    },
    "paladin": {
        "hit_die": 10,
        "primary_abilities": ["Strength", "Charisma"],
        "saving_throw_proficiencies": ["Wisdom", "Charisma"],
        "armor_proficiencies": ["All Armor", "Shields"],
        "weapon_proficiencies": ["Simple Weapons", "Martial Weapons"],
        "skill_proficiencies": {
            "choose": 2,
            "from": ["Athletics", "Insight", "Intimidation", "Medicine", "Persuasion", "Religion"]
        },
        "equipment": {
            "armor": "Chain Mail",
            "weapons": ["Longsword", "Shield", "5 Javelins"],
            "tools": [],
            "other": "Explorer's Pack"
        },
        "spellcasting": True,
        "spellcasting_ability": "Charisma",
        "ritual_casting": False,
        "features": {
            1: ["Divine Sense", "Lay on Hands"],
            2: ["Fighting Style", "Spellcasting", "Divine Smite"],
            3: ["Divine Health", "Sacred Oath"],
            4: ["Ability Score Improvement"],
            5: ["Extra Attack"]
        }
    },
    "ranger": {
        "hit_die": 10,
        "primary_abilities": ["Dexterity", "Wisdom"],
        "saving_throw_proficiencies": ["Strength", "Dexterity"],
        "armor_proficiencies": ["Light Armor", "Medium Armor", "Shields"],
        "weapon_proficiencies": ["Simple Weapons", "Martial Weapons"],
        "skill_proficiencies": {
            "choose": 3,
            "from": ["Animal Handling", "Athletics", "Insight", "Investigation", "Nature", "Perception", "Stealth", "Survival"]
        },
        "equipment": {
            "armor": "Studded Leather",
            "weapons": ["Shortsword", "Simple Weapon", "Longbow"],
            "tools": [],
            "other": "Explorer's Pack"
        },
        "spellcasting": True,
        "spellcasting_ability": "Wisdom",
        "ritual_casting": False,
        "features": {
            1: ["Favored Enemy", "Natural Explorer"],
            2: ["Fighting Style", "Spellcasting"],
            3: ["Ranger Archetype", "Primeval Awareness"],
            4: ["Ability Score Improvement"],
            5: ["Extra Attack"]
        }
    },
    "rogue": {
        "hit_die": 8,
        "primary_abilities": ["Dexterity"],
        "saving_throw_proficiencies": ["Dexterity", "Intelligence"],
        "armor_proficiencies": ["Light Armor"],
        "weapon_proficiencies": ["Simple Weapons", "Hand Crossbows", "Longswords", "Rapiers", "Shortswords"],
        "skill_proficiencies": {
            "choose": 4,
            "from": ["Acrobatics", "Athletics", "Deception", "Insight", "Intimidation", "Investigation", "Perception", "Performance", "Persuasion", "Sleight of Hand", "Stealth"]
        },
        "equipment": {
            "armor": "Leather Armor",
            "weapons": ["Rapier", "Shortbow", "2 Daggers", "Thieves' Tools"],
            "tools": ["Thieves' Tools"],
            "other": "Burglar's Pack"
        },
        "spellcasting": False,
        "features": {
            1: ["Expertise", "Sneak Attack", "Thieves' Cant"],
            2: ["Cunning Action"],
            3: ["Roguish Archetype"],
            4: ["Ability Score Improvement"],
            5: ["Uncanny Dodge"]
        }
    },
    "sorcerer": {
        "hit_die": 6,
        "primary_abilities": ["Charisma"],
        "saving_throw_proficiencies": ["Constitution", "Charisma"],
        "armor_proficiencies": [],
        "weapon_proficiencies": ["Daggers", "Darts", "Slings", "Quarterstaffs", "Light Crossbows"],
        "skill_proficiencies": {
            "choose": 2,
            "from": ["Arcana", "Deception", "Insight", "Intimidation", "Persuasion", "Religion"]
        },
        "equipment": {
            "armor": "None",
            "weapons": ["Light Crossbow", "Simple Weapon"],
            "tools": [],
            "other": "Dungeoneer's Pack"
        },
        "spellcasting": True,
        "spellcasting_ability": "Charisma",
        "ritual_casting": False,
        "features": {
            1: ["Spellcasting", "Sorcerous Origin"],
            2: ["Font of Magic"],
            3: ["Metamagic"],
            4: ["Ability Score Improvement"],
            5: []
        }
    },
    "warlock": {
        "hit_die": 8,
        "primary_abilities": ["Charisma"],
        "saving_throw_proficiencies": ["Wisdom", "Charisma"],
        "armor_proficiencies": ["Light Armor"],
        "weapon_proficiencies": ["Simple Weapons"],
        "skill_proficiencies": {
            "choose": 2,
            "from": ["Arcana", "Deception", "History", "Intimidation", "Investigation", "Nature", "Religion"]
        },
        "equipment": {
            "armor": "Leather Armor",
            "weapons": ["Light Crossbow", "Simple Weapon", "2 Daggers"],
            "tools": [],
            "other": "Scholar's Pack"
        },
        "spellcasting": True,
        "spellcasting_ability": "Charisma",
        "ritual_casting": False,
        "pact_magic": True,
        "features": {
            1: ["Otherworldly Patron", "Pact Magic"],
            2: ["Eldritch Invocations"],
            3: ["Pact Boon"],
            4: ["Ability Score Improvement"],
            5: []
        }
    },
    "wizard": {
        "hit_die": 6,
        "primary_abilities": ["Intelligence"],
        "saving_throw_proficiencies": ["Intelligence", "Wisdom"],
        "armor_proficiencies": [],
        "weapon_proficiencies": ["Daggers", "Darts", "Slings", "Quarterstaffs", "Light Crossbows"],
        "skill_proficiencies": {
            "choose": 2,
            "from": ["Arcana", "History", "Insight", "Investigation", "Medicine", "Religion"]
        },
        "equipment": {
            "armor": "None",
            "weapons": ["Dagger", "Simple Weapon"],
            "tools": [],
            "other": "Scholar's Pack"
        },
        "spellcasting": True,
        "spellcasting_ability": "Intelligence",
        "ritual_casting": True,
        "features": {
            1: ["Spellcasting", "Arcane Recovery"],
            2: ["Arcane Tradition"],
            3: ["Cantrip Formulas"],
            4: ["Ability Score Improvement"],
            5: []
        }
    }
}

def get_class_spell_slots_2024(character_class: str, level: int) -> dict:
    """Get spell slots for a class at specific level following 2024 rules"""
    
    # Full caster progression (Bard, Cleric, Druid, Sorcerer, Wizard)
    full_caster_slots = {
        1: [2, 0, 0, 0, 0, 0, 0, 0, 0],
        2: [3, 0, 0, 0, 0, 0, 0, 0, 0],
        3: [4, 2, 0, 0, 0, 0, 0, 0, 0],
        4: [4, 3, 0, 0, 0, 0, 0, 0, 0],
        5: [4, 3, 2, 0, 0, 0, 0, 0, 0],
        6: [4, 3, 3, 0, 0, 0, 0, 0, 0],
        7: [4, 3, 3, 1, 0, 0, 0, 0, 0],
        8: [4, 3, 3, 2, 0, 0, 0, 0, 0],
        9: [4, 3, 3, 3, 1, 0, 0, 0, 0],
        10: [4, 3, 3, 3, 2, 0, 0, 0, 0],
        11: [4, 3, 3, 3, 2, 1, 0, 0, 0],
        12: [4, 3, 3, 3, 2, 1, 0, 0, 0],
        13: [4, 3, 3, 3, 2, 1, 1, 0, 0],
        14: [4, 3, 3, 3, 2, 1, 1, 0, 0],
        15: [4, 3, 3, 3, 2, 1, 1, 1, 0],
        16: [4, 3, 3, 3, 2, 1, 1, 1, 0],
        17: [4, 3, 3, 3, 2, 1, 1, 1, 1],
        18: [4, 3, 3, 3, 3, 1, 1, 1, 1],
        19: [4, 3, 3, 3, 3, 2, 1, 1, 1],
        20: [4, 3, 3, 3, 3, 2, 2, 1, 1]
    }
    
    # Half caster progression (Paladin, Ranger) 
    half_caster_slots = {
        2: [2, 0, 0, 0, 0, 0, 0, 0, 0],
        3: [3, 0, 0, 0, 0, 0, 0, 0, 0],
        5: [4, 2, 0, 0, 0, 0, 0, 0, 0],
        6: [4, 2, 0, 0, 0, 0, 0, 0, 0],
        7: [4, 3, 0, 0, 0, 0, 0, 0, 0],
        9: [4, 3, 2, 0, 0, 0, 0, 0, 0],
        10: [4, 3, 2, 0, 0, 0, 0, 0, 0],
        11: [4, 3, 3, 0, 0, 0, 0, 0, 0],
        13: [4, 3, 3, 1, 0, 0, 0, 0, 0],
        14: [4, 3, 3, 1, 0, 0, 0, 0, 0],
        15: [4, 3, 3, 2, 0, 0, 0, 0, 0],
        17: [4, 3, 3, 3, 1, 0, 0, 0, 0],
        18: [4, 3, 3, 3, 1, 0, 0, 0, 0],
        19: [4, 3, 3, 3, 2, 0, 0, 0, 0],
        20: [4, 3, 3, 3, 2, 0, 0, 0, 0]
    }
    
    # Warlock pact magic (unique progression)
    warlock_slots = {
        1: [1, 0, 0, 0, 0, 0, 0, 0, 0],
        2: [2, 0, 0, 0, 0, 0, 0, 0, 0],
        3: [0, 2, 0, 0, 0, 0, 0, 0, 0],
        4: [0, 2, 0, 0, 0, 0, 0, 0, 0],
        5: [0, 0, 2, 0, 0, 0, 0, 0, 0],
        6: [0, 0, 2, 0, 0, 0, 0, 0, 0],
        7: [0, 0, 0, 2, 0, 0, 0, 0, 0],
        8: [0, 0, 0, 2, 0, 0, 0, 0, 0],
        9: [0, 0, 0, 0, 2, 0, 0, 0, 0],
        10: [0, 0, 0, 0, 2, 0, 0, 0, 0],
        11: [0, 0, 0, 0, 3, 0, 0, 0, 0],
        12: [0, 0, 0, 0, 3, 0, 0, 0, 0],
        13: [0, 0, 0, 0, 3, 0, 0, 0, 0],
        14: [0, 0, 0, 0, 3, 0, 0, 0, 0],
        15: [0, 0, 0, 0, 3, 0, 0, 0, 0],
        16: [0, 0, 0, 0, 3, 0, 0, 0, 0],
        17: [0, 0, 0, 0, 4, 0, 0, 0, 0],
        18: [0, 0, 0, 0, 4, 0, 0, 0, 0],
        19: [0, 0, 0, 0, 4, 0, 0, 0, 0],
        20: [0, 0, 0, 0, 4, 0, 0, 0, 0]
    }
    
    class_lower = character_class.lower()
    
    if class_lower == "warlock":
        slots = warlock_slots.get(level, [0] * 9)
    elif class_lower in ["paladin", "ranger"]:
        slots = half_caster_slots.get(level, [0] * 9)
    elif class_lower in ["bard", "cleric", "druid", "sorcerer", "wizard"]:
        slots = full_caster_slots.get(level, [0] * 9)
    else:
        slots = [0] * 9  # Non-spellcasting classes
    
    return {
        "1st": slots[0], "2nd": slots[1], "3rd": slots[2],
        "4th": slots[3], "5th": slots[4], "6th": slots[5],
        "7th": slots[6], "8th": slots[7], "9th": slots[8]
    }