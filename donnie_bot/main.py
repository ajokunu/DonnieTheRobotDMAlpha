# main.py - UPDATED WITH STATE SYNCHRONIZATION FIXES
# Replace the existing import section with this:

import discord
from discord.ext import commands
from discord import app_commands
import anthropic
import asyncio
import os
from dotenv import load_dotenv
import random
from typing import Optional
import aiohttp
import tempfile
import io
from datetime import datetime

# Combat system imports
import json
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from enum import Enum

load_dotenv()

# ====== FIXED DATABASE AND EPISODE MANAGEMENT IMPORTS ======
# Database imports - NOW WORKING!
try:
    from database import init_database, close_database
    from database.operations import EpisodeOperations, CharacterOperations, GuildOperations, DatabaseOperationError
    print("✅ Database operations imported successfully")
    DATABASE_AVAILABLE = True
except ImportError as e:
    print(f"❌ Database operations failed to import: {e}")
    print("Make sure database/__init__.py and database/operations.py exist")
    DATABASE_AVAILABLE = False
    # Create fallback empty classes to prevent crashes
    class EpisodeOperations:
        @staticmethod
        def create_episode(*args, **kwargs): pass
        @staticmethod
        def get_current_episode(*args, **kwargs): return None
        @staticmethod
        def update_session_history(*args, **kwargs): pass
        @staticmethod
        def end_episode(*args, **kwargs): pass
    
    class CharacterOperations:
        @staticmethod
        def create_character_snapshot(*args, **kwargs): pass
    
    class GuildOperations:
        @staticmethod
        def get_guild_settings(*args, **kwargs): return {}
        @staticmethod
        def update_guild_settings(*args, **kwargs): pass
    
    def init_database(): pass
    def close_database(): pass

# Episode Management imports - NOW WORKING!
try:
    from episode_manager import EpisodeCommands
    print("✅ Episode management imported successfully")
    EPISODE_MANAGER_AVAILABLE = True
except ImportError as e:
    print(f"❌ Episode management failed to import: {e}")
    print("Episode management will be disabled")
    EPISODE_MANAGER_AVAILABLE = False
    EpisodeCommands = None

# Character Progression imports - NOW WORKING!  
try:
    from character_tracker import CharacterProgressionCommands
    print("✅ Character progression imported successfully")
    CHARACTER_PROGRESSION_AVAILABLE = True
except ImportError as e:
    print(f"❌ Character progression failed to import: {e}")
    print("Character progression tracking will be disabled")
    CHARACTER_PROGRESSION_AVAILABLE = False
    CharacterProgressionCommands = None

# Audio system imports - WORKING!
try:
    from audio_system import EnhancedVoiceManager
    print("✅ Enhanced audio system imported successfully")
    ENHANCED_AUDIO_AVAILABLE = True
except ImportError as e:
    print(f"⚠️ Enhanced audio system not available: {e}")
    ENHANCED_AUDIO_AVAILABLE = False

# Initialize APIs
claude_client = anthropic.Anthropic(api_key=os.getenv('ANTHROPIC_API_KEY'))

# Discord bot setup with voice intents
intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True  # Required for voice functionality

bot = commands.Bot(command_prefix='/', intents=intents, help_command=None)

# Voice client storage
voice_clients = {}
tts_enabled = {}  # Track TTS status per guild
voice_speed = {}  # Track speech speed per guild (default 1.25)
voice_queue = {}  # Voice queue per guild to prevent overlapping

# Combat state tracking (integrates with existing campaign_context)
combat_state = {
    "active": False,
    "encounter_name": "",
    "round": 1,
    "initiative_order": [],
    "current_turn": 0,
    "monsters": {},
    "combat_log": []
}

# DM Thinking Sounds - ACTUAL sounds, not descriptions
DM_THINKING_SOUNDS = [
    "...Hhhhhmm...",
    "...Aaahhh okay let's try",  # actual throat clearing sound
    "...Uhhhh...huh yes okay...",
    "...Let meeee see...",
    "...Mmm-hmm...",
    "...Ah, okay then...",
    "...Right well okay...",
    "...Well...",
    "...Okay...",
    "...Hmm, hmm...",
    "...Uh-huh...", 
    "...Mmm...",
    "...Oh...",
    "...Alright...",
    "...Err...",
    "...Umm...",
    "...Ah-huh...",
    "...Hmmph...",
    "...alright, alright, alright...",
    "...Let me think...",
]

# Enhanced Storm King's Thunder Campaign Context with Episode Management
campaign_context = {
    "campaign_name": "Storm King's Thunder",
    "setting": "The Sword Coast - Giants have begun raiding settlements across the land. The ancient ordning that kept giant society in check has collapsed, throwing giantkind into chaos.",
    "players": {},
    "characters": {},  # Store character information
    "current_scene": "The village of Nightstone sits eerily quiet. Giant-sized boulders litter the village square, and not a soul can be seen moving in the streets. The party approaches the mysteriously open gates...",
    "session_history": [],
    "session_started": False,
    
    # New Episode Management Fields
    "current_episode": 0,
    "episode_active": False,
    "episode_start_time": None,
    "guild_id": None,  # Track which Discord server this campaign belongs to
}

# Enhanced DM Prompt that includes combat intelligence
ENHANCED_DM_PROMPT = """You are Donnie, a Dungeon Master running Storm King's Thunder for D&D 5th Edition (2024 rules).

SETTING: {setting}
CURRENT SCENE: {current_scene}
RECENT HISTORY: {session_history}
PARTY CHARACTERS: {characters}
PLAYERS: {players}
COMBAT STATUS: {combat_status}

You are running Storm King's Thunder - giants threaten the Sword Coast and the ordning has collapsed.

**COMBAT INTELLIGENCE SYSTEM:**
- DETECT COMBAT: If player action would trigger combat, automatically start encounter
- GENERATE ENCOUNTERS: Create thematically appropriate enemies based on story context
- SMART MONSTERS: Monster behavior based on Intelligence/Wisdom scores
- AUTO-INITIATIVE: Roll initiative for all participants
- TACTICAL AI: Monsters act intelligently based on their stats

**COMBAT DETECTION TRIGGERS:**
- Player attacks or threatens creatures
- Hostile creatures encounter the party
- Story moments require combat resolution
- Environmental dangers become active threats

**ENCOUNTER GENERATION:**
When combat triggers, immediately:
1. Announce combat start
2. Generate 1-3 appropriate monsters based on:
   - Current story location and context
   - Party level and size
   - Storm King's Thunder themes (giants, giant-kin, cultists, etc.)
3. Roll initiative for everyone
4. Begin structured combat

**MONSTER AI BEHAVIOR:**
- Intelligence 3-7: Basic instincts, attack nearest threat
- Intelligence 8-12: Tactical awareness, focus fire, use cover
- Intelligence 13+: Advanced tactics, spells, coordinated attacks
- Wisdom affects perception, environmental awareness, retreat decisions

**D&D 5e 2024 ADHERENCE FRAMEWORK - MANDATORY COMPLIANCE**

**1. COMBAT MECHANICS**
- MANDATORY: Roll initiative for ALL combat encounters
- MANDATORY: Track Action, Bonus Action, Movement, and Reaction separately each turn
- MANDATORY: Load complete stat block for all creatures before combat begins
- MANDATORY: Calculate encounter difficulty using CR guidelines before deployment
- FORMAT: "Initiative: [Character Name] - [Roll+Dex]. Turn: Action/Bonus/Move used this turn"

**2. RESOURCE TRACKING**
- SPELL SLOTS: Track precisely with format "Level X: Used Y/Total Z"
- ABILITIES: Track uses with format "Ability Name: Used X/Y per rest"
- HIT POINTS: Always state current/max format "HP: X/Y"
- EQUIPMENT: Maintain persistent inventory, track ammunition/consumables

**3. EXPERIENCE & LEVELING**
- XP TRACKING: Award XP using encounter values (CR-based) or milestone markers
- LEVEL PROGRESSION: Maximum 1 level per 2-4 sessions unless story milestone reached
- ADVANCEMENT: Follow PHB exactly - spell slots, abilities, proficiency bonus progression

**4. REST SYSTEM**
- SHORT REST: 1 hour, limited healing/ability recovery per PHB
- LONG REST: 8 hours, only after significant story progress or 6-8 encounters
- ADVENTURING DAY: 6-8 encounters between long rests to maintain resource tension

**5. SKILL CHECKS & DCs**
- STANDARD DCs: Easy (10), Medium (15), Hard (20), Nearly Impossible (25)
- ABILITY CHECKS: Always specify which ability + which skill
- ADVANTAGE/DISADVANTAGE: Only grant per specific rules or clear narrative justification

**STAT BLOCK PROTOCOL**
PRE-COMBAT CHECKLIST:
1. LOAD STAT BLOCK: Reference official stat block from Monster Manual/source
2. VERIFY CR: Confirm challenge rating matches party level appropriately
3. CALCULATE ENCOUNTER: Use encounter building guidelines for difficulty
4. PREPARE ABILITIES: Note special attacks, resistances, legendary actions
5. SET INITIATIVE: Have creature's initiative bonus ready

**CRITICAL RULES:**
- DO NOT REVEAL STAT BLOCKS TO PLAYERS
- ALWAYS USE CHARACTER NAMES, NOT DISCORD IDs
- ENFORCE action economy strictly
- Reference PHB/official rules for disputes
- Track resources precisely

**COMBAT FORMAT:**
When combat is active, structure responses as:
```
**COMBAT ROUND [current_round]**
**[current_creature]'s Turn:**
[Action description]
[Dice rolls if needed]
[Damage/effects]
[Next creature prompt]
```

**STORM KING'S THUNDER SPECIFIC:**
- Giants should feel massive and threatening when encountered
- Use vivid descriptions of the Sword Coast setting
- Reference character abilities and backgrounds in responses
- Ask for dice rolls when appropriate (D&D 5e 2024 rules)
- Keep responses 2-4 sentences for real-time play
- Make player choices matter and have consequences
- Create immersive roleplay opportunities
- You are fair but challenging - not too easy, not too harsh

PLAYER ACTION: {player_input}

Respond as Donnie, the Storm King's Thunder DM with intelligent combat automation:"""

# Combat Detection System
async def detect_combat_trigger(player_input: str, current_scene: str) -> Dict:
    """Detect if player action should trigger combat"""
    
    combat_triggers = [
        "attack", "fight", "charge", "ambush", "strike", "shoot", "cast", 
        "sneak attack", "initiative", "draw weapon", "ready spell"
    ]
    
    player_lower = player_input.lower()
    scene_lower = current_scene.lower()
    
    # Check for obvious combat triggers
    trigger_detected = any(trigger in player_lower for trigger in combat_triggers)
    
    # Enhanced detection based on scene context
    if not trigger_detected:
        # Check if scene suggests potential combat
        hostile_indicators = ["giant", "orc", "goblin", "bandit", "monster", "enemy", "threat"]
        scene_has_threats = any(indicator in scene_lower for indicator in hostile_indicators)
        
        approach_actions = ["approach", "enter", "investigate", "search", "explore"]
        player_approaching = any(action in player_lower for action in approach_actions)
        
        if scene_has_threats and player_approaching:
            trigger_detected = True
    
    return {
        "triggered": trigger_detected,
        "confidence": 0.9 if trigger_detected else 0.0,
        "reason": "Combat action detected" if trigger_detected else None
    }

async def generate_story_appropriate_encounter(scene: str, characters: Dict, claude_client) -> Optional[Dict]:
    """Generate combat encounter based on current story context"""
    
    # Calculate party strength
    party_size = len(characters)
    if party_size == 0:
        return None
    
    # Get average party level
    total_levels = sum(char_data.get("character_data", {}).get("level", 1) 
                      for char_data in characters.values())
    avg_level = total_levels // party_size
    
    encounter_prompt = f"""Generate a combat encounter for Storm King's Thunder based on the current scene.

CURRENT SCENE: {scene}

PARTY INFO:
- Size: {party_size} characters
- Average Level: {avg_level}
- Campaign: Storm King's Thunder (giant crisis theme)

REQUIREMENTS:
1. Generate 1-3 enemies that fit the scene naturally
2. Enemies should be thematically appropriate to Storm King's Thunder
3. Encounter should be challenging but fair for the party
4. Include enemy stats: HP, AC, attack bonuses, damage dice

Return a JSON object with this format:
{{
  "encounter_name": "Descriptive encounter name",
  "enemies": [
    {{
      "name": "Enemy Name",
      "count": 1,
      "hp": 30,
      "max_hp": 30,
      "ac": 15,
      "initiative_bonus": 2,
      "intelligence": 8,
      "wisdom": 12,
      "attacks": [
        {{
          "name": "Attack Name",
          "bonus": 5,
          "damage": "1d8+3",
          "type": "slashing"
        }}
      ],
      "special_abilities": ["Ability name if any"],
      "behavior": "aggressive/defensive/tactical/cowardly"
    }}
  ],
  "scene_description": "How the combat begins naturally from the scene"
}}

Make it feel like a natural story progression, not a random encounter."""
    
    try:
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: claude_client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=1000,
                messages=[{"role": "user", "content": encounter_prompt}]
        )
    )
        
        # Handle the response content properly
        response_text = ""
        if hasattr(response.content[0], 'text'):
            response_text = response.content[0].text.strip()
        else:
            response_text = str(response.content[0]).strip()
        
        # Extract JSON
        json_start = response_text.find('{')
        json_end = response_text.rfind('}') + 1
        
        if json_start != -1 and json_end != 0:
            encounter_data = json.loads(response_text[json_start:json_end])
            return encounter_data
            
    except Exception as e:
        print(f"Encounter generation error: {e}")
    
    # Fallback encounter
    return {
        "encounter_name": "Giant Threat",
        "enemies": [{
            "name": "Hill Giant",
            "count": 1,
            "hp": 105,
            "max_hp": 105,
            "ac": 13,
            "initiative_bonus": -1,
            "intelligence": 5,
            "wisdom": 9,
            "attacks": [{"name": "Greatclub", "bonus": 8, "damage": "3d8+5", "type": "bludgeoning"}],
            "special_abilities": [],
            "behavior": "aggressive"
        }],
        "scene_description": "A massive hill giant emerges from the area, drawn by the commotion!"
    }

