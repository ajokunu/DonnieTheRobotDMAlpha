# character_system/species_2024.py
"""
D&D 5e 2024 Species Data
Complete species definitions following 2024 Player's Handbook
"""

SPECIES_2024 = {
    "human": {
        "size": "Medium",
        "speed": 30,
        "creature_type": "Humanoid",
        "life_span": "About 100 years",
        "traits": {
            "resourceful": "You gain Heroic Inspiration whenever you finish a Long Rest.",
            "skillful": "You gain proficiency in one skill of your choice.",
            "versatile": "You gain the Skilled feat or another 1st-level feat of your choice."
        },
        "languages": ["Common", "One language of your choice"],
        "ability_score_increase": "Increase one ability score by 2 and another by 1, or increase three different ability scores by 1 each."
    },
    "elf": {
        "size": "Medium", 
        "speed": 30,
        "creature_type": "Humanoid",
        "life_span": "750 years",
        "traits": {
            "darkvision": "You can see in dim light within 60 feet as if it were bright light and in darkness as if it were dim light.",
            "elven_lineage": "You are part of an elven lineage that grants you supernatural abilities. Choose a lineage: Drow, High Elf, or Wood Elf.",
            "fey_ancestry": "You have Advantage on saving throws to avoid or end the Charmed condition.",
            "keen_senses": "You have proficiency in the Perception skill.",
            "trance": "You don't need to sleep, and magic can't force you to sleep. You can finish a Long Rest in 4 hours if you spend those hours in a trancelike meditation."
        },
        "languages": ["Common", "Elvish"],
        "ability_score_increase": "Increase one ability score by 2 and another by 1, or increase three different ability scores by 1 each."
    },
    "dwarf": {
        "size": "Medium",
        "speed": 25,
        "creature_type": "Humanoid", 
        "life_span": "350-400 years",
        "traits": {
            "darkvision": "You can see in dim light within 60 feet as if it were bright light and in darkness as if it were dim light.",
            "dwarven_resilience": "You have Resistance to Poison damage and Advantage on saving throws to avoid or end the Poisoned condition.",
            "dwarven_toughness": "Your Hit Point maximum increases by 1, and it increases by 1 again whenever you gain a level.",
            "forge_wise": "Your mystical connection to metalworking grants you proficiency with Smith's Tools, and you add double your Proficiency Bonus to ability checks made with them.",
            "stonecunning": "As a Bonus Action, you gain Tremorsense with a range of 60 feet for 10 minutes. You must finish a Long Rest before you can use this trait again."
        },
        "languages": ["Common", "Dwarvish"],
        "ability_score_increase": "Increase one ability score by 2 and another by 1, or increase three different ability scores by 1 each."
    },
    "halfling": {
        "size": "Small",
        "speed": 25,
        "creature_type": "Humanoid",
        "life_span": "About 150 years",
        "traits": {
            "brave": "You have Advantage on saving throws to avoid or end the Frightened condition.",
            "halfling_nimbleness": "You can move through the space of any creature that is a size larger than you, but you can't stop in the same space.",
            "luck": "When you roll a 1 on an attack roll, ability check, or saving throw, you can reroll the die, and you must use the new roll.",
            "naturally_stealthy": "You can take the Hide action even when you are obscured only by a creature that is at least one size larger than you."
        },
        "languages": ["Common", "Halfling"],
        "ability_score_increase": "Increase one ability score by 2 and another by 1, or increase three different ability scores by 1 each."
    },
    "dragonborn": {
        "size": "Medium",
        "speed": 30,
        "creature_type": "Humanoid",
        "life_span": "About 80 years",
        "traits": {
            "draconic_ancestry": "Your lineage stems from a dragon. Choose the type of dragon from the Draconic Ancestry table. Your choice affects your Breath Weapon and Damage Resistance traits.",
            "breath_weapon": "As an Action, you exhale destructive energy in a 15-foot cone. Each creature in that area must make a Dexterity saving throw (DC = 8 + your Constitution modifier + your Proficiency Bonus). On a failed save, a creature takes 1d10 + your character level in damage of the type determined by your Draconic Ancestry. On a successful save, it takes half damage. You can use this trait a number of times equal to your Proficiency Bonus, and you regain all expended uses when you finish a Long Rest.",
            "damage_resistance": "You have Resistance to the damage type determined by your Draconic Ancestry.",
            "draconic_flight": "As a Bonus Action, you sprout spectral wings that last for 10 minutes or until you're Incapacitated. During this time, you have a Fly Speed equal to your Speed. Your wings appear to be made of the same energy as your Breath Weapon. Once you use this trait, you can't use it again until you finish a Long Rest."
        },
        "languages": ["Common", "Draconic"],
        "ability_score_increase": "Increase one ability score by 2 and another by 1, or increase three different ability scores by 1 each."
    },
    "gnome": {
        "size": "Small",
        "speed": 25,
        "creature_type": "Humanoid",
        "life_span": "425 years",
        "traits": {
            "darkvision": "You can see in dim light within 60 feet as if it were bright light and in darkness as if it were dim light.",
            "gnomish_cunning": "You have Advantage on Intelligence, Wisdom, and Charisma saving throws.",
            "gnomish_lineage": "You are part of a gnomish lineage that grants you supernatural abilities. Choose a lineage: Forest Gnome or Rock Gnome."
        },
        "languages": ["Common", "Gnomish"],
        "ability_score_increase": "Increase one ability score by 2 and another by 1, or increase three different ability scores by 1 each."
    },
    "half-elf": {
        "size": "Medium",
        "speed": 30,
        "creature_type": "Humanoid",
        "life_span": "About 180 years",
        "traits": {
            "darkvision": "You can see in dim light within 60 feet as if it were bright light and in darkness as if it were dim light.",
            "fey_ancestry": "You have Advantage on saving throws to avoid or end the Charmed condition.",
            "versatile": "You gain the Skilled feat or another 1st-level feat of your choice."
        },
        "languages": ["Common", "Elvish", "One language of your choice"],
        "ability_score_increase": "Increase one ability score by 2 and another by 1, or increase three different ability scores by 1 each."
    },
    "half-orc": {
        "size": "Medium",
        "speed": 30,
        "creature_type": "Humanoid",
        "life_span": "About 75 years",
        "traits": {
            "adrenaline_rush": "You can take the Dash action as a Bonus Action. When you do so, you gain a number of Temporary Hit Points equal to your Proficiency Bonus. You can use this trait a number of times equal to your Proficiency Bonus, and you regain all expended uses when you finish a Long Rest.",
            "darkvision": "You can see in dim light within 60 feet as if it were bright light and in darkness as if it were dim light.",
            "relentless_endurance": "When you are reduced to 0 Hit Points but not killed outright, you can drop to 1 Hit Point instead. Once you use this trait, you can't do so again until you finish a Long Rest.",
            "savage_attacks": "When you score a Critical Hit with an attack roll, you can roll one of the attack's damage dice one additional time and add it to the extra damage of the Critical Hit."
        },
        "languages": ["Common", "Orc"],
        "ability_score_increase": "Increase one ability score by 2 and another by 1, or increase three different ability scores by 1 each."
    },
    "tiefling": {
        "size": "Medium",
        "speed": 30,
        "creature_type": "Humanoid",
        "life_span": "About 100 years",
        "traits": {
            "darkvision": "You can see in dim light within 60 feet as if it were bright light and in darkness as if it were dim light.",
            "fiendish_legacy": "You are the recipient of a fiendish legacy that grants you supernatural abilities. Choose a legacy: Abyssal, Chthonic, or Infernal.",
            "otherworldly_presence": "You know the Thaumaturgy cantrip. When you cast it with this trait, the spell uses the same spellcasting ability you use for your Fiendish Legacy spells."
        },
        "languages": ["Common", "Infernal"],
        "ability_score_increase": "Increase one ability score by 2 and another by 1, or increase three different ability scores by 1 each."
    }
}