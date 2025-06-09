import discord
from discord.ext import commands
from discord import app_commands
import asyncio
import json
import time
from typing import Dict, Any, Optional
import re

# Enhanced import checking with detailed error reporting
print("🔍 PDF Character Parser: Checking dependencies...")

PDF_AVAILABLE = False
IMPORT_ERRORS = []

try:
    import PyPDF2
    print(f"✅ PyPDF2 imported (version: {PyPDF2.__version__})")
except ImportError as e:
    IMPORT_ERRORS.append(f"PyPDF2: {e}")
    print(f"❌ PyPDF2 import failed: {e}")

try:
    import fitz  # PyMuPDF
    print(f"✅ PyMuPDF imported (version: {fitz.version})")
except ImportError as e:
    IMPORT_ERRORS.append(f"PyMuPDF: {e}")
    print(f"❌ PyMuPDF import failed: {e}")

try:
    from PIL import Image
    print(f"✅ Pillow imported")
except ImportError as e:
    IMPORT_ERRORS.append(f"Pillow: {e}")
    print(f"❌ Pillow import failed: {e}")

try:
    import io
    print(f"✅ io module imported")
except ImportError as e:
    IMPORT_ERRORS.append(f"io: {e}")
    print(f"❌ io import failed: {e}")

# Only set PDF_AVAILABLE to True if ALL imports succeeded
if not IMPORT_ERRORS:
    PDF_AVAILABLE = True
    print("✅ All PDF dependencies available - PDF features ENABLED")
else:
    PDF_AVAILABLE = False
    print(f"❌ PDF features DISABLED due to import errors: {IMPORT_ERRORS}")