def roll_initiative_for_encounter(encounter_data: Dict, player_characters: Dict) -> List[Tuple[str, int, bool, str]]:
    """Roll initiative for all participants"""
    
    initiative_list = []
    
    # Roll for players
    for user_id, player_data in player_characters.items():
        char_data = player_data.get("character_data", {})
        char_name = char_data.get("name", "Unknown")
        
        # Simple initiative calculation (can be enhanced)
        dex_mod = 0  # Would extract from character data
        initiative = random.randint(1, 20) + dex_mod
        
        initiative_list.append((f"player_{user_id}", initiative, True, char_name))
    
    # Roll for enemies
    for i, enemy in enumerate(encounter_data.get("enemies", [])):
        for j in range(enemy.get("count", 1)):
            enemy_id = f"enemy_{enemy['name'].lower().replace(' ', '_')}_{j}"
            initiative = random.randint(1, 20) + enemy.get("initiative_bonus", 0)
            enemy_name = enemy["name"] if enemy.get("count", 1) == 1 else f"{enemy['name']} {j+1}"
            
            initiative_list.append((enemy_id, initiative, False, enemy_name))
    
    # Sort by initiative (highest first)
    initiative_list.sort(key=lambda x: x[1], reverse=True)
    
    return initiative_list

async def execute_monster_turn(enemy_id: str, encounter_data: Dict, player_characters: Dict, claude_client) -> str:
    """Execute an intelligent monster turn"""
    
    # Find enemy data
    enemy_data = None
    for enemy in encounter_data.get("enemies", []):
        if enemy_id.startswith(f"enemy_{enemy['name'].lower().replace(' ', '_')}"):
            enemy_data = enemy
            break
    
    if not enemy_data:
        return "The enemy hesitates, unsure of what to do."
    
    # Get enemy intelligence for behavior
    intelligence = enemy_data.get("intelligence", 8)
    wisdom = enemy_data.get("wisdom", 10)
    behavior = enemy_data.get("behavior", "aggressive")
    
    # Select target (simplified - would be enhanced)
    alive_players = [char for char in player_characters.values() 
                    if char.get("character_data", {}).get("hp", 1) > 0]
    
    if not alive_players:
        return "The enemy looks around, confused by the lack of targets."
    
    # Select action based on intelligence
    if intelligence >= 12:
        # Smart enemy - target lowest HP or spellcasters
        target_strategy = "tactical"
    elif intelligence >= 8:
        # Average enemy - attack nearest or most threatening
        target_strategy = "focused"
    else:
        # Dumb enemy - attack randomly
        target_strategy = "random"
    
    # Get first attack
    attacks = enemy_data.get("attacks", [])
    if not attacks:
        return f"The {enemy_data['name']} roars menacingly but doesn't attack."
    
    attack = attacks[0]
    
    # Simple attack resolution
    attack_roll = random.randint(1, 20) + attack.get("bonus", 0)
    target_ac = 15  # Simplified - would get from actual character
    
    if attack_roll >= target_ac:
        # Hit - roll damage
        damage_dice = attack.get("damage", "1d6")
        damage = roll_damage_from_string(damage_dice)
        
        target_name = list(alive_players)[0].get("character_data", {}).get("name", "character")
        
        return f"**{enemy_data['name']}** attacks **{target_name}** with {attack['name']} - **HIT!** Dealing **{damage}** {attack.get('type', 'damage')}!"
    else:
        return f"**{enemy_data['name']}** attacks but misses! (Rolled {attack_roll} vs AC)"

def roll_damage_from_string(damage_str: str) -> int:
    """Roll damage from dice string like '1d8+3'"""
    try:
        if '+' in damage_str:
            dice_part, modifier = damage_str.split('+')
            modifier = int(modifier)
        elif '-' in damage_str:
            dice_part, mod_str = damage_str.split('-')
            modifier = -int(mod_str)
        else:
            dice_part = damage_str
            modifier = 0
        
        if 'd' in dice_part:
            num_dice, die_size = dice_part.split('d')
            num_dice = int(num_dice)
            die_size = int(die_size)
            
            total = sum(random.randint(1, die_size) for _ in range(num_dice))
            return max(1, total + modifier)
        else:
            return max(1, int(dice_part) + modifier)
    except:
        return 1

async def generate_tts_audio(text: str, voice: str = "fable", speed: float = 1.20, model: str = "tts-1") -> Optional[io.BytesIO]:
    """Generate TTS audio using OpenAI's API - optimized for speed"""
    try:
        # Clean text for TTS (remove excessive formatting)
        clean_text = text.replace("**", "").replace("*", "").replace("_", "")
        
        # Enhanced TTS optimization
        clean_text = optimize_text_for_tts(clean_text)
        
        # Use OpenAI TTS API with optimized settings for speed
        async with aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=8),  # Reduced timeout
            connector=aiohttp.TCPConnector(limit=10)
        ) as session:
            headers = {
                "Authorization": f"Bearer {os.getenv('OPENAI_API_KEY')}",
                "Content-Type": "application/json"
            }
            
            # OpenAI TTS payload optimized for speed
            payload = {
                "model": model,  # Default to tts-1 for speed
                "input": clean_text,
                "voice": voice,  # "fable" voice - expressive and dramatic for storytelling
                "response_format": "mp3",  # Changed from opus to mp3 for faster processing
                "speed": speed  # Adjustable speed for optimal gameplay
            }
            
            async with session.post(
                "https://api.openai.com/v1/audio/speech",
                headers=headers,
                json=payload
            ) as response:
                if response.status == 200:
                    audio_data = await response.read()
                    return io.BytesIO(audio_data)
                else:
                    error_text = await response.text()
                    print(f"OpenAI TTS API error: {response.status} - {error_text}")
                    return None
                    
    except Exception as e:
        print(f"TTS generation error: {e}")
        return None

def optimize_text_for_tts(text: str) -> str:
    """Optimize text specifically for faster, clearer TTS delivery"""
    import re
    
    # Remove excessive formatting
    clean_text = text.replace("**", "").replace("*", "").replace("_", "")
    
    # Spell out dice notation for better pronunciation
    clean_text = re.sub(r'\b(\d+)d(\d+)\b', r'\1 dee \2', clean_text)
    clean_text = re.sub(r'\bDC\s*(\d+)\b', r'difficulty class \1', clean_text)
    clean_text = re.sub(r'\bAC\s*(\d+)\b', r'armor class \1', clean_text)
    clean_text = re.sub(r'\bHP\s*(\d+)\b', r'hit points \1', clean_text)
    
    # Simplify complex words for faster speech
    replacements = {
        "immediately": "now",
        "suddenly": "",
        "extremely": "very",
        "tremendous": "huge",
        "magnificent": "great",
        "extraordinary": "amazing"
    }
    
    for old, new in replacements.items():
        clean_text = clean_text.replace(old, new)
    
    # Remove redundant phrases
    clean_text = re.sub(r'\b(very|quite|rather|extremely|incredibly|tremendously)\s+', '', clean_text)
    clean_text = re.sub(r'\b(suddenly|immediately|quickly|slowly)\s+', '', clean_text)
    
    # Clean up extra spaces
    clean_text = re.sub(r'\s+', ' ', clean_text).strip()
    
    return clean_text

