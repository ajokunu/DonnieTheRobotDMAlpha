import discord
from discord.ext import commands
from discord import app_commands
import anthropic
import asyncio
import os
from dotenv import load_dotenv
import random
from typing import Optional

load_dotenv()

# Initialize APIs
claude_client = anthropic.Anthropic(api_key=os.getenv('ANTHROPIC_API_KEY'))

# Discord bot setup
intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix='/', intents=intents, help_command=None)

# Storm King's Thunder Campaign Context
campaign_context = {
    "campaign_name": "Storm King's Thunder",
    "setting": "The Sword Coast - Giants have begun raiding settlements across the land. The ancient ordning that kept giant society in check has collapsed, throwing giantkind into chaos.",
    "players": {},
    "characters": {},  # Store character information
    "current_scene": "The village of Nightstone sits eerily quiet. Giant-sized boulders litter the village square, and not a soul can be seen moving in the streets. The party approaches the mysteriously open gates...",
    "session_history": [],
    "session_started": False
}

# Storm King's Thunder DM Prompt
DM_PROMPT = """You are a Dungeon Master running Storm King's Thunder for D&D 5th Edition (2024 rules).

SETTING: {setting}
CURRENT SCENE: {current_scene}
RECENT HISTORY: {session_history}
PARTY CHARACTERS: {characters}
PLAYERS: {players}

You are running Storm King's Thunder - giants threaten the Sword Coast and the ordning has collapsed.

PARTY COMPOSITION: Use the character information provided to personalize your responses. Address characters by name and reference their classes, backgrounds, and details when appropriate.

DM GUIDELINES:
- You are fair but challenging - not too easy, not too harsh
- Giants should feel massive and threatening when encountered
- Use vivid descriptions of the Sword Coast setting
- Reference character abilities and backgrounds in your responses
- Ask for dice rolls when appropriate (D&D 5e 2024 rules)
- Keep responses 2-4 sentences for real-time play
- Make player choices matter and have consequences
- Create immersive roleplay opportunities
- Address characters by their names when possible

PLAYER ACTION: {player_input}

Respond as the Storm King's Thunder DM:"""

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
        
        dm_response = response.content[0].text.strip()
        
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
    print('🔄 Syncing slash commands...')
    try:
        synced = await bot.tree.sync()
        print(f'✅ Synced {len(synced)} slash commands')
        print("🎲 Storm King's Thunder bot ready for adventure!")
    except Exception as e:
        print(f'❌ Failed to sync commands: {e}')
        import traceback
        traceback.print_exc()

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return
    await bot.process_commands(message)

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
        value="Use `/party` to see all characters, `/character_sheet` for details, or `/start` to begin the adventure!",
        inline=False
    )
    
    embed.set_footer(text="Character bound to your Discord account!")
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
    
    embed.set_footer(text="Use /update_character to modify character details")
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
                await interaction.response.send_message("❌ Level must be between 1 and 20!", ephemeral=True)
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
    
    embed.set_footer(text="Use /character_sheet to view your full character details")
    await interaction.response.send_message(embed=embed)

# ====== CORE GAMEPLAY COMMANDS ======

