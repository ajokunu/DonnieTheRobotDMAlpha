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

load_dotenv()

# Database and Episode Management Imports
from database.database import init_database, close_database
from episode_manager.episode_commands import EpisodeCommands  
from character_tracker.progression import CharacterProgressionCommands

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

# Storm King's Thunder DM Prompt (Enhanced for Donnie with 5e 2024 Adherence)
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

async def generate_tts_audio(text: str, voice: str = "fable", speed: float = 1.20) -> Optional[io.BytesIO]:
    """Generate TTS audio using OpenAI's Fable voice - optimized for speed"""
    try:
        # Clean text for TTS (remove excessive formatting)
        clean_text = text.replace("**", "").replace("*", "").replace("_", "")
        
        # Use OpenAI TTS API with optimized settings for speed
        async with aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=10),
            connector=aiohttp.TCPConnector(limit=10)
        ) as session:
            headers = {
                "Authorization": f"Bearer {os.getenv('OPENAI_API_KEY')}",
                "Content-Type": "application/json"
            }
            
            # OpenAI TTS payload optimized for speed
            payload = {
                "model": "tts-1-hd",  # voice quality model
                "input": clean_text,
                "voice": voice,  # "fable" voice - expressive and dramatic for storytelling
                "response_format": "opus",
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

def create_tts_version_with_continuation(full_text: str) -> tuple[str, str]:
    """
    Create TTS version and return both the spoken version and any continuation needed
    Returns: (tts_text, continuation_text)
    """
    import re
    
    original_text = full_text
    tts_text = full_text
    
    # Light cleanup - preserve the core message
    tts_text = re.sub(r'\b(very|quite|rather|extremely|incredibly|tremendously)\s+', '', tts_text)
    tts_text = re.sub(r'\b(suddenly|immediately|quickly|slowly)\s+', '', tts_text)
    tts_text = re.sub(r',\s+and\s+', ' and ', tts_text)
    tts_text = re.sub(r'\([^)]*\)', '', tts_text)
    tts_text = re.sub(r'\s+', ' ', tts_text).strip()
    
    continuation_text = ""
    
    # Check if we need to truncate for TTS speed - be more conservative
    if len(tts_text) > 400:  # Raised threshold to avoid unnecessary splits
        sentences = tts_text.split('. ')
        
        # Look for STRONG natural stopping points only
        natural_break_index = None
        for i, sentence in enumerate(sentences):
            # Only split at very clear breaks - questions or direct requests
            if any(indicator in sentence.lower() for indicator in [
                'what do you do?', 'roll a', 'make a', 'roll for', '?'
            ]) and i > 0:  # Don't split at the very first sentence
                natural_break_index = i + 1
                break
        
        # If we found a STRONG natural break, use it
        if natural_break_index and natural_break_index < len(sentences):
            spoken_sentences = sentences[:natural_break_index]
            remaining_sentences = sentences[natural_break_index:]
            
            tts_text = '. '.join(spoken_sentences) + '.'
            if remaining_sentences:
                continuation_text = '. '.join(remaining_sentences) + '.'
        
        # Only split at sentence boundaries if really long (500+ chars)
        elif len(tts_text) > 500 and len(sentences) > 3:
            # Take first half of sentences, but ensure we don't split mid-thought
            split_point = min(len(sentences) // 2, 3)  # Max 3 sentences in first part
            
            spoken_sentences = sentences[:split_point] 
            remaining_sentences = sentences[split_point:]
            
            tts_text = '. '.join(spoken_sentences) + '.'
            if remaining_sentences:
                continuation_text = '. '.join(remaining_sentences) + '.'
    
    # Clean up continuation text
    if continuation_text:
        continuation_text = continuation_text.strip()
        
        # Make sure continuation starts properly
        if continuation_text and not continuation_text[0].isupper():
            continuation_text = continuation_text[0].upper() + continuation_text[1:]
        
        # Remove any duplicate content between tts_text and continuation_text
        continuation_text = remove_duplicate_content(tts_text, continuation_text)
    
    return tts_text, continuation_text

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
    
    # Use faster speed for thinking sounds to keep them brief
    speed = voice_speed.get(guild_id, 1.25) * 1.2  # 20% faster for thinking sounds
    
    try:
        # Generate TTS audio quickly
        audio_data = await generate_tts_audio(text, voice="fable", speed=speed)
        if not audio_data:
            return
        
        # Save to temporary file
        with tempfile.NamedTemporaryFile(suffix=".opus", delete=False) as temp_file:
            temp_file.write(audio_data.getvalue())
            temp_filename = temp_file.name
        
        # Play immediately if not currently playing
        if not voice_client.is_playing():
            audio_source = discord.FFmpegPCMAudio(temp_filename)
            voice_client.play(audio_source)
            
            # Wait for this short sound to finish
            while voice_client.is_playing():
                await asyncio.sleep(0.1)
        
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
    
    # Generate TTS audio with optimized text
    audio_data = await generate_tts_audio(tts_text, voice="fable", speed=speed)
    if not audio_data:
        return
    
    # Save to temporary file
    with tempfile.NamedTemporaryFile(suffix=".opus", delete=False) as temp_file:
        temp_file.write(audio_data.getvalue())
        temp_filename = temp_file.name
    
    try:
        # Wait for any current audio to finish
        while voice_client.is_playing():
            await asyncio.sleep(0.1)
        
        # Play audio in voice channel
        audio_source = discord.FFmpegPCMAudio(temp_filename)
        voice_client.play(audio_source)
        
        # Wait for audio to finish
        while voice_client.is_playing():
            await asyncio.sleep(0.5)
            
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

async def get_claude_dm_response(user_id: str, player_input: str):
    """Get DM response from Claude"""
    try:
        # Get character and player info
        player_data = campaign_context["players"][user_id]
        char_data = player_data["character_data"]
        player_name = player_data["player_name"]
        character_name = char_data["name"]
        
        # Format character information for the prompt
        character_info = []
        for uid, char_desc in campaign_context["characters"].items():
            if uid in campaign_context["players"]:
                p_data = campaign_context["players"][uid]
                c_data = p_data["character_data"]
                character_info.append(f"{c_data['name']} ({p_data['player_name']}): {char_desc}")
        
        characters_text = "\n".join(character_info) if character_info else "No characters registered yet"
        
        formatted_prompt = DM_PROMPT.format(
            setting=campaign_context["setting"],
            current_scene=campaign_context["current_scene"],
            session_history=campaign_context["session_history"][-3:],
            characters=characters_text,
            players=[p["player_name"] for p in campaign_context["players"].values()],
            player_input=f"{character_name} ({player_name}): {player_input}"
        )
        
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
        
        # Handle the response content properly
        if hasattr(response.content[0], 'text'):
            dm_response = response.content[0].text.strip()
        else:
            # Fallback for different response types
            dm_response = str(response.content[0]).strip()
        
        # Update session history
        campaign_context["session_history"].append({
            "player": f"{character_name} ({player_name})",
            "action": player_input,
            "dm_response": dm_response
        })
        
        if len(campaign_context["session_history"]) > 10:
            campaign_context["session_history"] = campaign_context["session_history"][-10:]
        
        return dm_response
        
    except Exception as e:
        print(f"Claude API error: {e}")
        return "The DM pauses momentarily as otherworldly forces intervene... (Error occurred)"

@bot.event
async def on_ready():
    print(f'⚡ {bot.user} is ready for Storm King\'s Thunder!')
    print(f'🏔️ Giants threaten the Sword Coast!')
    print(f'🎤 Donnie the DM is ready to speak!')
    
    # Initialize database
    try:
        init_database()
        print("✅ Database initialized successfully")
    except Exception as e:
        print(f"❌ Database initialization failed: {e}")
    
    print('🔄 Syncing slash commands...')
    
    # Check for FFmpeg
    import subprocess
    try:
        subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True)
        print("✅ FFmpeg detected")
    except:
        print("⚠️  FFmpeg not found - required for voice features")
        
    try:
        synced = await bot.tree.sync()
        print(f'✅ Synced {len(synced)} slash commands')
        print("🎲 Storm King's Thunder TTS bot with Episode Management ready for adventure!")
    except Exception as e:
        print(f'❌ Failed to sync commands: {e}')
        import traceback
        traceback.print_exc()

@bot.event
async def on_disconnect():
    print("🔌 Bot disconnecting...")
    close_database()
    print("✅ Database connections closed")

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return
    await bot.process_commands(message)

# ====== VOICE CHANNEL COMMANDS ======

@bot.tree.command(name="join_voice", description="Donnie joins your voice channel to narrate the adventure")
async def join_voice_channel(interaction: discord.Interaction):
    """Join the user's voice channel"""
    if not interaction.user.voice:
        await interaction.response.send_message("❌ You need to be in a voice channel first!", ephemeral=True)
        return
    
    if not campaign_context.get("session_started", False) and not campaign_context.get("episode_active", False):
        await interaction.response.send_message("❌ Start the campaign first with `/start` or `/start_episode`!", ephemeral=True)
        return
    
    voice_channel = interaction.user.voice.channel
    guild_id = interaction.guild.id
    
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
        welcome_text = "Greetings, brave adventurers! I am Donnie, your Dungeon Master. I'll be narrating this Storm King's Thunder campaign, you might be thinking, ah a fake robot I can def exploit this guy to cheat my way to the top of the party and eventually bust this campaign wide open, we'll see about that fiends, but anyway yeah just type in forward slash action and tell me what you want to try and do and lets tell this story together shall we!"
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

@bot.tree.command(name="donnie_speed", description="Adjust Donnie's speaking speed")
@app_commands.describe(speed="Speaking speed (0.5 = very slow, 1.0 = normal, 1.5 = fast, 2.0 = very fast)")
async def adjust_voice_speed(interaction: discord.Interaction, speed: float):
    """Adjust TTS speaking speed"""
    guild_id = interaction.guild.id
    
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
        name="🎤 Realistic DM Experience",
        value="Donnie now uses thinking sounds, paper shuffling, and natural DM behaviors while preparing responses!",
        inline=False
    )
    
    # Test the new speed with a quick message
    if tts_enabled.get(guild_id, False):
        test_message = f"Speed adjusted to {speed}x. This is how fast I speak now!"
        await add_to_voice_queue(guild_id, test_message, "Speed Test")
    
    await interaction.response.send_message(embed=embed)

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
        value="Start an episode with `/start_episode`, then use `/join_voice` to have Donnie narrate your adventure with dramatic voice and episode recaps!",
        inline=False
    )
    
    embed.set_footer(text="Character bound to your Discord account and will be saved to episode history!")
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
        value="Use `/action <what you do>` to interact with the world. The AI DM will respond based on your character's capabilities and the unfolding story.\n\n🎤 **Voice Narration:** Join a voice channel and use `/join_voice` to have Donnie speak his responses with dramatic flair!",
        inline=False
    )
    
    embed.add_field(
        name="🆕 Episode Management Available",
        value="Use `/start_episode` for full campaign management with episode recaps, character progression tracking, and persistent story memory!",
        inline=False
    )
    
    embed.set_footer(text="What do you do in this moment of crisis?")
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="action", description="Take an action in the Storm King's Thunder campaign")
@app_commands.describe(what_you_do="Describe what your character does or says")
async def take_action(interaction: discord.Interaction, what_you_do: str):
    """Process player action and get DM response with TTS - INSTANT response"""
    user_id = str(interaction.user.id)
    player_name = interaction.user.display_name
    
    # Check if player has registered a character
    if user_id not in campaign_context["characters"]:
        embed = discord.Embed(
            title="🎭 Character Not Registered",
            description=f"Please register your character first using `/character`!",
            color=0xFF6B6B
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    
    # Check if session has started
    if not campaign_context.get("session_started", False) and not campaign_context.get("episode_active", False):
        embed = discord.Embed(
            title="⚡ Adventure Not Started",
            description="Use `/start_episode` (recommended) or `/start` to begin the Storm King's Thunder adventure first!",
            color=0xFF6B6B
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    
    # Get character data
    char_data = campaign_context["players"][user_id]["character_data"]
    character_name = char_data["name"]
    
    # Update current player name in case it changed
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
    guild_id = interaction.guild.id
    voice_will_speak = (guild_id in voice_clients and 
                       voice_clients[guild_id].is_connected() and 
                       tts_enabled.get(guild_id, False))
    
    if voice_will_speak:
        embed.add_field(name="🎤", value="*Donnie prepares his response...*", inline=False)
    elif guild_id in voice_clients and voice_clients[guild_id].is_connected():
        embed.add_field(name="🔇", value="*Donnie is muted*", inline=False)
    
    # Add character context footer
    episode_info = f"Level {char_data['level']} • {char_data['background']} • Player: {player_name}"
    if campaign_context.get("episode_active", False):
        episode_info += f" • Episode {campaign_context.get('current_episode', 0)}"
    embed.set_footer(text=episode_info)
    
    # Send the response IMMEDIATELY
    await interaction.response.send_message(embed=embed)
    message = await interaction.original_response()
    
    # Play thinking sound immediately if voice is enabled (fills the waiting gap)
    if voice_will_speak:
        asyncio.create_task(play_thinking_sound(guild_id, character_name))
    
    # Process Claude API call in background
    asyncio.create_task(process_dm_response_background(
        user_id, what_you_do, message, character_name, char_data, 
        player_name, guild_id, voice_will_speak
    ))

async def process_dm_response_background(user_id: str, player_input: str, message, 
                                       character_name: str, char_data: dict, 
                                       player_name: str, guild_id: int, voice_will_speak: bool):
    """Process DM response with automatic continuation support"""
    try:
        # Get Claude DM response
        dm_response = await get_claude_dm_response(user_id, player_input)
        
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
        print(f"Background processing error: {e}")
        # Update with error message
        try:
            embed = message.embeds[0]
            for i, field in enumerate(embed.fields):
                if field.name == "🐉 Donnie the DM":
                    embed.set_field_at(i, name="🐉 Donnie the DM", 
                                     value="*The DM pauses as otherworldly forces intervene...*", inline=False)
                    break
            await message.edit(embed=embed)
        except:
            pass

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
            value="Use `/character` to register your character, then `/start_episode` to begin with full episode management!",
            inline=False
        )
    elif not campaign_context.get("session_started", False) and not campaign_context.get("episode_active", False):
        embed.add_field(
            name="⚠️ Next Step", 
            value="Use `/start_episode` for full episode management or `/start` for simple session!",
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

# ====== HELP COMMAND ======

@bot.tree.command(name="help", description="Show comprehensive guide for the Storm King's Thunder TTS bot")
async def show_help(interaction: discord.Interaction):
    """Show comprehensive bot guide including TTS features and episode management"""
    embed = discord.Embed(
        title="⚡ Storm King's Thunder TTS Bot - Complete Guide",
        description="Your AI-powered D&D 5e adventure with Donnie the DM's optimized voice and episode management!",
        color=0x4169E1
    )
    
    embed.add_field(
        name="🎤 Voice Features (OPTIMIZED!)",
        value="`/join_voice` - Donnie joins voice with fast, optimized narration\n`/leave_voice` - Donnie leaves voice channel\n`/mute_donnie` - Disable TTS narration\n`/unmute_donnie` - Enable TTS narration\n`/donnie_speed <1.0-2.0>` - Adjust speaking speed",
        inline=False
    )
    
    embed.add_field(
        name="📺 Episode Management (NEW!)",
        value="`/start_episode [name]` - Begin new episode with recap\n`/end_episode [summary]` - End current episode\n`/episode_recap [#] [style]` - Get AI dramatic recaps\n`/episode_history` - View past episodes\n`/add_story_note` - Add player notes (non-canonical)",
        inline=False
    )
    
    embed.add_field(
        name="📈 Character Progression (NEW!)",
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
        value="`/set_scene` - Update current scene",
        inline=False
    )
    
    embed.add_field(
        name="🌟 New Episode System Features",
        value="• **Persistent Memory**: Episodes saved with character snapshots\n• **AI Dramatic Recaps**: \"Previously on Storm King's Thunder...\"\n• **Character Progression**: Level tracking across episodes\n• **Player Story Notes**: Add notes (marked non-canonical)\n• **Voice Integration**: Episode recaps spoken by Donnie\n• **Auto-Save**: Characters and progress automatically saved",
        inline=False
    )
    
    embed.set_footer(text="Donnie the DM awaits to guide your persistent, voice-enabled campaign adventure!")
    await interaction.response.send_message(embed=embed)

# Initialize Episode Management and Character Progression
episode_commands = EpisodeCommands(
    bot=bot,
    campaign_context=campaign_context,
    voice_clients=voice_clients,
    tts_enabled=tts_enabled,
    add_to_voice_queue_func=add_to_voice_queue
)

character_progression = CharacterProgressionCommands(
    bot=bot,
    campaign_context=campaign_context,
    voice_clients=voice_clients,
    tts_enabled=tts_enabled,
    add_to_voice_queue_func=add_to_voice_queue
)

if __name__ == "__main__":
    # Check for required dependencies
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
        print("⚠️  FFmpeg not found - required for voice features")
        print("Install FFmpeg: https://ffmpeg.org/download.html")
    
    # Get bot token with proper error handling
    bot_token = os.getenv('DISCORD_BOT_TOKEN')
    if not bot_token:
        print("❌ DISCORD_BOT_TOKEN environment variable not set!")
        exit(1)
    
    try:
        bot.run(bot_token)
    except KeyboardInterrupt:
        print("🛑 Bot shutdown requested")
    finally:
        close_database()
        print("✅ Cleanup completed")