def create_tts_version_with_continuation(full_text: str) -> tuple[str, str]:
    """
    Create TTS version and return both the spoken version and any continuation needed
    Returns: (tts_text, continuation_text)
    """
    import re
    
    # Apply enhanced text optimization
    optimized_text = optimize_text_for_tts(full_text)
    
    continuation_text = ""
    
    # Check if we need to truncate for TTS speed - be more aggressive for speed
    if len(optimized_text) > 350:  # Reduced threshold for faster response
        sentences = optimized_text.split('. ')
        
        # Look for STRONG natural stopping points only
        natural_break_index = None
        for i, sentence in enumerate(sentences):
            # Only split at very clear breaks - questions or direct requests
            if any(indicator in sentence.lower() for indicator in [
                'what do you do?', 'roll a', 'make a', 'roll for', '?', 'initiative'
            ]) and i > 0:  # Don't split at the very first sentence
                natural_break_index = i + 1
                break
        
        # If we found a STRONG natural break, use it
        if natural_break_index and natural_break_index < len(sentences):
            spoken_sentences = sentences[:natural_break_index]
            remaining_sentences = sentences[natural_break_index:]
            
            optimized_text = '. '.join(spoken_sentences) + '.'
            if remaining_sentences:
                continuation_text = '. '.join(remaining_sentences) + '.'
        
        # More aggressive splitting for speed - if still too long
        elif len(optimized_text) > 400 and len(sentences) > 2:
            # Take first 2 sentences maximum for speed
            split_point = min(len(sentences) // 2, 2)  # Max 2 sentences in first part
            
            spoken_sentences = sentences[:split_point] 
            remaining_sentences = sentences[split_point:]
            
            optimized_text = '. '.join(spoken_sentences) + '.'
            if remaining_sentences:
                continuation_text = '. '.join(remaining_sentences) + '.'
    
    # Clean up continuation text
    if continuation_text:
        continuation_text = continuation_text.strip()
        
        # Make sure continuation starts properly
        if continuation_text and not continuation_text[0].isupper():
            continuation_text = continuation_text[0].upper() + continuation_text[1:]
        
        # Remove any duplicate content between tts_text and continuation_text
        continuation_text = remove_duplicate_content(optimized_text, continuation_text)
    
    return optimized_text, continuation_text

def remove_duplicate_content(first_part: str, second_part: str) -> str:
    """Remove duplicate sentences between first and second part"""
    if not second_part:
        return ""
    
    # Split both parts into sentences
    first_sentences = [s.strip() for s in first_part.split('.') if s.strip()]
    second_sentences = [s.strip() for s in second_part.split('.') if s.strip()]
    
    # Remove sentences from second part that appear in first part
    unique_sentences = []
    for sentence in second_sentences:
        # Check if this sentence (or very similar) appears in first part
        is_duplicate = False
        for first_sentence in first_sentences:
            # Check for exact match or high similarity
            if (sentence.lower() in first_sentence.lower() or 
                first_sentence.lower() in sentence.lower() or
                sentence == first_sentence):
                is_duplicate = True
                break
        
        if not is_duplicate:
            unique_sentences.append(sentence)
    
    # Rebuild continuation text
    if unique_sentences:
        return '. '.join(unique_sentences) + '.'
    else:
        return ""  # Return empty if all content was duplicate

async def send_continuation_if_needed(message, full_dm_response: str, tts_text: str, 
                                    continuation_text: str, guild_id: int, character_name: str):
    """Send continuation message if the response was truncated"""
    if not continuation_text or len(continuation_text.strip()) < 10:
        return
    
    # Wait a moment for the TTS to finish or get close to finishing
    await asyncio.sleep(3)
    
    # Create continuation embed
    embed = discord.Embed(color=0x2E8B57)
    embed.add_field(
        name="🐉 Donnie continues...",
        value=continuation_text,
        inline=False
    )
    embed.set_footer(text="💬 Response continuation")
    
    # Send as follow-up
    try:
        await message.channel.send(embed=embed)
        
        # Add continuation to voice queue if voice is active
        voice_will_speak = (guild_id in voice_clients and 
                           voice_clients[guild_id].is_connected() and 
                           tts_enabled.get(guild_id, False))
        
        if voice_will_speak:
            await add_to_voice_queue(guild_id, continuation_text, f"{character_name} (continued)")
            
    except Exception as e:
        print(f"Error sending continuation: {e}")

async def play_thinking_sound(guild_id: int, character_name: str):
    """Play a random DM thinking sound immediately to fill waiting time"""
    if (guild_id not in voice_clients or 
        not voice_clients[guild_id].is_connected() or 
        not tts_enabled.get(guild_id, False)):
        return
    
    # Choose a random thinking sound
    thinking_sound = random.choice(DM_THINKING_SOUNDS)
    
    # Add some character-specific context occasionally
    if random.random() < 0.3:  # 30% chance
        character_variations = [
            f"So {character_name}...",
            f"Hmm, {character_name}...",
            f"Alright {character_name}, let me see...",
            f"Well {character_name}...",
        ]
        thinking_sound = random.choice(character_variations)
    
    # Play immediately without queue (these are quick filler sounds)
    await speak_thinking_sound_directly(guild_id, thinking_sound)

async def speak_thinking_sound_directly(guild_id: int, text: str):
    """Play thinking sound directly without queue system - for immediate feedback"""
    if guild_id not in voice_clients or not tts_enabled.get(guild_id, False):
        return
    
    voice_client = voice_clients[guild_id]
    if not voice_client or not voice_client.is_connected():
        return
    
    # Use faster speed and model for thinking sounds to keep them brief
    speed = voice_speed.get(guild_id, 1.25) * 1.3  # 30% faster for thinking sounds
    
    try:
        # Generate TTS audio quickly with faster model
        audio_data = await generate_tts_audio(text, voice="fable", speed=speed, model="tts-1")
        if not audio_data:
            return
        
        # Save to temporary file
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as temp_file:
            temp_file.write(audio_data.getvalue())
            temp_filename = temp_file.name
        
        # Play immediately if not currently playing
        if not voice_client.is_playing():
            audio_source = discord.FFmpegPCMAudio(temp_filename)
            voice_client.play(audio_source)
            
            # Wait for this short sound to finish
            while voice_client.is_playing():
                await asyncio.sleep(0.05)  # Reduced polling interval
        
        # Clean up temp file
        try:
            os.unlink(temp_filename)
        except:
            pass
            
    except Exception as e:
        print(f"Thinking sound error: {e}")

async def process_voice_queue(guild_id: int):
    """Process voice queue to prevent overlapping speech"""
    if guild_id not in voice_queue:
        voice_queue[guild_id] = []
    
    while voice_queue[guild_id]:
        # Get next item in queue
        queue_item = voice_queue[guild_id].pop(0)
        text = queue_item['text']
        message = queue_item.get('message')
        player_name = queue_item.get('player_name', 'Unknown')
        
        # Check if voice is still enabled and connected
        if (guild_id not in voice_clients or 
            not voice_clients[guild_id].is_connected() or 
            not tts_enabled.get(guild_id, False)):
            continue
        
        # Update message to show this player is speaking
        if message:
            try:
                embed = message.embeds[0]
                for i, field in enumerate(embed.fields):
                    if field.name == "🎤":
                        embed.set_field_at(i, name="🎤", value=f"*Donnie responds to {player_name}*", inline=False)
                        break
                await message.edit(embed=embed)
            except:
                pass
        
        # Generate and play TTS
        await speak_text_directly(guild_id, text)
        
        # Small pause between voice lines
        await asyncio.sleep(0.5)

async def speak_text_directly(guild_id: int, text: str):
    """Generate TTS and play directly without queue management"""
    if guild_id not in voice_clients or not tts_enabled.get(guild_id, False):
        return
    
    voice_client = voice_clients[guild_id]
    if not voice_client or not voice_client.is_connected():
        return
    
    # Get guild-specific speed or use default
    speed = voice_speed.get(guild_id, 1.25)
    
    # Create optimized version for TTS (shorter = faster)
    tts_text, _ = create_tts_version_with_continuation(text)  # We only want the first part for voice
    
    # Choose model based on quality settings
    quality_mode = voice_quality.get(guild_id, "smart")  # Default to smart mode
    
    if quality_mode == "speed":
        model = "tts-1"
    elif quality_mode == "quality":
        model = "tts-1-hd"
    else:  # smart mode
        # Use tts-1-hd for dramatic moments, tts-1 for regular responses
        dramatic_keywords = ["critical", "natural 20", "initiative", "damage", "combat begins", "you take", "saving throw"]
        if len(tts_text) < 120 and any(word in tts_text.lower() for word in dramatic_keywords):
            model = "tts-1-hd"  # Use high quality for important moments
        else:
            model = "tts-1"  # Use speed for regular responses
    
    print(f"🎤 TTS: Using {model} for {len(tts_text)} chars in {quality_mode} mode")
    
    # Generate TTS audio with optimized text
    audio_data = await generate_tts_audio(tts_text, voice="fable", speed=speed, model=model)
    if not audio_data:
        return
    
    # Save to temporary file
    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as temp_file:
        temp_file.write(audio_data.getvalue())
        temp_filename = temp_file.name
    
    try:
        # Wait for any current audio to finish
        while voice_client.is_playing():
            await asyncio.sleep(0.05)  # Reduced polling interval
        
        # Play audio in voice channel
        audio_source = discord.FFmpegPCMAudio(temp_filename)
        voice_client.play(audio_source)
        
        # Wait for audio to finish
        while voice_client.is_playing():
            await asyncio.sleep(0.1)
            
    except Exception as e:
        print(f"Audio playback error: {e}")
    finally:
        # Clean up temp file
        try:
            os.unlink(temp_filename)
        except:
            pass

async def add_to_voice_queue(guild_id: int, text: str, player_name: str, message=None):
    """Add voice request to queue and process it"""
    if guild_id not in voice_queue:
        voice_queue[guild_id] = []
    
    # Add to queue
    voice_queue[guild_id].append({
        'text': text,
        'message': message,
        'player_name': player_name
    })
    
    # Show queue status if multiple items
    queue_size = len(voice_queue[guild_id])
    if message and queue_size > 1:
        try:
            embed = message.embeds[0]
            for i, field in enumerate(embed.fields):
                if field.name == "🎤":
                    embed.set_field_at(i, name="🎤", value=f"*Queued ({queue_size} in line) - {player_name}*", inline=False)
                    break
            await message.edit(embed=embed)
        except:
            pass
    
    # Start processing queue if not already running
    if queue_size == 1:  # Only start if this is the first item
        asyncio.create_task(process_voice_queue(guild_id))

# Enhanced get_claude_dm_response function that includes combat intelligence
async def get_enhanced_claude_dm_response(user_id: str, player_input: str):
    """Enhanced DM response with combat intelligence"""
    try:
        print(f"🤖 Enhanced Claude API call started for user {user_id}")
        
        # Get character and player info
        player_data = campaign_context["players"][user_id]
        char_data = player_data["character_data"]
        player_name = player_data["player_name"]
        character_name = char_data["name"]
        
        print(f"📝 Processing action for {character_name} ({player_name}): {player_input}")
        
        # Format character information for the prompt
        character_info = []
        for uid, char_desc in campaign_context["characters"].items():
            if uid in campaign_context["players"]:
                p_data = campaign_context["players"][uid]
                c_data = p_data["character_data"]
                character_info.append(f"{c_data['name']} ({p_data['player_name']}): {char_desc}")
        
        characters_text = "\n".join(character_info) if character_info else "No characters registered yet"
        
        # Combat status for context
        combat_status = "No active combat"
        if combat_state["active"]:
            combat_status = f"COMBAT ACTIVE - {combat_state['encounter_name']} - Round {combat_state['round']}"
        
        print(f"⚔️ Combat status: {combat_status}")
        
        # Check for combat trigger
        combat_trigger = await detect_combat_trigger(player_input, campaign_context["current_scene"])
        print(f"🎯 Combat trigger detected: {combat_trigger['triggered']}")
        
        # If combat triggered and not already active, start combat
        if combat_trigger["triggered"] and not combat_state["active"]:
            print("🚨 Starting new combat encounter...")
            encounter_data = await generate_story_appropriate_encounter(
                campaign_context["current_scene"], 
                campaign_context["players"], 
                claude_client
            )
            
            if encounter_data:
                print(f"👹 Generated encounter: {encounter_data['encounter_name']}")
                # Start combat
                combat_state["active"] = True
                combat_state["encounter_name"] = encounter_data["encounter_name"]
                combat_state["round"] = 1
                combat_state["monsters"] = encounter_data
                
                # Roll initiative
                initiative_order = roll_initiative_for_encounter(encounter_data, campaign_context["players"])
                combat_state["initiative_order"] = initiative_order
                combat_state["current_turn"] = 0
                
                # Update combat status
                combat_status = f"COMBAT STARTED - {encounter_data['encounter_name']} - Initiative rolled!"
        
        formatted_prompt = ENHANCED_DM_PROMPT.format(
            setting=campaign_context["setting"],
            current_scene=campaign_context["current_scene"],
            session_history=campaign_context["session_history"][-3:],
            characters=characters_text,
            players=[p["player_name"] for p in campaign_context["players"].values()],
            combat_status=combat_status,
            player_input=f"{character_name} ({player_name}): {player_input}"
        )
        
        print("🧠 Sending request to Claude API...")
        
        # Check if claude_client is properly initialized
        if not claude_client:
            raise Exception("Claude client not initialized - check ANTHROPIC_API_KEY")
        
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: claude_client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=300,  # Increased for combat responses
                messages=[{
                    "role": "user",
                    "content": formatted_prompt
                }]
            )
        )
        
        print("✅ Claude API response received")
        
        # Handle the response content properly
        dm_response = ""
        if hasattr(response.content[0], 'text'):
            dm_response = response.content[0].text.strip()
        else:
            dm_response = str(response.content[0]).strip()
        
        print(f"📜 DM Response length: {len(dm_response)} characters")
        
        # If combat just started, add initiative order to response
        if combat_trigger["triggered"] and combat_state["active"] and combat_state["round"] == 1:
            print("⚔️ Adding combat initiative to response...")
            initiative_text = "\n\n**⚔️ COMBAT BEGINS! ⚔️**\n**Initiative Order:**\n"
            for i, (entity_id, initiative, is_player, name) in enumerate(combat_state["initiative_order"]):
                marker = "▶️" if i == 0 else "⏸️"
                player_icon = "🎭" if is_player else "👹"
                initiative_text += f"{marker} {player_icon} **{name}** ({initiative})\n"
            
            dm_response += initiative_text
            if 'encounter_data' in locals():
                dm_response += f"\n*{combat_state['encounter_name']} - {encounter_data.get('scene_description', '')}*"
        
        # Handle monster turns if it's their turn in combat
        if combat_state["active"] and combat_state["current_turn"] < len(combat_state["initiative_order"]):
            current_entity = combat_state["initiative_order"][combat_state["current_turn"]]
            if not current_entity[2]:  # Not a player (is monster)
                print("👹 Processing monster turn...")
                monster_action = await execute_monster_turn(
                    current_entity[0], 
                    combat_state["monsters"], 
                    campaign_context["players"], 
                    claude_client
                )
                dm_response += f"\n\n**👹 Monster Turn:**\n{monster_action}"
                
                # Advance turn
                combat_state["current_turn"] += 1
                if combat_state["current_turn"] >= len(combat_state["initiative_order"]):
                    combat_state["current_turn"] = 0
                    combat_state["round"] += 1
        
        # Update session history
        campaign_context["session_history"].append({
            "player": f"{character_name} ({player_name})",
            "action": player_input,
            "dm_response": dm_response
        })
        
        if len(campaign_context["session_history"]) > 10:
            campaign_context["session_history"] = campaign_context["session_history"][-10:]
        
        print("✅ Enhanced Claude DM response complete")
        return dm_response
        
    except Exception as e:
        print(f"❌ Enhanced Claude API error: {e}")
        import traceback
        traceback.print_exc()
        return f"The DM pauses momentarily as otherworldly forces intervene... (Enhanced Error: {str(e)})"