@bot.tree.command(name="start", description="Begin your Storm King's Thunder adventure")
async def start_adventure(interaction: discord.Interaction):
    """Start the Storm King's Thunder campaign"""
    
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
        value="Use `/action <what you do>` to interact with the world. The AI DM will respond based on your character's capabilities and the unfolding story.",
        inline=False
    )
    
    embed.set_footer(text="What do you do in this moment of crisis?")
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="action", description="Take an action in the Storm King's Thunder campaign")
@app_commands.describe(what_you_do="Describe what your character does or says")
async def take_action(interaction: discord.Interaction, what_you_do: str):
    """Process player action and get DM response"""
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
    if not campaign_context.get("session_started", False):
        embed = discord.Embed(
            title="⚡ Adventure Not Started",
            description="Use `/start` to begin the Storm King's Thunder adventure first!",
            color=0xFF6B6B
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    
    # Get character data
    char_data = campaign_context["players"][user_id]["character_data"]
    character_name = char_data["name"]
    
    # Update current player name in case it changed
    campaign_context["players"][user_id]["player_name"] = player_name
    
    # Send initial response to avoid timeout
    await interaction.response.defer()
    
    # Get Claude DM response with character context
    dm_response = await get_claude_dm_response(user_id, what_you_do)
    
    # Create response embed with character name and class
    char_title = f"{character_name} ({char_data['race']} {char_data['class']})"
    
    embed = discord.Embed(color=0x2E8B57)
    embed.add_field(
        name=f"🎭 {char_title}",
        value=what_you_do,
        inline=False
    )
    embed.add_field(
        name="🐉 Dungeon Master",
        value=dm_response,
        inline=False
    )
    
    # Add character context footer
    embed.set_footer(text=f"Level {char_data['level']} • {char_data['background']} • Player: {player_name}")
    
    await interaction.followup.send(embed=embed)

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
    
    embed.add_field(
        name="📜 Session Progress",
        value=f"{len(campaign_context['session_history'])} interactions",
        inline=True
    )
    
    embed.add_field(
        name="🎮 Session Status",
        value="✅ Active" if campaign_context.get("session_started", False) else "⏸️ Not Started",
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
            value="Use `/character` to register your character, then `/start` to begin!",
            inline=False
        )
    elif not campaign_context.get("session_started", False):
        embed.add_field(
            name="⚠️ Next Step", 
            value="Use `/start` to begin your adventure!",
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

@bot.tree.command(name="giants", description="Learn about the different types of giants threatening the Sword Coast")
async def giants_info(interaction: discord.Interaction):
    """Show giant types and threats"""
    embed = discord.Embed(
        title="🏔️ Giant Types - Know Your Enemies",
        description="The collapsed ordning has unleashed chaos among giantkind",
        color=0x8B4513
    )
    
    embed.add_field(
        name="⛰️ Hill Giants",
        value="Crude and gluttonous raiders who attack settlements for food and shiny objects",
        inline=False
    )
    
    embed.add_field(
        name="🗻 Stone Giants", 
        value="Artistic but increasingly violent when their underground domains are disturbed",
        inline=False
    )
    
    embed.add_field(
        name="🧊 Frost Giants",
        value="Militaristic raiders from the northern mountains, believing in conquest through strength",
        inline=False
    )
    
    embed.add_field(
        name="🔥 Fire Giants",
        value="Master crafters seeking ancient relics and weapons in their mountain forges",
        inline=False
    )
    
    embed.add_field(
        name="☁️ Cloud Giants",
        value="Arrogant nobility who rain destruction from their flying castles",
        inline=False
    )
    
    embed.add_field(
        name="⚡ Storm Giants",
        value="The mysterious rulers of the ordning, now in disarray with their king missing",
        inline=False
    )
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="ordning", description="Learn about the giant social hierarchy system")
async def explain_ordning(interaction: discord.Interaction):
    """Explain the giant ordning system"""
    embed = discord.Embed(
        title="⚡ The Ordning - Giant Social Hierarchy",
        description="The ancient system that maintained order among giantkind",
        color=0x4169E1
    )
    
    embed.add_field(
        name="1. Storm Giants (Highest)",
        value="Rulers of all giants, masters of sea and sky. King Hekaton has mysteriously disappeared.",
        inline=False
    )
    embed.add_field(
        name="2. Cloud Giants", 
        value="Arrogant nobility who live in sky castles and consider themselves superior to all.",
        inline=False
    )
    embed.add_field(
        name="3. Fire Giants",
        value="Master smiths and crafters, militaristic and disciplined in their mountain forges.",
        inline=False
    )
    embed.add_field(
        name="4. Frost Giants",
        value="Savage raiders from the north, believing in strength through conquest.",
        inline=False
    )
    embed.add_field(
        name="5. Stone Giants",
        value="Artistic and reclusive, they prefer their underground domains to the surface world.",
        inline=False
    )
    embed.add_field(
        name="6. Hill Giants (Lowest)",
        value="Crude and gluttonous, they raid for food and shiny objects without strategy.",
        inline=False
    )
    
    embed.set_footer(text="With the ordning broken, giants fight each other and terrorize small folk")
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

@bot.tree.command(name="lore", description="Learn about Storm King's Thunder campaign background")
async def campaign_lore(interaction: discord.Interaction):
    """Show campaign background and lore"""
    embed = discord.Embed(
        title="📚 Storm King's Thunder - Campaign Lore",
        description="The ancient order has collapsed, and giants roam free",
        color=0x191970
    )
    
    embed.add_field(
        name="⚡ The Ordning",
        value="An ancient hierarchy that kept giant society ordered: Storm > Cloud > Fire > Frost > Stone > Hill. Its collapse has thrown giantkind into chaos.",
        inline=False
    )
    
    embed.add_field(
        name="🗺️ The Sword Coast",
        value="A region of city-states and frontier settlements along Faerûn's western coast. Trade routes and communities now live in fear of giant raids.",
        inline=False
    )
    
    embed.add_field(
        name="👑 The Missing King",
        value="King Hekaton, ruler of the storm giants and the ordning itself, has mysteriously vanished, leaving giantkind without leadership.",
        inline=False
    )
    
    embed.add_field(
        name="🎯 Your Mission",
        value="As heroes, you must uncover the truth behind the giant crisis and find a way to restore order before the small folk are destroyed.",
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
    
    embed.set_footer(text="Use /giants, /ordning, and /locations for more detailed information")
    await interaction.response.send_message(embed=embed)

# ====== ADMIN COMMANDS ======

@bot.tree.command(name="set_scene", description="Update the current scene (Admin only)")
@app_commands.describe(scene_description="The new scene description")
async def set_scene(interaction: discord.Interaction, scene_description: str):
    """Update current scene (Admin only)"""
    if interaction.user.guild_permissions.administrator:
        campaign_context["current_scene"] = scene_description
        embed = discord.Embed(
            title="🏛️ Scene Updated",
            description=scene_description,
            color=0x4169E1
        )
        await interaction.response.send_message(embed=embed)
    else:
        await interaction.response.send_message("❌ Only server administrators can update scenes!", ephemeral=True)

@bot.tree.command(name="threat", description="Introduce a specific giant threat (Admin only)")
@app_commands.describe(
    giant_type="Type of giant threat",
    threat_description="Description of the threat"
)
@app_commands.choices(giant_type=[
    app_commands.Choice(name="Hill Giant", value="hill"),
    app_commands.Choice(name="Stone Giant", value="stone"),
    app_commands.Choice(name="Frost Giant", value="frost"),
    app_commands.Choice(name="Fire Giant", value="fire"),
    app_commands.Choice(name="Cloud Giant", value="cloud"),
    app_commands.Choice(name="Storm Giant", value="storm")
])
async def introduce_giant_threat(interaction: discord.Interaction, giant_type: str, threat_description: str):
    """Introduce a specific giant threat (Admin only)"""
    if interaction.user.guild_permissions.administrator:
        embed = discord.Embed(
            title=f"⚡ {giant_type.title()} Giant Threat!",
            description=threat_description,
            color=0xFF4500
        )
        embed.set_footer(text="The giant crisis escalates...")
        await interaction.response.send_message(embed=embed)
        
        # Update scene to reflect the threat
        campaign_context["current_scene"] = f"GIANT THREAT: {threat_description}"
    else:
        await interaction.response.send_message("❌ Only administrators can introduce giant threats!", ephemeral=True)

# ====== HELP COMMAND ======

@bot.tree.command(name="help", description="Show comprehensive guide for the Storm King's Thunder bot")
async def show_help(interaction: discord.Interaction):
    """Show comprehensive bot guide"""
    embed = discord.Embed(
        title="⚡ Storm King's Thunder DM Bot - Complete Guide",
        description="Your AI-powered D&D 5e adventure through the giant crisis!",
        color=0x4169E1
    )
    
    embed.add_field(
        name="🎭 Character Management",
        value="`/character` - Register detailed character\n`/party` - View all party members\n`/character_sheet` - View character details\n`/update_character` - Modify character aspects",
        inline=False
    )
    
    embed.add_field(
        name="🎮 Core Gameplay",
        value="`/start` - Begin Storm King's Thunder\n`/action <what_you_do>` - Take actions (AI DM responds)\n`/roll <dice>` - Roll dice (1d20+3, 3d6, etc.)\n`/status` - Show campaign status",
        inline=False
    )
    
    embed.add_field(
        name="📚 World Information",
        value="`/scene` - View current scene\n`/giants` - Learn about giant types\n`/ordning` - Giant hierarchy system\n`/locations` - Sword Coast locations\n`/lore` - Campaign background\n`/campaign` - Full campaign info",
        inline=False
    )
    
    embed.add_field(
        name="⚙️ Admin Commands",
        value="`/set_scene` - Update current scene\n`/threat` - Introduce giant threats",
        inline=False
    )
    
    embed.add_field(
        name="🚀 Getting Started",
        value="1. Use `/character` to register your hero\n2. Use `/start` to begin the adventure\n3. Use `/action` to interact with the world\n4. The AI DM will respond based on your character!",
        inline=False
    )
    
    embed.set_footer(text="The giant crisis awaits your heroes! Ready to face the Storm King's Thunder?")
    await interaction.response.send_message(embed=embed)

if __name__ == "__main__":
    bot.run(os.getenv('DISCORD_BOT_TOKEN'))