class PDFCharacterCommands:
    def __init__(self, bot, campaign_context, claude_client):
        print(f"🔄 PDFCharacterCommands initializing... PDF_AVAILABLE: {PDF_AVAILABLE}")
        
        self.bot = bot
        self.campaign_context = campaign_context
        self.claude_client = claude_client
        self.pending_confirmations = {}  # Store pending character confirmations
        
        # Register the commands with enhanced error checking
        if PDF_AVAILABLE:
            print("📋 PDF processing available - registering commands...")
            try:
                self._register_commands()
                print("✅ PDF commands registered successfully!")
            except Exception as e:
                print(f"❌ Failed to register PDF commands: {e}")
                import traceback
                traceback.print_exc()
        else:
            print("⚠️ PDF processing not available - commands not registered")
            print(f"   Reason: {IMPORT_ERRORS}")
    
    def _register_commands(self):
        """Register PDF-related commands with enhanced error handling"""
        print("🔄 Registering upload_character_sheet command...")
        
        @self.bot.tree.command(name="upload_character_sheet", description="Upload a PDF character sheet for automatic parsing")
        @app_commands.describe(
            character_sheet="Your D&D character sheet PDF file (max 10MB)",
            replace_existing="Replace existing character if you have one registered (default: False)"
        )
        async def upload_character_sheet(interaction: discord.Interaction, 
                                       character_sheet: discord.Attachment, 
                                       replace_existing: bool = False):
            """Upload and parse PDF character sheet with FULL registration integration"""
            print(f"📄 Character sheet upload triggered by {interaction.user.display_name}")
            await self._handle_character_sheet_upload(interaction, character_sheet, replace_existing)
        
        print("🔄 Registering character_sheet_help command...")
        
        @self.bot.tree.command(name="character_sheet_help", description="Get help with uploading character sheets")
        async def character_sheet_help(interaction: discord.Interaction):
            """Show help for character sheet uploads"""
            print(f"❓ Character sheet help requested by {interaction.user.display_name}")
            await self._show_upload_help(interaction)
        
        print("✅ Both PDF commands registered with bot.tree")
    
    async def _register_parsed_character(self, interaction: discord.Interaction, character_data: Dict):
        """Register the parsed character into the main campaign system"""
        
        user_id = str(interaction.user.id)
        player_name = interaction.user.display_name
        
        print(f"🔄 Registering parsed character for {player_name} (ID: {user_id})")
        
        # Build comprehensive character profile (same format as manual /character command)
        character_profile = {
            "name": character_data.get("name", "Unknown"),
            "race": character_data.get("race", "Unknown"),
            "class": character_data.get("class", "Unknown"), 
            "level": character_data.get("level", 1),
            "background": character_data.get("background", "Unknown"),
            "stats": self._format_ability_scores(character_data.get("ability_scores", {})),
            "equipment": self._format_equipment(character_data.get("equipment", {})),
            "spells": self._format_spells(character_data.get("spellcasting", {})),
            "affiliations": self._format_affiliations(character_data.get("affiliations", {})),
            "personality": self._format_personality(character_data.get("personality", {})),
            "player_name": player_name,
            "discord_user_id": user_id,
            "full_character_data": character_data  # Store the complete parsed data
        }
        
        # Create formatted character description for Claude (same as manual registration)
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
        
        # ✅ CRITICAL: Store in the same dictionaries that episode system checks
        self.campaign_context["characters"][user_id] = character_description
        self.campaign_context["players"][user_id] = {
            "user_id": user_id,
            "player_name": player_name,
            "character_data": character_profile,
            "character_description": character_description
        }
        
        print(f"✅ PDF character {character_profile['name']} registered for {player_name}")
        
        # Set guild_id in campaign context if not set
        if self.campaign_context.get("guild_id") is None:
            guild_id_str = str(interaction.guild.id)
            self.campaign_context["guild_id"] = guild_id_str
            print(f"✅ Set guild_id in campaign_context: {guild_id_str}")
    
    def _format_ability_scores(self, ability_scores: Dict) -> str:
        """Format ability scores for character description"""
        if not ability_scores:
            return "From PDF"
        
        try:
            formatted = []
            for ability, score in ability_scores.items():
                if isinstance(score, int):
                    formatted.append(f"{ability.upper()}: {score}")
            return ", ".join(formatted) if formatted else "From PDF"
        except:
            return "From PDF"
    
    def _format_equipment(self, equipment: Dict) -> str:
        """Format equipment for character description"""
        if not equipment:
            return "From PDF"
        
        try:
            items = []
            for category, item_list in equipment.items():
                if isinstance(item_list, list) and item_list:
                    items.extend(item_list[:3])  # Limit to first 3 items per category
            
            if items:
                return ", ".join(items[:5]) + ("..." if len(items) > 5 else "")
            return "From PDF"
        except:
            return "From PDF"
    
    def _format_spells(self, spellcasting: Dict) -> str:
        """Format spells for character description"""
        if not spellcasting or not spellcasting.get("spellcasting_class"):
            return "None"
        
        try:
            spells = []
            cantrips = spellcasting.get("cantrips", [])
            if cantrips:
                spells.extend(cantrips[:3])
            
            spells_known = spellcasting.get("spells_known", {})
            for level, spell_list in spells_known.items():
                if isinstance(spell_list, list) and spell_list:
                    spells.extend(spell_list[:2])  # Limit to 2 per level
                    if len(spells) >= 5:  # Don't overwhelm the description
                        break
            
            if spells:
                return ", ".join(spells[:5]) + ("..." if len(spells) > 5 else "")
            return f"{spellcasting.get('spellcasting_class')} Spellcaster"
        except:
            return "From PDF"
    
    def _format_affiliations(self, affiliations: Dict) -> str:
        """Format affiliations for character description"""
        if not affiliations:
            return "None"
        
        try:
            all_affiliations = []
            for category, affiliation_list in affiliations.items():
                if isinstance(affiliation_list, list) and affiliation_list:
                    all_affiliations.extend(affiliation_list[:2])  # Limit per category
            
            if all_affiliations:
                return ", ".join(all_affiliations[:3])
            return "None"
        except:
            return "None"
    
    def _format_personality(self, personality: Dict) -> str:
        """Format personality for character description"""
        if not personality:
            return "From PDF"
        
        try:
            traits = []
            
            # Add personality traits
            if personality.get("personality_traits"):
                traits.extend(personality["personality_traits"][:2])
            
            # Add ideals
            if personality.get("ideals"):
                traits.extend(personality["ideals"][:1])
            
            # Add bonds
            if personality.get("bonds"):
                traits.extend(personality["bonds"][:1])
            
            if traits:
                return "; ".join(traits[:3])
            
            # Fallback to backstory if available
            if personality.get("backstory"):
                backstory = personality["backstory"][:100]
                return backstory + ("..." if len(personality["backstory"]) > 100 else "")
            
            return "From PDF"
        except:
            return "From PDF"
    
    async def _handle_character_sheet_upload(self, interaction: discord.Interaction, 
                                           attachment: discord.Attachment, replace_existing: bool):
        """Handle character sheet PDF upload and parsing"""
        user_id = str(interaction.user.id)
        player_name = interaction.user.display_name
        
        print(f"🔄 Processing character sheet upload for {player_name} (ID: {user_id})")
        
        # Check if user already has a character and replace_existing is False
        if user_id in self.campaign_context["characters"] and not replace_existing:
            embed = discord.Embed(
                title="⚠️ Character Already Registered",
                description=f"You already have a character registered. Use `replace_existing: True` to replace it, or use `/update_character` to modify specific aspects.",
                color=0xFFD700
            )
            embed.add_field(
                name="Current Character",
                value=f"**{self.campaign_context['players'][user_id]['character_data']['name']}**",
                inline=False
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        # Validate file type and size
        if not attachment.filename.lower().endswith('.pdf'):
            await interaction.response.send_message("❌ Please upload a PDF file only!", ephemeral=True)
            return
        
        if attachment.size > 10_000_000:  # 10MB limit
            await interaction.response.send_message("❌ File too large! Maximum size is 10MB.", ephemeral=True)
            return
        
        # Send initial processing message
        embed = discord.Embed(
            title="📄 Processing Character Sheet...",
            description="Donnie is carefully reading through your character sheet...",
            color=0x1E90FF
        )
        embed.add_field(
            name="📋 File Info",
            value=f"**File:** {attachment.filename}\n**Size:** {attachment.size / 1024:.1f} KB",
            inline=False
        )
        embed.add_field(
            name="⏳ Status",
            value="🔍 Extracting text from PDF...",
            inline=False
        )
        
        await interaction.response.send_message(embed=embed)
        
        try:
            print(f"📄 Extracting text from {attachment.filename}...")
            # Extract text from PDF
            pdf_text = await self._extract_pdf_text(attachment)
            
            if not pdf_text or len(pdf_text.strip()) < 50:
                raise ValueError("Could not extract sufficient text from PDF")
            
            print(f"✅ Extracted {len(pdf_text)} characters from PDF")
            
            # Update status
            embed.set_field_at(1, name="⏳ Status", value="🤖 AI analyzing character sheet...", inline=False)
            await interaction.edit_original_response(embed=embed)
            
            # Parse with Claude AI (with retry logic)
            character_data = await self._parse_character_sheet_with_ai_retry(pdf_text, player_name, user_id, interaction, embed)
            
            if not character_data:
                # Show error with manual option
                await self._show_parsing_error(interaction, pdf_text)
                return
            
            print(f"✅ Successfully parsed character: {character_data.get('name', 'Unknown')}")
            
            # Update status
            embed.set_field_at(1, name="⏳ Status", value="✅ Parsing complete! Registering character...", inline=False)
            await interaction.edit_original_response(embed=embed)
            
            # ✅ NEW: Register the character into main system
            await self._register_parsed_character(interaction, character_data)
            
            # Show success with full integration
            await self._show_registration_success(interaction, character_data, player_name)
            
        except Exception as e:
            print(f"❌ Character sheet upload error: {e}")
            import traceback
            traceback.print_exc()
            await self._show_upload_error(interaction, str(e))
    
    async def _show_registration_success(self, interaction: discord.Interaction, character_data: Dict, player_name: str):
        """Show successful registration with campaign integration"""
        embed = discord.Embed(
            title="✅ Character Registered Successfully!",
            description=f"**{character_data['name']}** has been parsed and registered!",
            color=0x32CD32
        )
        
        embed.add_field(
            name=f"⚔️ {character_data['name']}",
            value=f"**{character_data.get('race', 'Unknown')} {character_data.get('class', 'Unknown')}** (Level {character_data.get('level', 1)})\n*Player: {player_name}*",
            inline=False
        )
        
        embed.add_field(
            name="✅ Ready for Adventure",
            value="Use `/start_episode` to begin your next adventure!\nUse `/party` to see all registered characters!",
            inline=False
        )
        
        # Show what was extracted
        if character_data.get('background'):
            embed.add_field(name="📚 Background", value=character_data['background'], inline=True)
        
        if character_data.get('equipment'):
            equipment_text = self._format_equipment(character_data['equipment'])
            if equipment_text != "From PDF":
                embed.add_field(name="⚔️ Equipment", value=equipment_text, inline=True)
        
        if character_data.get('spellcasting') and character_data['spellcasting'].get('spellcasting_class'):
            spells_text = self._format_spells(character_data['spellcasting'])
            if spells_text not in ["None", "From PDF"]:
                embed.add_field(name="✨ Spells", value=spells_text, inline=True)
        
        # Update the original message with success
        await interaction.edit_original_response(content=None, embed=embed)
        
        print(f"✅ PDF character {character_data['name']} fully integrated into campaign")
    
    async def _extract_pdf_text(self, attachment: discord.Attachment) -> str:
        """Extract text from PDF using PyPDF2 and PyMuPDF as fallback"""
        print("🔄 Starting PDF text extraction...")
        pdf_content = await attachment.read()
        print(f"📄 Read {len(pdf_content)} bytes from PDF")
        
        # Try PyMuPDF first (usually better at text extraction)
        try:
            print("🔄 Trying PyMuPDF extraction...")
            doc = fitz.open(stream=pdf_content, filetype="pdf")
            text_parts = []
            
            for page_num in range(len(doc)):
                page = doc.load_page(page_num)
                text = page.get_text()
                if text.strip():  # Only add non-empty pages
                    text_parts.append(f"--- Page {page_num + 1} ---\n{text}")
                    print(f"📄 Page {page_num + 1}: {len(text)} characters")
            
            doc.close()
            full_text = "\n\n".join(text_parts)
            
            if full_text.strip():
                print(f"✅ PyMuPDF extraction successful: {len(full_text)} characters")
                return full_text
        
        except Exception as e:
            print(f"❌ PyMuPDF extraction failed: {e}")
        
        # Fallback to PyPDF2
        try:
            print("🔄 Trying PyPDF2 extraction...")
            pdf_reader = PyPDF2.PdfReader(io.BytesIO(pdf_content))
            text_parts = []
            
            for page_num, page in enumerate(pdf_reader.pages):
                text = page.extract_text()
                if text.strip():  # Only add non-empty pages
                    text_parts.append(f"--- Page {page_num + 1} ---\n{text}")
                    print(f"📄 Page {page_num + 1}: {len(text)} characters")
            
            full_text = "\n\n".join(text_parts)
            print(f"✅ PyPDF2 extraction successful: {len(full_text)} characters")
            return full_text
        
        except Exception as e:
            print(f"❌ PyPDF2 extraction failed: {e}")
            raise ValueError("Could not extract text from PDF using any method")
    
    async def _parse_character_sheet_with_ai_retry(self, pdf_text: str, player_name: str, user_id: str, interaction, embed) -> Optional[Dict[str, Any]]:
        """Parse character sheet with retry logic for API errors"""
        max_retries = 3
        base_delay = 2
        
        for attempt in range(max_retries):
            try:
                print(f"🤖 AI parsing attempt {attempt + 1}/{max_retries}")
                
                # Update status with attempt info
                if attempt > 0:
                    embed.set_field_at(1, name="⏳ Status", value=f"🤖 AI analyzing... (Attempt {attempt + 1}/{max_retries})", inline=False)
                    await interaction.edit_original_response(embed=embed)
                
                character_data = await self._parse_character_sheet_with_ai(pdf_text, player_name, user_id)
                
                if character_data:
                    print(f"✅ AI parsing successful on attempt {attempt + 1}")
                    return character_data
                    
            except Exception as e:
                error_msg = str(e)
                print(f"❌ Claude API attempt {attempt + 1} failed: {error_msg}")
                
                # Check if it's an API overload error
                if "overloaded" in error_msg.lower() or "529" in error_msg:
                    if attempt < max_retries - 1:
                        delay = base_delay * (2 ** attempt)  # Exponential backoff
                        print(f"⏳ Waiting {delay}s before retry...")
                        embed.set_field_at(1, name="⏳ Status", value=f"⏳ Claude AI is busy, retrying in {delay}s... ({attempt + 1}/{max_retries})", inline=False)
                        await interaction.edit_original_response(embed=embed)
                        await asyncio.sleep(delay)
                        continue
                    else:
                        # Final attempt failed
                        embed.set_field_at(1, name="⏳ Status", value="❌ Claude AI is overloaded. Please try again later.", inline=False)
                        await interaction.edit_original_response(embed=embed)
                        return None
                else:
                    # Other error, don't retry
                    print(f"❌ Non-retryable error: {error_msg}")
                    return None
        
        return None
    
    async def _parse_character_sheet_with_ai(self, pdf_text: str, player_name: str, user_id: str) -> Optional[Dict[str, Any]]:
        """Parse character sheet text using Claude AI with robust error handling"""
        
        # Truncate very long PDFs to avoid token limits
        if len(pdf_text) > 15000:  # Roughly 15k characters
            pdf_text = pdf_text[:15000] + "\n\n[Content truncated for processing...]"
        
        parsing_prompt = f"""You are analyzing a D&D 5th Edition character sheet. Extract ALL character information and return it as a valid JSON object.

CHARACTER SHEET TEXT:
{pdf_text}

PLAYER INFO:
- Player Name: {player_name}
- Discord ID: {user_id}

REQUIRED: Return ONLY a valid JSON object with this exact structure. If information is missing from the sheet, use reasonable defaults:

{{
    "name": "Character Name",
    "race": "Character Race (including subrace if any)",
    "class": "Character Class and Subclass",
    "level": 1,
    "background": "Character Background",
    "alignment": "Character Alignment",
    "experience_points": 0,
    "ability_scores": {{
        "strength": 10,
        "dexterity": 10,
        "constitution": 10,
        "intelligence": 10,
        "wisdom": 10,
        "charisma": 10
    }},
    "ability_modifiers": {{
        "strength": "+0",
        "dexterity": "+0",
        "constitution": "+0",
        "intelligence": "+0",
        "wisdom": "+0",
        "charisma": "+0"
    }},
    "combat_stats": {{
        "armor_class": 10,
        "initiative": "+0",
        "speed": "30 ft",
        "hit_point_maximum": 8,
        "current_hit_points": 8,
        "temporary_hit_points": 0,
        "hit_dice": "1d8",
        "death_saves_successes": 0,
        "death_saves_failures": 0
    }},
    "proficiencies": {{
        "proficiency_bonus": "+2",
        "saving_throws": [],
        "skills": [],
        "languages": [],
        "tools": [],
        "weapons_armor": []
    }},
    "equipment": {{
        "weapons": [],
        "armor": [],
        "items": [],
        "treasure": []
    }},
    "spellcasting": {{
        "spellcasting_class": null,
        "spellcasting_ability": null,
        "spell_save_dc": 8,
        "spell_attack_bonus": "+0",
        "spell_slots": {{
            "level_1": {{"total": 0, "expended": 0}},
            "level_2": {{"total": 0, "expended": 0}},
            "level_3": {{"total": 0, "expended": 0}},
            "level_4": {{"total": 0, "expended": 0}},
            "level_5": {{"total": 0, "expended": 0}},
            "level_6": {{"total": 0, "expended": 0}},
            "level_7": {{"total": 0, "expended": 0}},
            "level_8": {{"total": 0, "expended": 0}},
            "level_9": {{"total": 0, "expended": 0}}
        }},
        "cantrips": [],
        "spells_known": {{
            "level_1": [],
            "level_2": [],
            "level_3": [],
            "level_4": [],
            "level_5": [],
            "level_6": [],
            "level_7": [],
            "level_8": [],
            "level_9": []
        }}
    }},
    "features_and_traits": {{
        "racial_traits": [],
        "class_features": [],
        "background_features": [],
        "feats": [],
        "other_features": []
    }},
    "personality": {{
        "personality_traits": [],
        "ideals": [],
        "bonds": [],
        "flaws": [],
        "backstory": ""
    }},
    "affiliations": {{
        "organizations": [],
        "allies": [],
        "enemies": [],
        "other_relationships": []
    }},
    "physical_description": {{
        "age": "",
        "height": "",
        "weight": "",
        "eyes": "",
        "skin": "",
        "hair": "",
        "appearance": ""
    }},
    "additional_notes": ""
}}

CRITICAL: 
- Return ONLY the JSON object, no other text
- Extract actual values from the character sheet text
- If information is missing, use the defaults shown above
- Ensure all numbers are actual numbers, not strings
- Level must be between 1-20
- If character is not a spellcaster, leave spellcasting fields as null/empty
"""
        
        try:
            print("🤖 Sending character sheet to Claude AI for parsing...")
            
            # Use Claude to parse the character sheet
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self.claude_client.messages.create(
                    model="claude-sonnet-4-20250514",
                    max_tokens=4000,
                    messages=[{
                        "role": "user",
                        "content": parsing_prompt
                    }]
                )
            )
            
            # Extract response text
            if hasattr(response.content[0], 'text'):
                response_text = response.content[0].text.strip()
            else:
                response_text = str(response.content[0]).strip()
            
            print(f"🤖 Claude response received: {len(response_text)} characters")
            
            # Try to extract JSON from the response
            json_start = response_text.find('{')
            json_end = response_text.rfind('}') + 1
            
            if json_start == -1 or json_end == 0:
                print("❌ No JSON found in Claude response")
                return None
            
            json_text = response_text[json_start:json_end]
            
            # Parse JSON
            try:
                character_data = json.loads(json_text)
                
                # Validate required fields
                required_fields = ['name', 'race', 'class', 'level']
                for field in required_fields:
                    if field not in character_data or not character_data[field]:
                        print(f"❌ Missing required field: {field}")
                        return None
                
                # Validate level
                if not isinstance(character_data['level'], int) or character_data['level'] < 1 or character_data['level'] > 20:
                    print(f"⚠️ Invalid level: {character_data['level']}, defaulting to 1")
                    character_data['level'] = 1  # Default to 1
                
                print(f"✅ Successfully parsed character: {character_data['name']}")
                return character_data
                
            except json.JSONDecodeError as e:
                print(f"❌ JSON parse error: {e}")
                print(f"JSON text preview: {json_text[:500]}...")
                return None
        
        except Exception as e:
            print(f"❌ Claude parsing error: {e}")
            # Re-raise the exception so retry logic can handle it
            raise e
    
    async def _show_parsing_error(self, interaction, pdf_text):
        """Show parsing error with manual entry option"""
        embed = discord.Embed(
            title="⚠️ AI Parsing Temporarily Unavailable",
            description="Claude AI is currently overloaded and can't parse your character sheet right now.",
            color=0xFFD700
        )
        embed.add_field(
            name="🔄 What You Can Do",
            value="1. **Try Again Later**: The AI service should be back to normal soon\n"
                  "2. **Manual Entry**: Use `/character` to register manually\n"
                  "3. **Wait & Retry**: Come back in a few minutes and try uploading again",
            inline=False
        )
        embed.add_field(
            name="📝 Alternative",
            value="Use `/character` to manually register your character with full details.",
            inline=False
        )
        await interaction.edit_original_response(embed=embed)
    
    async def _show_upload_error(self, interaction, error_msg):
        """Show upload error with helpful information"""
        embed = discord.Embed(
            title="❌ Character Sheet Upload Failed",
            description="There was an issue processing your character sheet.",
            color=0xFF6B6B
        )
        embed.add_field(
            name="🔧 Error Details",
            value=f"```{error_msg}```",
            inline=False
        )
        embed.add_field(
            name="📝 Alternative",
            value="Use `/character` to manually register your character.",
            inline=False
        )
        await interaction.edit_original_response(embed=embed)
    
    async def _show_upload_help(self, interaction):
        """Show help information for character sheet uploads"""
        embed = discord.Embed(
            title="📄 Character Sheet Upload Help",
            description="Learn how to upload and use PDF character sheets with Donnie!",
            color=0x4169E1
        )
        
        embed.add_field(
            name="📋 System Status",
            value=f"**PDF Processing:** {'✅ Available' if PDF_AVAILABLE else '❌ Unavailable'}\n**Import Errors:** {IMPORT_ERRORS if IMPORT_ERRORS else 'None'}",
            inline=False
        )
        
        embed.add_field(
            name="📋 Supported Formats",
            value="• **PDF files only** (max 10MB)\n• Standard D&D 5e character sheets\n• Most online character sheet generators\n• Hand-filled sheets (if clearly readable)",
            inline=False
        )
        
        embed.add_field(
            name="🔄 How It Works",
            value="1. Upload your PDF character sheet\n2. Donnie extracts text from the PDF\n3. Claude AI analyzes and parses character data\n4. Character is automatically registered for campaigns\n5. Ready to use with `/start_episode` and `/party`!",
            inline=False
        )
        
        embed.add_field(
            name="⚠️ Troubleshooting",
            value="• **Parsing fails?** Try a different PDF format or use `/character` for manual entry\n• **AI overloaded?** Wait a few minutes and try again\n• **Missing data?** The AI extracts what it can find - you can update with `/update_character`",
            inline=False
        )
        
        embed.add_field(
            name="🎯 Best Results",
            value="• Use standard D&D 5e character sheet formats\n• Ensure text is clearly readable\n• Avoid heavily stylized or custom layouts\n• Include all character information on the sheet",
            inline=False
        )
        
        await interaction.response.send_message(embed=embed)