# Keep the original function for fallback
async def get_claude_dm_response(user_id: str, player_input: str):
    """Get DM response from Claude (original version)"""
    try:
        print(f"🔄 Fallback Claude API call started for user {user_id}")
        
        # Get character and player info
        player_data = campaign_context["players"][user_id]
        char_data = player_data["character_data"]
        player_name = player_data["player_name"]
        character_name = char_data["name"]
        
        print(f"📝 Fallback processing action for {character_name} ({player_name}): {player_input}")
        
        # Format character information for the prompt
        character_info = []
        for uid, char_desc in campaign_context["characters"].items():
            if uid in campaign_context["players"]:
                p_data = campaign_context["players"][uid]
                c_data = p_data["character_data"]
                character_info.append(f"{c_data['name']} ({p_data['player_name']}): {char_desc}")
        
        characters_text = "\n".join(character_info) if character_info else "No characters registered yet"
        
        # Original DM prompt (keep for compatibility)
        DM_PROMPT = """You are Donnie, a Dungeon Master running Storm King's Thunder for D&D 5th Edition (2024 rules).

SETTING: {setting}
CURRENT SCENE: {current_scene}
RECENT HISTORY: {session_history}
PARTY CHARACTERS: {characters}
PLAYERS: {players}

You are running Storm King's Thunder - giants threaten the Sword Coast and the ordning has collapsed.

PARTY COMPOSITION: Use the character information provided to personalize your responses. Address characters by their CHARACTER NAMES (not Discord IDs) and reference their classes, backgrounds, and details when appropriate.

**D&D 5e 2024 ADHERENCE FRAMEWORK - MANDATORY COMPLIANCE**

**1. COMBAT MECHANICS**
- MANDATORY: Roll initiative for ALL combat encounters
- MANDATORY: Track Action, Bonus Action, Movement, and Reaction separately each turn
- MANDATORY: Load complete stat block for all creatures before combat begins
- MANDATORY: Calculate encounter difficulty using CR guidelines before deployment
- FORMAT: "Initiative: [Character Name] - [Roll+Dex]. Turn: Action/Bonus/Move used this turn"

**2. RESOURCE TRACKING**
- SPELL SLOTS: Track precisely with format "Level X: Used Y/Total Z"
- ABILITIES: Track uses with format "Ability Name: Used X/Y per rest"
- HIT POINTS: Always state current/max format "HP: X/Y"
- EQUIPMENT: Maintain persistent inventory, track ammunition/consumables

**3. EXPERIENCE & LEVELING**
- XP TRACKING: Award XP using encounter values (CR-based) or milestone markers
- LEVEL PROGRESSION: Maximum 1 level per 2-4 sessions unless story milestone reached
- ADVANCEMENT: Follow PHB exactly - spell slots, abilities, proficiency bonus progression

**4. REST SYSTEM**
- SHORT REST: 1 hour, limited healing/ability recovery per PHB
- LONG REST: 8 hours, only after significant story progress or 6-8 encounters
- ADVENTURING DAY: 6-8 encounters between long rests to maintain resource tension

**5. SKILL CHECKS & DCs**
- STANDARD DCs: Easy (10), Medium (15), Hard (20), Nearly Impossible (25)
- ABILITY CHECKS: Always specify which ability + which skill
- ADVANTAGE/DISADVANTAGE: Only grant per specific rules or clear narrative justification

**STAT BLOCK PROTOCOL**
PRE-COMBAT CHECKLIST:
1. LOAD STAT BLOCKS: Reference official stat block from Monster Manual/source
2. VERIFY CR: Confirm challenge rating matches party level appropriately
3. CALCULATE ENCOUNTER: Use encounter building guidelines for difficulty
4. PREPARE ABILITIES: Note special attacks, resistances, legendary actions
5. SET INITIATIVE: Have creature's initiative bonus ready

**CRITICAL RULES:**
- DO NOT REVEAL STAT BLOCKS TO PLAYERS
- ALWAYS USE CHARACTER NAMES, NOT DISCORD IDs
- ENFORCE action economy strictly
- Reference PHB/official rules for disputes
- Track resources precisely

**STORM KING'S THUNDER SPECIFIC:**
- Giants should feel massive and threatening when encountered
- Use vivid descriptions of the Sword Coast setting
- Reference character abilities and backgrounds in responses
- Ask for dice rolls when appropriate (D&D 5e 2024 rules)
- Keep responses 2-4 sentences for real-time play
- Make player choices matter and have consequences
- Create immersive roleplay opportunities
- You are fair but challenging - not too easy, not too harsh

PLAYER ACTION: {player_input}

Respond as Donnie, the Storm King's Thunder DM, following ALL D&D 5e 2024 rules strictly:"""
        
        formatted_prompt = DM_PROMPT.format(
            setting=campaign_context["setting"],
            current_scene=campaign_context["current_scene"],
            session_history=campaign_context["session_history"][-3:],
            characters=characters_text,
            players=[p["player_name"] for p in campaign_context["players"].values()],
            player_input=f"{character_name} ({player_name}): {player_input}"
        )
        
        print("🧠 Sending fallback request to Claude API...")
        
        # Check if claude_client is properly initialized
        if not claude_client:
            raise Exception("Claude client not initialized - check ANTHROPIC_API_KEY")
        
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: claude_client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=200,
                messages=[{
                    "role": "user",
                    "content": formatted_prompt
                }]
            )
        )
        
        print("✅ Fallback Claude API response received")
        
        # Handle the response content properly
        dm_response = ""
        if hasattr(response.content[0], 'text'):
            dm_response = response.content[0].text.strip()
        else:
            # Fallback for different response types
            dm_response = str(response.content[0]).strip()
        
        print(f"📜 Fallback DM Response length: {len(dm_response)} characters")
        
        # Update session history
        campaign_context["session_history"].append({
            "player": f"{character_name} ({player_name})",
            "action": player_input,
            "dm_response": dm_response
        })
        
        if len(campaign_context["session_history"]) > 10:
            campaign_context["session_history"] = campaign_context["session_history"][-10:]
        
        print("✅ Fallback Claude DM response complete")
        return dm_response
        
    except Exception as e:
        print(f"❌ Fallback Claude API error: {e}")
        import traceback
        traceback.print_exc()
        return f"The DM pauses momentarily as otherworldly forces intervene... (Fallback Error: {str(e)})"

# ====== STATE SYNCHRONIZATION FIXES ======

def sync_campaign_context_with_database(guild_id: str):
    """Sync in-memory campaign context with database state - FIXED VERSION"""
    if not DATABASE_AVAILABLE:
        return
    
    try:
        # Get current episode from database
        current_episode = EpisodeOperations.get_current_episode(guild_id)
        if current_episode:
            # SYNC ALL STATE VARIABLES - THE FIX
            campaign_context["current_episode"] = current_episode.episode_number
            campaign_context["episode_active"] = True  # ✅ ENSURE THIS IS SET
            campaign_context["session_started"] = True  # ✅ ENSURE THIS IS SET TOO
            campaign_context["episode_start_time"] = current_episode.start_time
            campaign_context["guild_id"] = guild_id
            
            # Load session history from database
            if current_episode.session_history:
                campaign_context["session_history"] = current_episode.session_history
            
            print(f"✅ Synced campaign context with Episode {current_episode.episode_number}")
            print(f"   episode_active: {campaign_context['episode_active']}")
            print(f"   session_started: {campaign_context['session_started']}")
        else:
            # NO ACTIVE EPISODE - CLEAR ALL STATE
            campaign_context["current_episode"] = 0
            campaign_context["episode_active"] = False
            campaign_context["session_started"] = False
            campaign_context["episode_start_time"] = None
            print(f"✅ No active episode - cleared all state")
        
        # Get guild settings
        guild_settings = GuildOperations.get_guild_settings(guild_id)
        if guild_settings:
            # Sync voice settings with database - FIX GUILD ID TYPE
            voice_speed[int(guild_id)] = guild_settings.get('voice_speed', 1.25)
            tts_enabled[int(guild_id)] = guild_settings.get('tts_enabled', False)
            
            print(f"✅ Synced guild settings for {guild_id}")
            
    except Exception as e:
        print(f"⚠️ Failed to sync campaign context: {e}")
        import traceback
        traceback.print_exc()

async def ensure_state_sync(guild_id: str):
    """Helper function to ensure state is synced before operations"""
    sync_campaign_context_with_database(guild_id)
    
    # Verify sync worked and fix any remaining issues
    if DATABASE_AVAILABLE:
        try:
            db_episode = EpisodeOperations.get_current_episode(guild_id)
            memory_active = campaign_context.get("episode_active", False)
            memory_started = campaign_context.get("session_started", False)
            
            if db_episode and not memory_active:
                print(f"⚠️ State sync issue detected - forcing memory state update")
                campaign_context["episode_active"] = True
                campaign_context["session_started"] = True
                campaign_context["current_episode"] = db_episode.episode_number
                campaign_context["guild_id"] = guild_id
            elif not db_episode and memory_active:
                print(f"⚠️ State sync issue detected - clearing memory state")
                campaign_context["episode_active"] = False
                campaign_context["session_started"] = False
                campaign_context["current_episode"] = 0
        except Exception as e:
            print(f"⚠️ State validation error: {e}")

@bot.event
async def on_ready():
    print(f'⚡ {bot.user} is ready for Storm King\'s Thunder!')
    print(f'🏔️ Giants threaten the Sword Coast!')
    print(f'🎤 Donnie the DM is ready to speak!')
    print(f'⚔️ Intelligent Combat System loaded!')
    
    # Initialize database with enhanced error handling
    if DATABASE_AVAILABLE:
        try:
            init_database()
            print("✅ Database initialized successfully")
            
            # Test database health
            from database import health_check, get_database_stats
            if health_check():
                stats = get_database_stats()
                print(f"📊 Database stats: {stats}")
            else:
                print("⚠️ Database health check failed")
            
            # ✅ FORCE SYNC ALL ACTIVE GUILDS ON STARTUP
            print("🔄 Syncing guild states on startup...")
            try:
                # Get all guilds the bot is in
                for guild in bot.guilds:
                    guild_id = str(guild.id)
                    print(f"🔄 Syncing guild {guild.name} ({guild_id})")
                    sync_campaign_context_with_database(guild_id)
            except Exception as e:
                print(f"⚠️ Error during startup sync: {e}")
                
        except Exception as e:
            print(f"❌ Database initialization failed: {e}")
            print("🔄 Bot will continue without database features")
    else:
        print("⚠️ Database features disabled")
    
    print('🔄 Syncing slash commands...')
    
    # Check for FFmpeg
    import subprocess
    try:
        subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True)
        print("✅ FFmpeg detected")
    except:
        print("⚠️ FFmpeg not found - required for voice features")
        
    try:
        synced = await bot.tree.sync()
        print(f'✅ Synced {len(synced)} slash commands')
        
        # Feature status summary
        features = {
            "Database": "✅" if DATABASE_AVAILABLE else "❌",
            "Episodes": "✅" if episode_commands else "❌", 
            "Progression": "✅" if character_progression else "❌",
            "Enhanced Voice": "✅" if enhanced_voice_manager else "❌",
            "Combat Intelligence": "✅",
            "PDF Upload": "✅" if hasattr(bot, 'pdf_character_commands') else "❌"
        }
        
        print("🎲 Storm King's Thunder Bot Feature Status:")
        for feature, status in features.items():
            print(f"   {status} {feature}")
            
        print("🎉 Ready for epic adventures!")
        
    except Exception as e:
        print(f'❌ Failed to sync commands: {e}')
        import traceback
        traceback.print_exc()

@bot.event
async def on_disconnect():
    print("🔌 Bot disconnecting...")
    
    # Save any pending changes to database
    if DATABASE_AVAILABLE:
        try:
            # Update all active guild settings
            for guild_id in voice_speed.keys():
                update_database_from_campaign_context(str(guild_id))
            
            close_database()
            print("✅ Database connections closed and data saved")
        except Exception as e:
            print(f"⚠️ Error during database cleanup: {e}")
    
    print("👋 Goodbye!")

@bot.event
async def on_guild_join(guild):
    """Initialize database settings when bot joins a new guild"""
    if DATABASE_AVAILABLE:
        try:
            guild_id = str(guild.id)
            
            # Initialize guild settings in database
            GuildOperations.update_guild_settings(
                guild_id,
                voice_speed=1.25,
                voice_quality='smart',
                tts_enabled=False,
                current_episode=0
            )
            
            print(f"✅ Initialized database settings for guild: {guild.name}")
            
        except Exception as e:
            print(f"⚠️ Failed to initialize guild settings: {e}")

@bot.event  
async def on_guild_remove(guild):
    """Clean up when bot leaves a guild"""
    guild_id = guild.id
    
    # Clean up in-memory state
    if guild_id in voice_clients:
        try:
            await voice_clients[guild_id].disconnect()
            del voice_clients[guild_id]
        except:
            pass
    
    # Clean up other guild-specific data
    voice_speed.pop(guild_id, None)
    tts_enabled.pop(guild_id, None) 
    voice_queue.pop(guild_id, None)
    
    print(f"🧹 Cleaned up data for guild: {guild.name}")

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return
    
    # Auto-sync campaign context with database when messages are received
    if DATABASE_AVAILABLE and message.guild:
        guild_id = str(message.guild.id)
        
        # Only sync occasionally to avoid performance issues
        if random.random() < 0.1:  # 10% chance per message
            sync_campaign_context_with_database(guild_id)
    
    await bot.process_commands(message)

# ====== VOICE CHANNEL COMMANDS ======

@bot.tree.command(name="join_voice", description="Donnie joins your voice channel to narrate the adventure")
async def join_voice_channel(interaction: discord.Interaction):
    """Join the user's voice channel"""
    if not hasattr(interaction.user, 'voice') or not interaction.user.voice:
        await interaction.response.send_message("❌ You need to be in a voice channel first!", ephemeral=True)
        return
    
    if not campaign_context.get("session_started", False) and not campaign_context.get("episode_active", False):
        await interaction.response.send_message("❌ Start the campaign first with `/start` or `/start_episode`!", ephemeral=True)
        return
    
    voice_channel = interaction.user.voice.channel
    if not voice_channel:
        await interaction.response.send_message("❌ Could not access your voice channel!", ephemeral=True)
        return
        
    guild_id = interaction.guild.id if interaction.guild else 0
    
    try:
        # Leave existing voice channel if connected
        if guild_id in voice_clients and voice_clients[guild_id].is_connected():
            await voice_clients[guild_id].disconnect()
        
        # Join new voice channel
        voice_client = await voice_channel.connect()
        voice_clients[guild_id] = voice_client
        tts_enabled[guild_id] = True
        voice_speed[guild_id] = 1.25  # Default faster speed for gameplay
        
        embed = discord.Embed(
            title="🎤 Donnie the DM Joins!",
            description=f"*Donnie's expressive Fable voice echoes through {voice_channel.name}*",
            color=0x32CD32
        )
        
        embed.add_field(
            name="🗣️ Voice Activated",
            value="Donnie will now narrate DM responses aloud with theatrical flair during your adventure!",
            inline=False
        )
        
        embed.add_field(
            name="🔧 Controls",
            value="`/mute_donnie` - Disable TTS\n`/unmute_donnie` - Enable TTS\n`/leave_voice` - Donnie leaves voice\n`/donnie_speed` - Adjust speaking speed",
            inline=False
        )
        
        await interaction.response.send_message(embed=embed)
        
        # Welcome message in voice
        welcome_text = "Greetings, brave adventurers! I am Donnie, your Dungeon Master. I'll be narrating this Storm King's Thunder campaign with intelligent combat automation. When you take actions that trigger combat, I'll automatically generate appropriate encounters, roll initiative, and control monster AI. Just describe what you want to do, and let the adventure unfold naturally!"
        await add_to_voice_queue(guild_id, welcome_text, "Donnie")
        
    except Exception as e:
        await interaction.response.send_message(f"❌ Failed to join voice channel: {str(e)}", ephemeral=True)

