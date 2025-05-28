# character_system/backgrounds_2024.py
"""
D&D 5e 2024 Backgrounds Data
Complete background definitions following 2024 Player's Handbook
"""

BACKGROUNDS_2024 = {
    "acolyte": {
        "description": "You spent your early life in a religious community, studying sacred texts and serving in temples.",
        "skill_proficiencies": ["Insight", "Religion"],
        "languages": 2,
        "equipment": ["Holy symbol", "Prayer book", "5 sticks of incense", "Vestments", "Common clothes", "Belt pouch with 15 gp"],
        "feature": "Shelter of the Faithful",
        "suggested_characteristics": {
            "personality_traits": [
                "I idolize a particular hero of my faith, and constantly refer to that person's deeds and example.",
                "I can find common ground between the fiercest enemies, empathizing with them and always working toward peace."
            ],
            "ideals": ["Tradition", "Charity", "Change", "Power", "Faith", "Aspiration"],
            "bonds": ["I would die to recover an ancient relic of my faith that was lost long ago."],
            "flaws": ["I judge others harshly, and myself even more severely."]
        }
    },
    "criminal": {
        "description": "You are an experienced criminal with a history of breaking the law.",
        "skill_proficiencies": ["Deception", "Stealth"],
        "tool_proficiencies": ["Thieves' tools", "One type of gaming set"],
        "equipment": ["Crowbar", "Dark common clothes with hood", "Belt pouch with 15 gp"],
        "feature": "Criminal Contact",
        "criminal_specialty": ["Blackmailer", "Burglar", "Enforcer", "Fence", "Highway robber", "Hired killer", "Pickpocket", "Smuggler"],
        "suggested_characteristics": {
            "personality_traits": [
                "I always have a plan for what to do when things go wrong.",
                "I am always calm, no matter what the situation. I never raise my voice or let my emotions control me."
            ],
            "ideals": ["Honor", "Freedom", "Charity", "Greed", "People", "Redemption"],
            "bonds": ["I'm trying to pay off an old debt I owe to a generous benefactor."],
            "flaws": ["When I see something valuable, I can't think about anything but how to steal it."]
        }
    },
    "folk_hero": {
        "description": "You come from a humble social rank, but you are destined for so much more.",
        "skill_proficiencies": ["Animal Handling", "Survival"],
        "tool_proficiencies": ["One type of artisan's tools", "Vehicles (land)"],
        "equipment": ["Artisan's tools", "Shovel", "Iron pot", "Common clothes", "Belt pouch with 10 gp"],
        "feature": "Rustic Hospitality",
        "defining_event": ["I stood up to a tyrant's agents.", "I saved people during a natural disaster.", "I stood alone against a terrible monster."],
        "suggested_characteristics": {
            "personality_traits": [
                "I judge people by their actions, not their words.",
                "If someone is in trouble, I'm always ready to lend help."
            ],
            "ideals": ["Respect", "Fairness", "Freedom", "Might", "Sincerity", "Destiny"],
            "bonds": ["I have a family, but I have no idea where they are. I hope to see them again one day."],
            "flaws": ["The tyrant who rules my land will stop at nothing to see me killed."]
        }
    },
    "noble": {
        "description": "You understand wealth, power, and privilege and carry a noble title.",
        "skill_proficiencies": ["History", "Persuasion"],
        "tool_proficiencies": ["One type of gaming set"],
        "languages": 1,
        "equipment": ["Signet ring", "Scroll of pedigree", "Fine clothes", "Belt pouch with 25 gp"],
        "feature": "Position of Privilege",
        "suggested_characteristics": {
            "personality_traits": [
                "My eloquent flattery makes everyone I talk to feel like the most wonderful and important person in the world.",
                "Despite my noble birth, I do not place myself above other folk. We all have the same blood."
            ],
            "ideals": ["Respect", "Responsibility", "Noble Obligation", "Power", "Family", "Noble Obligation"],
            "bonds": ["The common folk must see me as a hero of the people."],
            "flaws": ["I secretly believe that everyone is beneath me."]
        }
    },
    "sage": {
        "description": "You spent years learning the lore of the multiverse and uncovering its secrets.",
        "skill_proficiencies": ["Arcana", "History"],
        "languages": 2,
        "equipment": ["Bottle of black ink", "Quill", "Small knife", "Letter from colleague", "Common clothes", "Belt pouch with 10 gp"],
        "feature": "Researcher",
        "specialty": ["Alchemist", "Astronomer", "Discredited academic", "Librarian", "Professor", "Researcher", "Wizard's apprentice", "Scribe"],
        "suggested_characteristics": {
            "personality_traits": [
                "I use polysyllabic words that convey the impression of great erudition.",
                "I've read every book in the world's greatest libraries— or I like to boast that I have."
            ],
            "ideals": ["Knowledge", "Beauty", "Logic", "No Limits", "Power", "Self-Improvement"],
            "bonds": ["The workshop where I learned my trade is the most important place in the world to me."],
            "flaws": ["I am horribly, horribly awkward in social situations."]
        }
    },
    "soldier": {
        "description": "You had a military rank and fought in organized campaigns.",
        "skill_proficiencies": ["Athletics", "Intimidation"],
        "tool_proficiencies": ["One type of gaming set", "Vehicles (land)"],
        "equipment": ["Insignia of rank", "Trophy from fallen enemy", "Deck of cards", "Common clothes", "Belt pouch with 10 gp"],
        "feature": "Military Rank",
        "specialty": ["Officer", "Scout", "Infantry", "Cavalry", "Healer", "Quartermaster", "Standard bearer", "Support staff"],
        "suggested_characteristics": {
            "personality_traits": [
                "I'm always respectful and polite.",
                "I'm haunted by memories of war. I can't get the images of violence out of my mind."
            ],
            "ideals": ["Greater Good", "Responsibility", "Independence", "Might", "Live and Let Live", "Nation"],
            "bonds": ["I would still lay down my life for the people I served with."],
            "flaws": ["I made a terrible mistake in battle that cost many lives— and I would do anything to keep that mistake secret."]
        }
    },
    "charlatan": {
        "description": "You have always had a way with people. You know what makes them tick.",
        "skill_proficiencies": ["Deception", "Sleight of Hand"],
        "tool_proficiencies": ["Forgery kit", "One type of gaming set"],
        "equipment": ["Fine clothes", "Signet ring of an imaginary person", "15 gp"],
        "feature": "False Identity"
    },
    "entertainer": {
        "description": "You thrive in front of an audience, performing for their amusement.",
        "skill_proficiencies": ["Acrobatics", "Performance"],
        "tool_proficiencies": ["Disguise kit", "One type of musical instrument"],
        "equipment": ["Musical instrument", "Favor of an admirer", "Costume", "15 gp"],
        "feature": "By Popular Demand"
    },
    "guild_artisan": {
        "description": "You are a member of an artisan's guild, skilled in a particular field.",
        "skill_proficiencies": ["Insight", "Persuasion"],
        "tool_proficiencies": ["One type of artisan's tools"],
        "languages": 1,
        "equipment": ["Artisan's tools", "Letter of introduction from guild", "Traveler's clothes", "15 gp"],
        "feature": "Guild Membership"
    },
    "hermit": {
        "description": "You lived in seclusion for a formative part of your life.",
        "skill_proficiencies": ["Medicine", "Religion"],
        "tool_proficiencies": ["Herbalism kit"],
        "languages": 1,
        "equipment": ["Herbalism kit", "Scroll case", "Blanket", "5 gp"],
        "feature": "Discovery"
    },
    "outlander": {
        "description": "You grew up in the wilds, far from civilization and the comforts of town and technology.",
        "skill_proficiencies": ["Athletics", "Survival"],
        "tool_proficiencies": ["One type of musical instrument"],
        "languages": 1,
        "equipment": ["Staff", "Hunting trap", "Traveler's clothes", "Belt pouch with 10 gp"],
        "feature": "Wanderer"
    },
    "sailor": {
        "description": "You sailed on a seagoing vessel for years, working as crew.",
        "skill_proficiencies": ["Athletics", "Perception"],
        "tool_proficiencies": ["Navigator's tools", "Vehicles (water)"],
        "equipment": ["Belaying pin", "50 feet of silk rope", "Lucky charm", "Common clothes", "Belt pouch with 10 gp"],
        "feature": "Ship's Passage"
    }
}