@bot.tree.command(name="leave_voice", description="Donnie leaves the voice channel")
async def leave_voice_channel(interaction: discord.Interaction):
    """Leave the voice channel"""
    guild_id = interaction.guild.id
    
    if guild_id not in voice_clients or not voice_clients[guild_id].is_connected():
        await interaction.response.send_message("❌ Donnie isn't in a voice channel!", ephemeral=True)
        return
    
    try:
        await voice_clients[guild_id].disconnect()
        del voice_clients[guild_id]
        tts_enabled[guild_id] = False
        if guild_id in voice_speed:
            del voice_speed[guild_id]  # Clean up speed setting
        if guild_id in voice_queue:
            del voice_queue[guild_id]  # Clean up voice queue
        
        embed = discord.Embed(
            title="👋 Donnie the DM Departs",
            description="*Donnie's expressive voice fades away as he steps back from the microphone*",
            color=0xFF4500
        )
        
        embed.add_field(
            name="🔇 Voice Disabled",
            value="Use `/join_voice` to have Donnie speak again!",
            inline=False
        )
        
        await interaction.response.send_message(embed=embed)
        
    except Exception as e:
        await interaction.response.send_message(f"❌ Error leaving voice channel: {str(e)}", ephemeral=True)

@bot.tree.command(name="mute_donnie", description="Mute Donnie's voice (stay in channel)")
async def mute_tts(interaction: discord.Interaction):
    """Disable TTS while staying in voice channel"""
    guild_id = interaction.guild.id
    
    if guild_id not in voice_clients or not voice_clients[guild_id].is_connected():
        await interaction.response.send_message("❌ Donnie isn't in a voice channel!", ephemeral=True)
        return
    
    tts_enabled[guild_id] = False
    
    embed = discord.Embed(
        title="🔇 Donnie Muted",
        description="Donnie remains in the voice channel but won't speak responses aloud",
        color=0xFFD700
    )
    
    embed.add_field(
        name="ℹ️ Note",
        value="Use `/unmute_donnie` to re-enable voice narration",
        inline=False
    )
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="unmute_donnie", description="Unmute Donnie's voice")
async def unmute_tts(interaction: discord.Interaction):
    """Re-enable TTS in voice channel"""
    guild_id = interaction.guild.id
    
    if guild_id not in voice_clients or not voice_clients[guild_id].is_connected():
        await interaction.response.send_message("❌ Donnie isn't in a voice channel! Use `/join_voice` first.", ephemeral=True)
        return
    
    tts_enabled[guild_id] = True
    
    embed = discord.Embed(
        title="🔊 Donnie Unmuted",
        description="Donnie's expressive voice returns to narrate your adventure!",
        color=0x32CD32
    )
    
    await interaction.response.send_message(embed=embed)

# Voice quality preferences per guild
voice_quality = {}  # Guild ID -> "speed" or "quality"

@bot.tree.command(name="donnie_speed", description="Adjust Donnie's speaking speed")
@app_commands.describe(speed="Speaking speed (0.5 = very slow, 1.0 = normal, 1.5 = fast, 2.0 = very fast)")
async def adjust_voice_speed(interaction: discord.Interaction, speed: float):
    """Adjust TTS speaking speed"""
    guild_id = interaction.guild.id if interaction.guild else 0
    
    if guild_id not in voice_clients or not voice_clients[guild_id].is_connected():
        await interaction.response.send_message("❌ Donnie isn't in a voice channel! Use `/join_voice` first.", ephemeral=True)
        return
    
    # Validate speed range
    if speed < 0.25 or speed > 4.0:
        await interaction.response.send_message("❌ Speed must be between 0.25 and 4.0!", ephemeral=True)
        return
    
    # Update speed
    voice_speed[guild_id] = speed
    
    # Create response with speed descriptions
    if speed < 0.7:
        speed_desc = "Very Slow & Dramatic"
    elif speed < 0.9:
        speed_desc = "Slow & Theatrical"
    elif speed < 1.1:
        speed_desc = "Normal Pace"
    elif speed < 1.3:
        speed_desc = "Fast & Engaging"
    elif speed < 1.7:
        speed_desc = "Very Fast"
    else:
        speed_desc = "Extremely Fast"
    
    embed = discord.Embed(
        title="⚡ Donnie's Speed Adjusted!",
        description=f"Speed set to **{speed}x** ({speed_desc})",
        color=0x32CD32
    )
    
    embed.add_field(
        name="🎤 Optimized Performance",
        value="Donnie uses smart model selection and enhanced text processing for faster responses!",
        inline=False
    )
    
    # Test the new speed with a quick message
    if tts_enabled.get(guild_id, False):
        test_message = f"Speed adjusted to {speed}x. This is how fast I speak now!"
        await add_to_voice_queue(guild_id, test_message, "Speed Test")
    
    await interaction.response.send_message(embed=embed)

# ====== DEBUG COMMAND - STEP 1 OF STATE SYNC FIX ======

@bot.tree.command(name="debug_state", description="Show detailed state information (Admin only)")
async def debug_state(interaction: discord.Interaction):
    """Debug command to show all state information"""
    if not hasattr(interaction.user, 'guild_permissions') or not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ Admin only!", ephemeral=True)
        return
    
    guild_id = str(interaction.guild.id)
    
    # Get database state
    db_episode = None
    if DATABASE_AVAILABLE:
        db_episode = EpisodeOperations.get_current_episode(guild_id)
    
    embed = discord.Embed(
        title="🔍 Debug State Information",
        color=0x4169E1
    )
    
    # In-memory state
    embed.add_field(
        name="📝 In-Memory State",
        value=f"session_started: {campaign_context.get('session_started', False)}\n"
              f"episode_active: {campaign_context.get('episode_active', False)}\n"
              f"current_episode: {campaign_context.get('current_episode', 0)}\n"
              f"guild_id: {campaign_context.get('guild_id', 'None')}",
        inline=False
    )
    
    # Database state
    if db_episode:
        embed.add_field(
            name="🗄️ Database State",
            value=f"Episode ID: {db_episode.id}\n"
                  f"Episode Number: {db_episode.episode_number}\n"
                  f"Episode Name: {db_episode.episode_name}\n"
                  f"Start Time: {db_episode.start_time}\n"
                  f"End Time: {db_episode.end_time}",
            inline=False
        )
    else:
        embed.add_field(
            name="🗄️ Database State",
            value="No active episode in database",
            inline=False
        )
    
    await interaction.response.send_message(embed=embed, ephemeral=True)

# ====== CHARACTER MANAGEMENT COMMANDS ======

@bot.tree.command(name="character", description="Register your character for the Storm King's Thunder campaign")
@app_commands.describe(
    name="Your character's name",
    race="Character race (Human, Elf, Dwarf, etc.)",
    character_class="Character class (Fighter, Wizard, Rogue, etc.)",
    level="Character level (1-20)",
    background="Character background (Folk Hero, Acolyte, etc.)",
    stats="Key ability scores (STR 16, DEX 14, CON 15, etc.)",
    equipment="Important weapons, armor, and magical items",
    spells="Known spells (if applicable)",
    affiliations="Factions, organizations, or important relationships",
    personality="Key personality traits, ideals, bonds, and flaws"
)
async def register_character(interaction: discord.Interaction, 
                           name: str,
                           race: str, 
                           character_class: str,
                           level: int,
                           background: Optional[str] = None,
                           stats: Optional[str] = None,
                           equipment: Optional[str] = None,
                           spells: Optional[str] = None,
                           affiliations: Optional[str] = None,
                           personality: Optional[str] = None):
    """Register a detailed character for the campaign"""
    user_id = str(interaction.user.id)
    player_name = interaction.user.display_name
    
    # Set guild_id in campaign context if not set
    if campaign_context["guild_id"] is None:
        campaign_context["guild_id"] = str(interaction.guild.id)
    
    # Validate level
    if level < 1 or level > 20:
        await interaction.response.send_message("❌ Character level must be between 1 and 20!", ephemeral=True)
        return
    
    # Safely handle optional parameters
    safe_background = background if background is not None else "Unknown"
    safe_stats = stats if stats is not None else "Standard array"
    safe_equipment = equipment if equipment is not None else "Basic adventuring gear"
    safe_affiliations = affiliations if affiliations is not None else "None"
    safe_personality = personality if personality is not None else "To be determined in play"
    
    # Handle spells with class detection
    if spells is not None:
        safe_spells = spells
    else:
        spellcaster_classes = ["wizard", "cleric", "sorcerer", "warlock", "bard", "druid", "paladin", "ranger"]
        if any(cls in character_class.lower() for cls in spellcaster_classes):
            safe_spells = "Basic spells for class"
        else:
            safe_spells = "None"
    
    # Build comprehensive character profile
    character_profile = {
        "name": name,
        "race": race,
        "class": character_class,
        "level": level,
        "background": safe_background,
        "stats": safe_stats,
        "equipment": safe_equipment,
        "spells": safe_spells,
        "affiliations": safe_affiliations,
        "personality": safe_personality,
        "player_name": player_name,
        "discord_user_id": user_id
    }
    
    # Create formatted character description for Claude
    character_description = f"""
NAME: {character_profile['name']}
PLAYER: {player_name} (Discord ID: {user_id})
RACE & CLASS: {character_profile['race']} {character_profile['class']} (Level {character_profile['level']})
BACKGROUND: {character_profile['background']}
ABILITY SCORES: {character_profile['stats']}
EQUIPMENT: {character_profile['equipment']}
SPELLS: {character_profile['spells']}
AFFILIATIONS: {character_profile['affiliations']}
PERSONALITY: {character_profile['personality']}
"""
    
    # Store using Discord User ID as primary key
    campaign_context["characters"][user_id] = character_description
    campaign_context["players"][user_id] = {
        "user_id": user_id,
        "player_name": player_name,
        "character_data": character_profile,
        "character_description": character_description
    }
    
    # Create response embed
    embed = discord.Embed(
        title="🎭 Character Registered Successfully!",
        color=0x32CD32
    )
    
    embed.add_field(
        name=f"⚔️ {character_profile['name']}",
        value=f"**{character_profile['race']} {character_profile['class']}** (Level {character_profile['level']})\n*{character_profile['background']}*\n👤 Player: {player_name}",
        inline=False
    )
    
    if character_profile['stats'] != "Standard array":
        embed.add_field(name="📊 Ability Scores", value=character_profile['stats'], inline=True)
    
    if character_profile['equipment'] != "Basic adventuring gear":
        embed.add_field(name="⚔️ Equipment", value=character_profile['equipment'][:100] + ("..." if len(character_profile['equipment']) > 100 else ""), inline=True)
    
    if character_profile['spells'] not in ["None", "Basic spells for class"]:
        embed.add_field(name="✨ Spells", value=character_profile['spells'][:100] + ("..." if len(character_profile['spells']) > 100 else ""), inline=True)
    
    if character_profile['affiliations'] != "None":
        embed.add_field(name="🏛️ Affiliations", value=character_profile['affiliations'], inline=False)
    
    if character_profile['personality'] != "To be determined in play":
        embed.add_field(name="🎭 Personality", value=character_profile['personality'][:200] + ("..." if len(character_profile['personality']) > 200 else ""), inline=False)
    
    embed.add_field(
        name="⚡ Next Steps",
        value="Start an episode with `/start_episode`, or use `/upload_character_sheet` to import a PDF character sheet, then use `/join_voice` to have Donnie narrate your adventure with intelligent combat!",
        inline=False
    )
    
    embed.set_footer(text="Character bound to your Discord account and ready for intelligent combat!")
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="party", description="View all registered characters in your party")
async def view_party(interaction: discord.Interaction):
    """Show all registered characters"""
    if not campaign_context["characters"]:
        embed = discord.Embed(
            title="🎭 No Characters Registered",
            description="No one has registered their character yet! Use `/character` to introduce yourself.",
            color=0xFF6B6B
        )
        await interaction.response.send_message(embed=embed)
        return
    
    embed = discord.Embed(
        title="🗡️ Your Adventuring Party",
        description="Heroes ready to face the giant threat:",
        color=0x4B0082
    )
    
    for user_id, character_desc in campaign_context["characters"].items():
        if user_id in campaign_context["players"]:
            player_data = campaign_context["players"][user_id]
            char_data = player_data["character_data"]
            current_player_name = player_data["player_name"]
            
            # Create character summary
            char_summary = f"**{char_data['race']} {char_data['class']}** (Level {char_data['level']})"
            if char_data['background'] != "Unknown":
                char_summary += f"\n*{char_data['background']}*"
            
            # Add key equipment if specified
            if char_data['equipment'] != "Basic adventuring gear":
                equipment_brief = char_data['equipment'][:60] + ("..." if len(char_data['equipment']) > 60 else "")
                char_summary += f"\n🎒 {equipment_brief}"
            
            # Add affiliations if any
            if char_data['affiliations'] != "None":
                affiliations_brief = char_data['affiliations'][:50] + ("..." if len(char_data['affiliations']) > 50 else "")
                char_summary += f"\n🏛️ {affiliations_brief}"
            
            embed.add_field(
                name=f"⚔️ {char_data['name']} ({current_player_name})",
                value=char_summary,
                inline=False
            )
    
    embed.set_footer(text=f"Party size: {len(campaign_context['characters'])} heroes ready for adventure!")
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="character_sheet", description="View detailed character information")
@app_commands.describe(player="View another player's character (optional)")
async def view_character_sheet(interaction: discord.Interaction, player: Optional[discord.Member] = None):
    """Show detailed character sheet"""
    target_user = player or interaction.user
    user_id = str(target_user.id)
    
    if user_id not in campaign_context["characters"]:
        embed = discord.Embed(
            title="❌ Character Not Found",
            description=f"No character registered for {target_user.display_name}. Use `/character` to register!",
            color=0xFF6B6B
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    
    # Get character data
    char_data = campaign_context["players"][user_id]["character_data"]
    
    embed = discord.Embed(
        title=f"📜 Character Sheet: {char_data['name']}",
        description=f"**{char_data['race']} {char_data['class']}** (Level {char_data['level']})",
        color=0x4169E1
    )

    embed.add_field(name="📚 Background", value=char_data['background'], inline=True)
    embed.add_field(name="📊 Ability Scores", value=char_data['stats'], inline=True)
    embed.add_field(name="👤 Player", value=target_user.display_name, inline=True)
    embed.add_field(name="⚔️ Equipment & Items", value=char_data['equipment'], inline=False)
    
    if char_data['spells'] not in ["None", "Basic spells for class"]:
        embed.add_field(name="✨ Spells & Abilities", value=char_data['spells'], inline=False)
    
    if char_data['affiliations'] != "None":
        embed.add_field(name="🏛️ Affiliations & Connections", value=char_data['affiliations'], inline=False)
    
    if char_data['personality'] != "To be determined in play":
        embed.add_field(name="🎭 Personality & Roleplay", value=char_data['personality'], inline=False)
    
    embed.set_footer(text="Use /update_character to modify details • /character_progression to view progression")
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="update_character", description="Update specific aspects of your character")
@app_commands.describe(
    aspect="What to update",
    new_value="The new value"
)
@app_commands.choices(aspect=[
    app_commands.Choice(name="Level", value="level"),
    app_commands.Choice(name="Stats/Ability Scores", value="stats"),
    app_commands.Choice(name="Equipment/Items", value="equipment"), 
    app_commands.Choice(name="Spells/Abilities", value="spells"),
    app_commands.Choice(name="Affiliations/Connections", value="affiliations"),
    app_commands.Choice(name="Personality/Roleplay", value="personality")
])
async def update_character(interaction: discord.Interaction, aspect: str, new_value: str):
    """Update specific character aspects"""
    user_id = str(interaction.user.id)
    player_name = interaction.user.display_name
    
    if user_id not in campaign_context["characters"]:
        embed = discord.Embed(
            title="❌ No Character Found",
            description="Please register a character first using `/character`!",
            color=0xFF6B6B
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    
    # Get current character data
    char_data = campaign_context["players"][user_id]["character_data"]
    
    # Update the specified aspect
    if aspect == "level":
        try:
            level = int(new_value)
            if level < 1 or level > 20:
                await interaction.response.send_message("❌ Level must be between 1 and 20! Use `/level_up` to properly track progression.", ephemeral=True)
                return
            char_data["level"] = level
        except ValueError:
            await interaction.response.send_message("❌ Level must be a number!", ephemeral=True)
            return
    else:
        char_data[aspect] = new_value
    
    # Update player name in case it changed
    char_data["player_name"] = player_name
    
    # Rebuild character description for Claude
    character_description = f"""
NAME: {char_data['name']}
PLAYER: {player_name} (Discord ID: {user_id})
RACE & CLASS: {char_data['race']} {char_data['class']} (Level {char_data['level']})
BACKGROUND: {char_data['background']}
ABILITY SCORES: {char_data['stats']}
EQUIPMENT: {char_data['equipment']}
SPELLS: {char_data['spells']}
AFFILIATIONS: {char_data['affiliations']}
PERSONALITY: {char_data['personality']}
"""
    
    # Update stored data
    campaign_context["characters"][user_id] = character_description
    campaign_context["players"][user_id]["character_description"] = character_description
    campaign_context["players"][user_id]["player_name"] = player_name
    
    # Create confirmation embed  
    aspect_names = {
        "level": "⭐ Level",
        "stats": "📊 Ability Scores",
        "equipment": "⚔️ Equipment", 
        "spells": "✨ Spells",
        "affiliations": "🏛️ Affiliations",
        "personality": "🎭 Personality"
    }
    
    embed = discord.Embed(
        title=f"✅ {char_data['name']} Updated!",
        color=0x32CD32
    )
    
    embed.add_field(
        name=f"{aspect_names[aspect]} Updated",
        value=new_value,
        inline=False
    )
    
    embed.set_footer(text="Character changes will be saved to the next episode snapshot")
    await interaction.response.send_message(embed=embed)

# ====== CORE GAMEPLAY COMMANDS ======

@bot.tree.command(name="start", description="Begin your Storm King's Thunder adventure (legacy - use /start_episode)")
async def start_adventure(interaction: discord.Interaction):
    """Start the Storm King's Thunder campaign (legacy command)"""
    
    # Check if we have any characters registered
    if not campaign_context["characters"]:
        embed = discord.Embed(
            title="⚡ Welcome to Storm King's Thunder!",
            description="Before we begin our adventure, we need to know who you are!",
            color=0xFF6B6B
        )
        
        embed.add_field(
            name="🎭 Character Registration Required",
            value="Please use `/character` to register your character before starting.\n\nThis helps the AI DM personalize the adventure for your specific character!",
            inline=False
        )
        
        embed.add_field(
            name="📝 Required Information",
            value="**Basic:** Name, Race, Class, Level\n**Optional:** Background, Stats, Equipment, Spells, Affiliations, Personality",
            inline=False
        )
        
        embed.add_field(
            name="🆕 New Episode System",
            value="**Recommended:** Use `/start_episode` instead for full episode management with recaps and progression tracking!",
            inline=False
        )
        
        embed.set_footer(text="Use /help for more detailed instructions!")
        await interaction.response.send_message(embed=embed)
        return
    
    # If characters are registered, start the adventure
    campaign_context["session_started"] = True
    
    embed = discord.Embed(
        title="⚡ Storm King's Thunder - Adventure Begins!",
        description=campaign_context["current_scene"],
        color=0x1E90FF
    )
    
    embed.add_field(
        name="🏔️ The Giant Crisis",
        value="Giants raid settlements across the Sword Coast. The ancient ordning that maintained giant society has shattered, throwing giantkind into chaos. Small folk live in terror as massive beings roam the land unchecked.",
        inline=False
    )
    
    # Show detailed party composition
    party_info = []
    for user_id, character_desc in campaign_context["characters"].items():
        if user_id in campaign_context["players"]:
            player_data = campaign_context["players"][user_id]
            char_data = player_data["character_data"]
            current_player_name = player_data["player_name"]
            party_info.append(f"**{char_data['name']}** - {char_data['race']} {char_data['class']} (Level {char_data['level']}) - *{current_player_name}*")
    
    embed.add_field(
        name="🗡️ Your Heroic Party",
        value="\n".join(party_info),
        inline=False
    )
    
    embed.add_field(
        name="⚔️ Ready for Action",
        value="Use `/action <what you do>` to interact with the world. The AI DM will respond based on your character's capabilities and the unfolding story.\n\n🎤 **Voice Narration:** Join a voice channel and use `/join_voice` to have Donnie speak his responses with dramatic flair!\n\n🤖 **Smart Combat:** Combat triggers automatically with intelligent monster AI!",
        inline=False
    )
    
    embed.add_field(
        name="🆕 Episode Management Available",
        value="Use `/start_episode` for full campaign management with episode recaps, character progression tracking, and persistent story memory!",
        inline=False
    )
    
    embed.set_footer(text="What do you do in this moment of crisis?")
    await interaction.response.send_message(embed=embed)

# ====== FIXED ACTION COMMAND - STEP 4 OF STATE SYNC FIX ======

@bot.tree.command(name="action", description="Take an action in the Storm King's Thunder campaign")
@app_commands.describe(what_you_do="Describe what your character does or says")
async def take_action(interaction: discord.Interaction, what_you_do: str):
    """Streamlined action processing - FAST"""
    user_id = str(interaction.user.id)
    player_name = interaction.user.display_name
    guild_id = str(interaction.guild.id)
    
    # ✅ FORCE SYNC BEFORE CHECKING STATE
    await ensure_state_sync(guild_id)
    
    # Quick validation
    if user_id not in campaign_context["characters"]:
        embed = discord.Embed(
            title="🎭 Character Not Registered",
            description=f"Please register your character first using `/character`!",
            color=0xFF6B6B
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    
    # ✅ CHECK BOTH CONDITIONS WITH DEBUG INFO
    session_started = campaign_context.get("session_started", False)
    episode_active = campaign_context.get("episode_active", False)
    
    print(f"🔍 Action check - session_started: {session_started}, episode_active: {episode_active}")
    
    if not session_started and not episode_active:
        embed = discord.Embed(
            title="⚡ Adventure Not Started",
            description=f"Use `/start_episode` or `/start` to begin!\n\n**Debug Info:**\nSession Started: {session_started}\nEpisode Active: {episode_active}\nCurrent Episode: {campaign_context.get('current_episode', 0)}",
            color=0xFF6B6B
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    
    # Get character data (rest of function stays the same)
    char_data = campaign_context["players"][user_id]["character_data"]
    character_name = char_data["name"]
    
    # Update player name
    campaign_context["players"][user_id]["player_name"] = player_name
    
    # Create response embed with character name and class
    char_title = f"{character_name} ({char_data['race']} {char_data['class']})"
    
    embed = discord.Embed(color=0x2E8B57)
    embed.add_field(
        name=f"🎭 {char_title}",
        value=what_you_do,
        inline=False
    )
    embed.add_field(
        name="🐉 Donnie the DM",
        value="*Donnie considers his response...*",
        inline=False
    )
    
    # Add voice status indicator
    voice_will_speak = (interaction.guild.id in voice_clients and 
                       voice_clients[interaction.guild.id].is_connected() and 
                       tts_enabled.get(interaction.guild.id, False))
    
    if voice_will_speak:
        embed.add_field(name="🎤", value="*Donnie prepares his response...*", inline=False)
    elif interaction.guild.id in voice_clients and voice_clients[interaction.guild.id].is_connected():
        embed.add_field(name="🔇", value="*Donnie is muted*", inline=False)
    
    # Add character context footer with combat status
    episode_info = f"Level {char_data['level']} • {char_data['background']} • Player: {player_name}"
    if campaign_context.get("episode_active", False):
        episode_info += f" • Episode {campaign_context.get('current_episode', 0)}"
    if combat_state["active"]:
        episode_info += f" • ⚔️ Combat Active"
    embed.set_footer(text=episode_info)
    
    # Send the response IMMEDIATELY
    await interaction.response.send_message(embed=embed)
    message = await interaction.original_response()
    
    # Play thinking sound immediately if voice is enabled (fills the waiting gap)
    if voice_will_speak:
        asyncio.create_task(play_thinking_sound(interaction.guild.id, character_name))
    
    # Process Claude API call in background with enhanced combat intelligence
    asyncio.create_task(process_enhanced_dm_response_background(
        user_id, what_you_do, message, character_name, char_data, 
        player_name, interaction.guild.id, voice_will_speak
    ))

async def process_enhanced_dm_response_background(user_id: str, player_input: str, message, 
                                                character_name: str, char_data: dict, 
                                                player_name: str, guild_id: int, voice_will_speak: bool):
    """Process DM response with enhanced combat intelligence and automatic continuation support"""
    try:
        # Use enhanced DM response with combat intelligence
        dm_response = await get_enhanced_claude_dm_response(user_id, player_input)
        
        # Get TTS version and continuation
        tts_text, continuation_text = create_tts_version_with_continuation(dm_response)
        
        # Update the message with the actual response (show full response in text)
        embed = message.embeds[0]
        
        # Update DM response field with FULL response
        for i, field in enumerate(embed.fields):
            if field.name == "🐉 Donnie the DM":
                embed.set_field_at(i, name="🐉 Donnie the DM", value=dm_response, inline=False)
                break
        
        await message.edit(embed=embed)
        
        # Add to voice queue if voice is enabled (use TTS-optimized version for speed)
        if voice_will_speak:
            await add_to_voice_queue(guild_id, tts_text, character_name, message)
        
        # Send continuation if needed
        if continuation_text:
            await send_continuation_if_needed(
                message, dm_response, tts_text, continuation_text, guild_id, character_name
            )
            
    except Exception as e:
        print(f"Enhanced background processing error: {e}")
        import traceback
        traceback.print_exc()
        
        # Fall back to original system
        try:
            print("Falling back to original Claude system...")
            dm_response = await get_claude_dm_response(user_id, player_input)
            embed = message.embeds[0]
            for i, field in enumerate(embed.fields):
                if field.name == "🐉 Donnie the DM":
                    embed.set_field_at(i, name="🐉 Donnie the DM", value=dm_response, inline=False)
                    break
            await message.edit(embed=embed)
            
            if voice_will_speak:
                await add_to_voice_queue(guild_id, dm_response, character_name, message)
        except Exception as e2:
            print(f"Fallback system also failed: {e2}")
            import traceback
            traceback.print_exc()
            
            # Final fallback
            embed = message.embeds[0]
            for i, field in enumerate(embed.fields):
                if field.name == "🐉 Donnie the DM":
                    embed.set_field_at(i, name="🐉 Donnie the DM", 
                                     value="*The DM pauses as otherworldly forces intervene...*", inline=False)
                    break
            await message.edit(embed=embed)

@bot.tree.command(name="roll", description="Roll dice for your Storm King's Thunder adventure")
@app_commands.describe(dice="Dice notation like 1d20, 3d6, 2d8+3")
async def roll_dice(interaction: discord.Interaction, dice: str = "1d20"):
    """Roll dice with D&D notation"""
    try:
        # Handle simple modifier (like 1d20+5)
        modifier = 0
        if '+' in dice:
            dice_part, mod_part = dice.split('+')
            modifier = int(mod_part.strip())
            dice = dice_part.strip()
        elif '-' in dice and dice.count('-') == 1:
            dice_part, mod_part = dice.split('-')
            modifier = -int(mod_part.strip())
            dice = dice_part.strip()
        
        if 'd' in dice:
            num_dice, die_size = dice.split('d')
            num_dice = int(num_dice) if num_dice else 1
            die_size = int(die_size)
            
            if num_dice > 20 or die_size > 1000:
                await interaction.response.send_message("❌ Maximum 20 dice of size 1000!", ephemeral=True)
                return
            
            rolls = [random.randint(1, die_size) for _ in range(num_dice)]
            total = sum(rolls) + modifier
            
            # Format the result
            result_text = f"🎲 **{interaction.user.display_name}** rolled {dice}"
            if modifier != 0:
                result_text += f"{'+' if modifier > 0 else ''}{modifier}"
            
            if len(rolls) > 1:
                result_text += f"\n**Rolls:** {rolls}"
                if modifier != 0:
                    result_text += f" {'+' if modifier > 0 else ''}{modifier}"
                result_text += f" = **{total}**"
            else:
                if modifier != 0:
                    result_text += f"\n**Roll:** {rolls[0]} {'+' if modifier > 0 else ''}{modifier} = **{total}**"
                else:
                    result_text += f"\n**Result:** **{total}**"
            
            # Add context for common D&D rolls
            if dice == "1d20":
                if rolls[0] == 20:
                    result_text += " 🎯 **Natural 20!**"
                elif rolls[0] == 1:
                    result_text += " 💥 **Natural 1!**"
            
            await interaction.response.send_message(result_text)
        else:
            await interaction.response.send_message("❌ Use dice notation like: 1d20, 3d6, 2d8+3", ephemeral=True)
            
    except ValueError:
        await interaction.response.send_message("❌ Invalid dice notation! Use format like: 1d20, 3d6, 2d8+3", ephemeral=True)

@bot.tree.command(name="status", description="Show current Storm King's Thunder campaign status")
async def show_status(interaction: discord.Interaction):
    """Display campaign status"""
    embed = discord.Embed(
        title="⚡ Storm King's Thunder - Campaign Status",
        color=0x4B0082
    )
    
    embed.add_field(
        name="📍 Current Scene",
        value=campaign_context["current_scene"],
        inline=False
    )
    
    # Show characters if any are registered
    if campaign_context["characters"]:
        party_info = []
        for user_id, character_desc in campaign_context["characters"].items():
            if user_id in campaign_context["players"]:
                player_data = campaign_context["players"][user_id]
                char_data = player_data["character_data"]
                current_player_name = player_data["player_name"]
                character_name = char_data["name"]
                party_info.append(f"**{character_name}** ({current_player_name})")
        
        embed.add_field(
            name="🗡️ Party Members",
            value="\n".join(party_info),
            inline=True
        )
    else:
        embed.add_field(
            name="🗡️ Party Members",
            value="No characters registered yet",
            inline=True
        )
    
    # Episode information
    episode_status = "⏸️ Not Started"
    if campaign_context.get("episode_active", False):
        episode_status = f"📺 Episode {campaign_context.get('current_episode', 0)} Active"
    elif campaign_context.get("session_started", False):
        episode_status = "✅ Legacy Session Active"
    
    embed.add_field(
        name="🎬 Episode Status",
        value=episode_status,
        inline=True
    )
    
    embed.add_field(
        name="📜 Session Progress",
        value=f"{len(campaign_context['session_history'])} interactions",
        inline=True
    )
    
    # Combat status
    combat_status = "⚔️ No Active Combat"
    if combat_state["active"]:
        combat_status = f"⚔️ **{combat_state['encounter_name']}** - Round {combat_state['round']}"
    
    embed.add_field(
        name="🤖 Combat Intelligence",
        value=combat_status,
        inline=True
    )
    
    # Voice status
    guild_id = interaction.guild.id
    if guild_id in voice_clients and voice_clients[guild_id].is_connected():
        if tts_enabled.get(guild_id, False):
            speed = voice_speed.get(guild_id, 1.25)
            queue_size = len(voice_queue.get(guild_id, []))
            if queue_size > 0:
                voice_status = f"🎤 Connected ({speed}x speed, {queue_size} queued)"
            else:
                voice_status = f"🎤 Connected ({speed}x speed)"
        else:
            voice_status = "🔇 Muted"
    else:
        voice_status = "🔇 Not Connected"
    
    embed.add_field(
        name="🎭 Donnie's Voice",
        value=voice_status,
        inline=True
    )
    
    embed.add_field(
        name="🏔️ Giant Threat Level",
        value="🔴 **CRITICAL** - Multiple giant types terrorizing the Sword Coast",
        inline=False
    )
    
    if not campaign_context["characters"]:
        embed.add_field(
            name="⚠️ Next Step",
            value="Use `/character` to register your character, then `/start_episode` to begin with full episode management and intelligent combat!",
            inline=False
        )
    elif not campaign_context.get("session_started", False) and not campaign_context.get("episode_active", False):
        embed.add_field(
            name="⚠️ Next Step", 
            value="Use `/start_episode` for full episode management or `/start` for simple session with smart combat!",
            inline=False
        )
    
    await interaction.response.send_message(embed=embed)

# ====== COMBAT COMMANDS ======

@bot.tree.command(name="combat_status", description="View current combat status and initiative order")
async def view_combat_status(interaction: discord.Interaction):
    """Show current combat status"""
    
    if not combat_state["active"]:
        embed = discord.Embed(
            title="⚔️ Combat Status",
            description="No active combat encounter.",
            color=0x808080
        )
        
        embed.add_field(
            name="💡 Starting Combat",
            value="Combat will start automatically when you take hostile actions or encounter enemies!\n\nJust use `/action` to describe what you do - Donnie will handle the rest.",
            inline=False
        )
        
        embed.add_field(
            name="🤖 Intelligence Features",
            value="• **Auto-Detection**: Combat triggers based on your actions\n• **Story Encounters**: Enemies fit the current scene\n• **Smart AI**: Monsters act based on their Intelligence scores\n• **Initiative Management**: Automatic turn order",
            inline=False
        )
        
        await interaction.response.send_message(embed=embed)
        return
    
    embed = discord.Embed(
        title=f"⚔️ {combat_state['encounter_name']}",
        description=f"**Round {combat_state['round']}** - Combat in progress!",
        color=0xFF4500
    )
    
    # Show initiative order
    init_order = []
    for i, (entity_id, initiative, is_player, name) in enumerate(combat_state["initiative_order"]):
        marker = "▶️" if i == combat_state["current_turn"] else "⏸️"
        icon = "🎭" if is_player else "👹"
        init_order.append(f"{marker} {icon} **{name}** ({initiative})")
    
    embed.add_field(
        name="🎲 Initiative Order",
        value="\n".join(init_order),
        inline=False
    )
    
    # Show party status
    party_status = []
    for user_id, player_data in campaign_context["players"].items():
        char_data = player_data["character_data"]
        char_name = char_data["name"]
        # Would show actual HP if tracked
        party_status.append(f"🎭 **{char_name}**: Ready for action")
    
    if party_status:
        embed.add_field(
            name="🗡️ Party Status",
            value="\n".join(party_status),
            inline=True
        )
    
    # Show enemies
    enemy_status = []
    for enemy in combat_state["monsters"].get("enemies", []):
        enemy_status.append(f"👹 **{enemy['name']}**: {enemy['hp']}/{enemy['max_hp']} HP")
    
    if enemy_status:
        embed.add_field(
            name="👹 Enemies",
            value="\n".join(enemy_status),
            inline=True
        )
    
    embed.add_field(
        name="🎮 How to Play",
        value="Use `/action` to describe what you want to do!\n\nDonnie will automatically handle:\n• Initiative order\n• Monster AI turns\n• Damage calculation\n• Combat flow",
        inline=False
    )
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="end_combat", description="End the current combat encounter (Admin only)")
async def end_combat_command(interaction: discord.Interaction):
    """End combat encounter"""
    
    if not hasattr(interaction.user, 'guild_permissions') or not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ Only administrators can end combat!", ephemeral=True)
        return
    
    if not combat_state["active"]:
        await interaction.response.send_message("❌ No active combat to end!", ephemeral=True)
        return
    
    # Reset combat state
    encounter_name = combat_state["encounter_name"]
    combat_state["active"] = False
    combat_state["encounter_name"] = ""
    combat_state["round"] = 1
    combat_state["initiative_order"] = []
    combat_state["current_turn"] = 0
    combat_state["monsters"] = {}
    combat_state["combat_log"] = []
    
    embed = discord.Embed(
        title="✅ Combat Ended",
        description=f"**{encounter_name}** has been concluded.",
        color=0x32CD32
    )
    
    embed.add_field(
        name="🎉 Resolution",
        value="Combat has been ended by the DM. The party can continue their adventure!",
        inline=False
    )
    
    await interaction.response.send_message(embed=embed)

# ====== WORLD INFORMATION COMMANDS ======

@bot.tree.command(name="scene", description="View the current scene in detail")
async def view_scene(interaction: discord.Interaction):
    """Show detailed current scene"""
    embed = discord.Embed(
        title="📍 Current Scene",
        description=campaign_context["current_scene"],
        color=0x8FBC8F
    )
    
    embed.add_field(
        name="🗺️ Location Context",
        value="You are in the Sword Coast region, where the giant crisis has created chaos and fear among the small folk.",
        inline=False
    )
    
    embed.set_footer(text="Use /action to interact with your surroundings")
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="locations", description="Learn about key Sword Coast locations")
async def show_locations(interaction: discord.Interaction):
    """Show key Sword Coast locations"""
    embed = discord.Embed(
        title="🗺️ Key Locations - The Sword Coast",
        description="Important places in your Storm King's Thunder adventure",
        color=0x228B22
    )
    
    embed.add_field(
        name="🏰 Nightstone",
        value="Small village recently attacked by cloud giants and abandoned",
        inline=False
    )
    
    embed.add_field(
        name="🏰 Waterdeep",
        value="The City of Splendors, major hub of trade and politics",
        inline=False
    )
    
    embed.add_field(
        name="🏰 Neverwinter",
        value="Rebuilt city, seat of Lord Neverember's power",
        inline=False
    )
    
    embed.add_field(
        name="🏰 Triboar",
        value="Important crossroads town and target of giant raids",
        inline=False
    )
    
    embed.add_field(
        name="🏰 Bryn Shander",
        value="Largest settlement in Ten-Towns, threatened by frost giants",
        inline=False
    )
    
    embed.add_field(
        name="🏰 Ironslag",
        value="Fire giant stronghold where Duke Zalto forges weapons",
        inline=False
    )
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="campaign", description="Show comprehensive Storm King's Thunder campaign information")
async def show_campaign_info(interaction: discord.Interaction):
    """Show Storm King's Thunder campaign information"""
    embed = discord.Embed(
        title="⚡ Storm King's Thunder - Campaign Information",
        description="The giant crisis threatening the Sword Coast",
        color=0x191970
    )
    
    embed.add_field(
        name="📖 Campaign Setting",
        value=campaign_context["setting"][:800] + ("..." if len(campaign_context["setting"]) > 800 else ""),
        inline=False
    )
    
    embed.add_field(
        name="⚡ Current Crisis",
        value="Giants roam the land in unprecedented numbers. The ordning has collapsed. Heroes are needed to restore order and protect the innocent.",
        inline=False
    )
    
    embed.add_field(
        name="🎯 Key NPCs",
        value="**Zephyros** - Ancient cloud giant wizard\n**Harshnag** - Frost giant ally\n**Princess Serissa** - Storm giant princess\n**Duke Zalto** - Fire giant weaponsmith",
        inline=False
    )
    
    embed.set_footer(text="Use /locations for more detailed location information")
    await interaction.response.send_message(embed=embed)

# ====== ADMIN COMMANDS ======

@bot.tree.command(name="set_scene", description="Update the current scene (Admin only)")
@app_commands.describe(scene_description="The new scene description")
async def set_scene(interaction: discord.Interaction, scene_description: str):
    """Update current scene (Admin only)"""
    if hasattr(interaction.user, 'guild_permissions') and interaction.user.guild_permissions.administrator:
        campaign_context["current_scene"] = scene_description
        embed = discord.Embed(
            title="🏛️ Scene Updated",
            description=scene_description,
            color=0x4169E1
        )
        await interaction.response.send_message(embed=embed)
    else:
        await interaction.response.send_message("❌ Only server administrators can update scenes!", ephemeral=True)

@bot.tree.command(name="cleanup_confirmations", description="Clean up expired character sheet confirmations (Admin only)")
async def cleanup_confirmations(interaction: discord.Interaction):
    """Clean up expired confirmations (Admin only)"""
    if not hasattr(interaction.user, 'guild_permissions') or not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ Only server administrators can use this command!", ephemeral=True)
        return
    
    try:
        # Import the PDF character parser
        from pdf_character_parser import PDFCharacterCommands
        
        if hasattr(bot, 'pdf_character_commands') and bot.pdf_character_commands:
            expired_count = bot.pdf_character_commands.cleanup_expired_confirmations()
            embed = discord.Embed(
                title="🧹 Cleanup Complete",
                description=f"Removed {expired_count} expired character sheet confirmations",
                color=0x32CD32
            )
        else:
            embed = discord.Embed(
                title="⚠️ PDF System Not Available",
                description="The PDF character system is not currently loaded",
                color=0xFFD700
            )
        
        await interaction.response.send_message(embed=embed)
        
    except Exception as e:
        await interaction.response.send_message(f"❌ Error during cleanup: {str(e)}", ephemeral=True)

# ====== HELP COMMAND ======

@bot.tree.command(name="help", description="Show comprehensive guide for the Storm King's Thunder TTS bot")
async def show_help(interaction: discord.Interaction):
    """Show comprehensive bot guide including TTS features, episode management, combat intelligence, and PDF uploads"""
    embed = discord.Embed(
        title="⚡ Storm King's Thunder TTS Bot - Complete Guide",
        description="Your AI-powered D&D 5e adventure with Donnie the DM's optimized voice, episode management, and intelligent combat!",
        color=0x4169E1
    )
    
    embed.add_field(
        name="🎤 Voice Features (OPTIMIZED!)",
        value="`/join_voice` - Donnie joins voice with fast, optimized narration\n`/leave_voice` - Donnie leaves voice channel\n`/mute_donnie` - Disable TTS narration\n`/unmute_donnie` - Enable TTS narration\n`/donnie_speed <1.0-2.0>` - Adjust speaking speed\n`/debug_state` - Show state sync info (Admin)",
        inline=False
    )
    
    embed.add_field(
        name="📄 Character Upload",
        value="`/upload_character_sheet` - Upload PDF character sheet for auto-parsing\n`/character_sheet_help` - Get help with character sheet uploads\n`/character` - Manual character registration (alternative)",
        inline=False
    )
    
    embed.add_field(
        name="⚔️ Intelligent Combat",
        value="`/combat_status` - View current combat and initiative\n`/end_combat` - End combat encounter (Admin only)\n**Auto-Combat**: Combat triggers automatically from your actions!\n**Smart AI**: Monsters act based on Intelligence scores",
        inline=False
    )
    
    embed.add_field(
        name="📺 Episode Management",
        value="`/start_episode [name]` - Begin new episode with recap\n`/end_episode [summary]` - End current episode\n`/episode_recap [#] [style]` - Get AI dramatic recaps\n`/episode_history` - View past episodes\n`/episode_status` - Check current episode status",
        inline=False
    )
    
    embed.add_field(
        name="📈 Character Progression",
        value="`/level_up <level> [reason]` - Level up with tracking\n`/character_progression [player]` - View progression history\n`/character_snapshot [notes]` - Manual character snapshot\n`/party_progression` - View entire party progression",
        inline=False
    )
    
    embed.add_field(
        name="🎭 Character Management",
        value="`/character` - Register detailed character\n`/party` - View all party members\n`/character_sheet` - View character details\n`/update_character` - Modify character aspects",
        inline=False
    )
    
    embed.add_field(
        name="🎮 Core Gameplay",
        value="`/start_episode` - Begin with episode management (recommended)\n`/start` - Begin simple session (legacy)\n`/action <what_you_do>` - Take actions (AI DM responds + speaks quickly!)\n`/roll <dice>` - Roll dice (1d20+3, 3d6, etc.)\n`/status` - Show campaign status",
        inline=False
    )
    
    embed.add_field(
        name="📚 World Information",
        value="`/scene` - View current scene\n`/locations` - Sword Coast locations\n`/campaign` - Full campaign info",
        inline=False
    )
    
    embed.add_field(
        name="⚙️ Admin Commands",
        value="`/set_scene` - Update current scene\n`/cleanup_confirmations` - Clean up expired PDF confirmations\n`/end_combat` - End active combat encounter\n`/debug_state` - Show state synchronization info",
        inline=False
    )
    
    embed.add_field(
        name="🌟 State Sync Features (NEW!)",
        value="• **Automatic State Sync**: Memory and database always stay in sync\n• **Cross-Session Persistence**: Episodes persist across bot restarts\n• **Debug Tools**: `/debug_state` helps troubleshoot sync issues\n• **Smart Recovery**: Auto-fixes state mismatches\n• **Episode Continuity**: Never lose campaign progress",
        inline=False
    )
    
    embed.set_footer(text="Donnie the DM awaits to guide your persistent, voice-enabled, combat-intelligent campaign adventure!")
    await interaction.response.send_message(embed=embed)

# ====== ENHANCED SYSTEM INITIALIZATION ======

episode_commands = None
character_progression = None
enhanced_voice_manager = None

if EPISODE_MANAGER_AVAILABLE and DATABASE_AVAILABLE:
    try:
        episode_commands = EpisodeCommands(
            bot=bot,
            campaign_context=campaign_context,
            voice_clients=voice_clients,
            tts_enabled=tts_enabled,
            add_to_voice_queue_func=add_to_voice_queue,
            episode_operations=EpisodeOperations,  # Pass the operations class
            character_operations=CharacterOperations,  # Pass the operations class
            guild_operations=GuildOperations  # Pass the operations class
        )
        print("✅ Episode management system initialized with database support")
    except Exception as e:
        print(f"⚠️ Episode management initialization failed: {e}")
        import traceback
        traceback.print_exc()
        episode_commands = None
else:
    if not DATABASE_AVAILABLE:
        print("⚠️ Episode management disabled: Database not available")
    if not EPISODE_MANAGER_AVAILABLE:
        print("⚠️ Episode management disabled: Episode commands not available")

if CHARACTER_PROGRESSION_AVAILABLE and DATABASE_AVAILABLE:
    try:
        character_progression = CharacterProgressionCommands(
            bot=bot,
            campaign_context=campaign_context,
            voice_clients=voice_clients,
            tts_enabled=tts_enabled,
            add_to_voice_queue_func=add_to_voice_queue,
            character_operations=CharacterOperations,  # Correct parameter name
            episode_operations=EpisodeOperations  # Correct parameter name
        )
        print("✅ Character progression system initialized with database support")
    except Exception as e:
        print(f"⚠️ Character progression initialization failed: {e}")
        import traceback
        traceback.print_exc()
        character_progression = None
else:
    if not DATABASE_AVAILABLE:
        print("⚠️ Character progression disabled: Database not available")
    if not CHARACTER_PROGRESSION_AVAILABLE:
        print("⚠️ Character progression disabled: Progression commands not available")

# Initialize Enhanced Voice Manager - NEW!
if ENHANCED_AUDIO_AVAILABLE:
    try:
        enhanced_voice_manager = EnhancedVoiceManager(
            claude_client=claude_client,
            openai_api_key=os.getenv('OPENAI_API_KEY')
        )
        
        # Connect the voice manager functions to the actual implementations
        enhanced_voice_manager._get_claude_response = get_enhanced_claude_dm_response
        enhanced_voice_manager._generate_tts_audio = generate_tts_audio
        
        print("✅ Enhanced voice manager initialized")
    except Exception as e:
        print(f"⚠️ Enhanced voice manager initialization failed: {e}")
        enhanced_voice_manager = None

# Initialize PDF Character Sheet Commands - EXISTING
try:
    from pdf_character_parser import PDFCharacterCommands
    
    pdf_character_commands = PDFCharacterCommands(
        bot=bot,
        campaign_context=campaign_context,
        claude_client=claude_client
    )
    
    # Store reference for cleanup command
    bot.pdf_character_commands = pdf_character_commands  # type: ignore
    
    print("✅ PDF Character Sheet system initialized")
    
except ImportError as e:
    print(f"⚠️ PDF Character Sheet system not available: {e}")
    print("Install required packages: pip install PyPDF2 pymupdf pillow")
except Exception as e:
    print(f"❌ Error initializing PDF system: {e}")

# Add helper function to update database when campaign context changes
def update_database_from_campaign_context(guild_id: str):
    """Update database when campaign context changes"""
    if not DATABASE_AVAILABLE:
        return
    
    try:
        current_episode = EpisodeOperations.get_current_episode(guild_id)
        if current_episode and campaign_context.get("session_history"):
            # Update session history in database
            EpisodeOperations.update_session_history(
                current_episode.id,
                campaign_context["session_history"]
            )
        
        # Update guild settings
        GuildOperations.update_guild_settings(
            guild_id,
            voice_speed=voice_speed.get(guild_id, 1.25),
            tts_enabled=tts_enabled.get(guild_id, False),
            current_episode=campaign_context.get("current_episode", 0)
        )
        
    except Exception as e:
        print(f"⚠️ Failed to update database: {e}")

print("🎲 Storm King's Thunder TTS bot with Enhanced Episode Management ready!")
print("🔗 Database integration: " + ("✅ Active" if DATABASE_AVAILABLE else "❌ Disabled"))
print("📺 Episode management: " + ("✅ Active" if episode_commands else "❌ Disabled"))
print("📈 Character progression: " + ("✅ Active" if character_progression else "❌ Disabled"))
print("🎤 Enhanced voice: " + ("✅ Active" if enhanced_voice_manager else "❌ Disabled"))
print("🔄 State synchronization: ✅ Active")

if __name__ == "__main__":
    # Check for required dependencies
    print("🔍 Checking dependencies...")
    try:
        import discord
        print("✅ discord.py installed")
    except ImportError:
        print("❌ Install discord.py[voice]: pip install discord.py[voice]")
        exit(1)
    
    # Check for FFmpeg (required for voice)
    import subprocess
    try:
        subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True)
        print("✅ FFmpeg detected")
    except:
        print("⚠️ FFmpeg not found - required for voice features")
        print("Install FFmpeg: https://ffmpeg.org/download.html")
    
    # Check for PDF dependencies
    try:
        import PyPDF2
        import fitz  # PyMuPDF
        print("✅ PDF processing libraries detected")
    except ImportError:
        print("⚠️ PDF processing libraries not found")
        print("Install with: pip install PyPDF2 pymupdf pillow")
    
    # Combat system initialization messages
    print("✅ Seamless Combat Integration loaded!")
    print("🤖 Features: Auto-combat detection, AI monster intelligence, story-driven encounters")
    print("🎯 No new commands to learn - everything works through existing `/action` command!")
    print("⚔️ Combat will trigger automatically when players take hostile actions")
    print("🔄 State synchronization fixes applied!")
    
    # GET THE DISCORD TOKEN
    print("🔑 Checking Discord token...")
    try:
        token = os.getenv('DISCORD_BOT_TOKEN')
        if not token:
            print("❌ DISCORD_BOT_TOKEN not found in environment variables!")
            print("Make sure you have a .env file with DISCORD_BOT_TOKEN=your_token_here")
            print("Current working directory:", os.getcwd())
            print("Looking for .env file...")
            
            # Check if .env exists
            if os.path.exists('.env'):
                print("✅ .env file found")
                # Try to load it manually to see what's wrong
                with open('.env', 'r') as f:
                    content = f.read()
                    if 'DISCORD_BOT_TOKEN' in content:
                        print("✅ DISCORD_BOT_TOKEN found in .env")
                    else:
                        print("❌ DISCORD_BOT_TOKEN not found in .env file")
            else:
                print("❌ .env file not found")
            
            input("Press Enter to exit...")
            exit(1)
        else:
            print("✅ Discord token found")
    except Exception as e:
        print(f"❌ Error checking token: {e}")
        input("Press Enter to exit...")
        exit(1)
    
    # TRY TO START THE BOT WITH FULL ERROR HANDLING
    print("🚀 Starting Discord bot...")
    try:
        bot.run(token)
    except discord.LoginFailure:
        print("❌ INVALID DISCORD TOKEN!")
        print("Check that your bot token is correct in the .env file")
        input("Press Enter to exit...")
    except discord.HTTPException as e:
        print(f"❌ Discord HTTP Error: {e}")
        print("This might be a network issue or Discord API problem")
        input("Press Enter to exit...")
    except KeyboardInterrupt:
        print("🛑 Bot shutdown requested")
    except Exception as e:
        print(f"❌ UNEXPECTED ERROR: {e}")
        print("Full error details:")
        import traceback
        traceback.print_exc()
        input("Press Enter to exit...")
    finally:
        if DATABASE_AVAILABLE:
            try:
                close_database()
                print("✅ Cleanup completed")
            except:
                pass