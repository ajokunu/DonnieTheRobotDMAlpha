import discord
from discord.ext import commands
from discord import app_commands
import asyncio
import json
import time
from typing import Dict, Any, Optional
import re

try:
    import PyPDF2
    import fitz  # PyMuPDF
    from PIL import Image
    import io
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False

class PDFCharacterCommands:
    def __init__(self, bot, campaign_context, claude_client):
        self.bot = bot
        self.campaign_context = campaign_context
        self.claude_client = claude_client
        self.pending_confirmations = {}  # Store pending character confirmations
        
        # Register the commands
        if PDF_AVAILABLE:
            self._register_commands()
        else:
            print("⚠️  PDF processing not available - install PyPDF2, pymupdf, and pillow")
    
    def _register_commands(self):
        """Register PDF-related commands"""
        
        @self.bot.tree.command(name="upload_character_sheet", description="Upload a PDF character sheet for automatic parsing")
        @app_commands.describe(
            character_sheet="Your D&D character sheet PDF file (max 10MB)",
            replace_existing="Replace existing character if you have one registered (default: False)"
        )
        async def upload_character_sheet(interaction: discord.Interaction, 
                                       character_sheet: discord.Attachment, 
                                       replace_existing: bool = False):
            """Upload and parse a PDF character sheet"""
            await self._handle_character_sheet_upload(interaction, character_sheet, replace_existing)
        
        @self.bot.tree.command(name="character_sheet_help", description="Get help with uploading character sheets")
        async def character_sheet_help(interaction: discord.Interaction):
            """Show help for character sheet uploads"""
            await self._show_upload_help(interaction)
    
    async def _handle_character_sheet_upload(self, interaction: discord.Interaction, 
                                           attachment: discord.Attachment, replace_existing: bool):
        """Handle character sheet PDF upload and parsing"""
        user_id = str(interaction.user.id)
        player_name = interaction.user.display_name
        
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
            # Extract text from PDF
            pdf_text = await self._extract_pdf_text(attachment)
            
            if not pdf_text or len(pdf_text.strip()) < 50:
                raise ValueError("Could not extract sufficient text from PDF")
            
            # Update status
            embed.set_field_at(1, name="⏳ Status", value="🤖 AI analyzing character sheet...", inline=False)
            await interaction.edit_original_response(embed=embed)
            
            # Parse with Claude AI (with retry logic)
            character_data = await self._parse_character_sheet_with_ai_retry(pdf_text, player_name, user_id, interaction, embed)
            
            if not character_data:
                # Show error with manual option
                await self._show_parsing_error(interaction, pdf_text)
                return
            
            # Update status
            embed.set_field_at(1, name="⏳ Status", value="✅ Parsing complete! Please confirm...", inline=False)
            await interaction.edit_original_response(embed=embed)
            
            # Show confirmation
            await self._show_confirmation(interaction, character_data, user_id, player_name)
            
        except Exception as e:
            print(f"Character sheet upload error: {e}")
            await self._show_upload_error(interaction, str(e))
    
    async def _parse_character_sheet_with_ai_retry(self, pdf_text: str, player_name: str, user_id: str, interaction, embed) -> Optional[Dict[str, Any]]:
        """Parse character sheet with retry logic for API errors"""
        max_retries = 3
        base_delay = 2
        
        for attempt in range(max_retries):
            try:
                # Update status with attempt info
                if attempt > 0:
                    embed.set_field_at(1, name="⏳ Status", value=f"🤖 AI analyzing... (Attempt {attempt + 1}/{max_retries})", inline=False)
                    await interaction.edit_original_response(embed=embed)
                
                character_data = await self._parse_character_sheet_with_ai(pdf_text, player_name, user_id)
                
                if character_data:
                    return character_data
                    
            except Exception as e:
                error_msg = str(e)
                print(f"Claude API attempt {attempt + 1} failed: {error_msg}")
                
                # Check if it's an API overload error
                if "overloaded" in error_msg.lower() or "529" in error_msg:
                    if attempt < max_retries - 1:
                        delay = base_delay * (2 ** attempt)  # Exponential backoff
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
                    print(f"Non-retryable error: {error_msg}")
                    return None
        
        return None
    
    async def _show_parsing_error(self, interaction: discord.Interaction, pdf_text: str):
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
        
        # Show extracted text preview so it's not a total loss
        text_preview = pdf_text[:500] + "..." if len(pdf_text) > 500 else pdf_text
        
        # Try to extract basic info manually as fallback
        basic_info = self._extract_basic_info_fallback(pdf_text)
        
        if basic_info:
            embed.add_field(
                name="📋 Basic Info Detected",
                value=f"We did extract some basic information from your PDF:\n"
                      f"**Name:** {basic_info.get('name', 'Not found')}\n"
                      f"**Class:** {basic_info.get('class', 'Not found')}\n"
                      f"**Level:** {basic_info.get('level', 'Not found')}\n"
                      f"**Race:** {basic_info.get('race', 'Not found')}\n\n"
                      f"You can use this info with `/character` for manual registration.",
                inline=False
            )
        
        embed.add_field(
            name="🤖 About This Error",
            value="This is a temporary issue with Anthropic's Claude AI service, not a problem with your character sheet or our bot. The service experiences high demand at times.",
            inline=False
        )
        
        embed.set_footer(text="Sorry for the inconvenience! Try again in a few minutes.")
        
        await interaction.edit_original_response(embed=embed)
    
    def _extract_basic_info_fallback(self, pdf_text: str) -> Dict[str, Optional[str]]:
        """Extract basic character info using simple text parsing as fallback"""
        basic_info = {
            'name': None,
            'class': None,
            'level': None,
            'race': None
        }
        
        text_lower = pdf_text.lower()
        lines = pdf_text.split('\n')
        
        # Common D&D classes for detection
        classes = ['fighter', 'wizard', 'rogue', 'cleric', 'ranger', 'paladin', 'barbarian', 'bard', 'druid', 'monk', 'sorcerer', 'warlock', 'artificer']
        races = ['human', 'elf', 'dwarf', 'halfling', 'dragonborn', 'gnome', 'half-elf', 'half-orc', 'tiefling', 'aasimar', 'genasi', 'goliath', 'tabaxi', 'kenku']
        
        for line in lines:
            line_lower = line.lower().strip()
            
            # Look for character name (often appears as "Character Name:" or similar)
            if 'character name' in line_lower or 'name:' in line_lower:
                # Try to extract name after colon or similar
                parts = re.split(r'[:;]', line)
                if len(parts) > 1:
                    potential_name = parts[1].strip()
                    if potential_name and len(potential_name) > 1 and len(potential_name) < 50:
                        basic_info['name'] = potential_name
            
            # Look for class
            for cls in classes:
                if cls in line_lower:
                    basic_info['class'] = cls.title()
                    break
            
            # Look for race
            for race in races:
                if race in line_lower:
                    basic_info['race'] = race.title()
                    break
            
            # Look for level
            level_match = re.search(r'level\s*:?\s*(\d+)', line_lower)
            if level_match:
                basic_info['level'] = level_match.group(1)
        
        return basic_info
    
    async def _show_upload_error(self, interaction: discord.Interaction, error_msg: str):
        """Show upload error with helpful information"""
        embed = discord.Embed(
            title="❌ Character Sheet Upload Failed",
            description="There was an issue processing your character sheet.",
            color=0xFF6B6B
        )
        
        if "overloaded" in error_msg.lower() or "529" in error_msg:
            embed.add_field(
                name="🤖 AI Service Overloaded",
                value="Claude AI is currently experiencing high demand. This is temporary and should resolve soon.",
                inline=False
            )
            embed.add_field(
                name="🔄 What to Do",
                value="• **Wait 5-10 minutes** and try uploading again\n• Use `/character` for manual registration in the meantime\n• The AI service typically recovers quickly",
                inline=False
            )
        else:
            embed.add_field(
                name="🔧 Troubleshooting",
                value="• Make sure the PDF contains readable text (not just images)\n• Try a different PDF if possible\n• Ensure the file is a valid D&D character sheet\n• Check that the file isn't corrupted",
                inline=False
            )
        
        embed.add_field(
            name="🆘 Alternative Options",
            value="• Use `/character` to manually register your character\n• Try uploading again later when AI service is less busy\n• Use `/character_sheet_help` for more guidance",
            inline=False
        )
        
        await interaction.edit_original_response(embed=embed)
    
    async def _extract_pdf_text(self, attachment: discord.Attachment) -> str:
        """Extract text from PDF using PyPDF2 and PyMuPDF as fallback"""
        pdf_content = await attachment.read()
        
        # Try PyMuPDF first (usually better at text extraction)
        try:
            doc = fitz.open(stream=pdf_content, filetype="pdf")
            text_parts = []
            
            for page_num in range(len(doc)):
                page = doc.load_page(page_num)
                text = page.get_text()
                if text.strip():  # Only add non-empty pages
                    text_parts.append(f"--- Page {page_num + 1} ---\n{text}")
            
            doc.close()
            full_text = "\n\n".join(text_parts)
            
            if full_text.strip():
                return full_text
        
        except Exception as e:
            print(f"PyMuPDF extraction failed: {e}")
        
        # Fallback to PyPDF2
        try:
            pdf_reader = PyPDF2.PdfReader(io.BytesIO(pdf_content))
            text_parts = []
            
            for page_num, page in enumerate(pdf_reader.pages):
                text = page.extract_text()
                if text.strip():  # Only add non-empty pages
                    text_parts.append(f"--- Page {page_num + 1} ---\n{text}")
            
            full_text = "\n\n".join(text_parts)
            return full_text
        
        except Exception as e:
            print(f"PyPDF2 extraction failed: {e}")
            raise ValueError("Could not extract text from PDF using any method")
    
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
        "charisma": "+0
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
            
            print(f"Claude response received: {len(response_text)} characters")
            
            # Try to extract JSON from the response
            json_start = response_text.find('{')
            json_end = response_text.rfind('}') + 1
            
            if json_start == -1 or json_end == 0:
                print("No JSON found in Claude response")
                return None
            
            json_text = response_text[json_start:json_end]
            
            # Parse JSON
            try:
                character_data = json.loads(json_text)
                
                # Validate required fields
                required_fields = ['name', 'race', 'class', 'level']
                for field in required_fields:
                    if field not in character_data or not character_data[field]:
                        print(f"Missing required field: {field}")
                        return None
                
                # Validate level
                if not isinstance(character_data['level'], int) or character_data['level'] < 1 or character_data['level'] > 20:
                    print(f"Invalid level: {character_data['level']}")
                    character_data['level'] = 1  # Default to 1
                
                print(f"Successfully parsed character: {character_data['name']}")
                return character_data
                
            except json.JSONDecodeError as e:
                print(f"JSON parse error: {e}")
                print(f"JSON text: {json_text[:500]}...")
                return None
        
        except Exception as e:
            print(f"Claude parsing error: {e}")
            # Re-raise the exception so retry logic can handle it
            raise e
    
    async def _show_confirmation(self, interaction: discord.Interaction, character_data: Dict[str, Any], 
                               user_id: str, player_name: str):
        """Show confirmation dialog for parsed character data"""
        
        # Create confirmation embed
        embed = discord.Embed(
            title="📋 Character Sheet Parsed Successfully!",
            description="Please review the information Donnie extracted from your character sheet:",
            color=0x32CD32
        )
        
        # Basic character info
        embed.add_field(
            name="⚔️ Basic Information",
            value=f"**Name:** {character_data.get('name', 'Unknown')}\n"
                  f"**Race:** {character_data.get('race', 'Unknown')}\n"
                  f"**Class:** {character_data.get('class', 'Unknown')}\n"
                  f"**Level:** {character_data.get('level', 1)}\n"
                  f"**Background:** {character_data.get('background', 'Unknown')}",
            inline=False
        )
        
        # Combat stats
        combat = character_data.get('combat_stats', {})
        embed.add_field(
            name="⚔️ Combat Stats",
            value=f"**AC:** {combat.get('armor_class', 10)} | "
                  f"**HP:** {combat.get('hit_point_maximum', 8)} | "
                  f"**Speed:** {combat.get('speed', '30 ft')}",
            inline=False
        )
        
        # Ability scores
        abilities = character_data.get('ability_scores', {})
        embed.add_field(
            name="📊 Ability Scores",
            value=f"**STR:** {abilities.get('strength', 10)} | "
                  f"**DEX:** {abilities.get('dexterity', 10)} | "
                  f"**CON:** {abilities.get('constitution', 10)}\n"
                  f"**INT:** {abilities.get('intelligence', 10)} | "
                  f"**WIS:** {abilities.get('wisdom', 10)} | "
                  f"**CHA:** {abilities.get('charisma', 10)}",
            inline=False
        )
        
        # Equipment summary
        equipment = character_data.get('equipment', {})
        weapons = equipment.get('weapons', [])
        armor = equipment.get('armor', [])
        weapon_text = ', '.join(weapons[:3]) if weapons else "None listed"
        armor_text = ', '.join(armor[:2]) if armor else "None listed"
        
        embed.add_field(
            name="🎒 Equipment Summary",
            value=f"**Weapons:** {weapon_text}\n**Armor:** {armor_text}",
            inline=False
        )
        
        # Spellcasting (if applicable)
        spellcasting = character_data.get('spellcasting', {})
        if spellcasting.get('spellcasting_class'):
            cantrips = spellcasting.get('cantrips', [])
            cantrip_text = ', '.join(cantrips[:3]) if cantrips else "None"
            embed.add_field(
                name="✨ Spellcasting",
                value=f"**Class:** {spellcasting.get('spellcasting_class')}\n"
                      f"**Spell Save DC:** {spellcasting.get('spell_save_dc', 8)}\n"
                      f"**Cantrips:** {cantrip_text}",
                inline=False
            )
        
        embed.add_field(
            name="❓ Is This Correct?",
            value="Click ✅ to confirm and register this character, or ❌ to cancel.\n\n"
                  "*All detailed information has been captured! This is just a summary.*",
            inline=False
        )
        
        embed.set_footer(text="Character data expires in 5 minutes if not confirmed")
        
        # Create view with confirmation buttons
        view = CharacterConfirmationView(self, character_data, user_id, player_name)
        
        # Store pending confirmation
        confirmation_id = f"{user_id}_{int(time.time())}"
        self.pending_confirmations[confirmation_id] = {
            'character_data': character_data,
            'user_id': user_id,
            'player_name': player_name,
            'timestamp': time.time()
        }
        view.confirmation_id = confirmation_id
        
        await interaction.edit_original_response(embed=embed, view=view)
    
    def cleanup_expired_confirmations(self) -> int:
        """Clean up expired confirmations and return count of removed items"""
        current_time = time.time()
        expired_keys = []
        
        for key, data in self.pending_confirmations.items():
            if current_time - data['timestamp'] > 300:  # 5 minutes
                expired_keys.append(key)
        
        for key in expired_keys:
            del self.pending_confirmations[key]
        
        return len(expired_keys)
    
    async def _show_upload_help(self, interaction: discord.Interaction):
        """Show help information for character sheet uploads"""
        embed = discord.Embed(
            title="📄 Character Sheet Upload Help",
            description="Learn how to upload and use PDF character sheets with Donnie!",
            color=0x4169E1
        )
        
        embed.add_field(
            name="📋 Supported Formats",
            value="• **PDF files only** (max 10MB)\n• Standard D&D 5e character sheets\n• Most online character sheet generators\n• Hand-filled sheets (if clearly readable)",
            inline=False
        )
        
        embed.add_field(
            name="🤖 AI Parsing Features",
            value="• **Complete Analysis**: Reads every stat, spell, and feature\n• **Smart Recognition**: Understands various sheet formats\n• **Validation**: Ensures all data is valid for D&D 5e\n• **Confirmation**: Always asks you to verify before saving",
            inline=False
        )
        
        embed.add_field(
            name="🔧 How to Use",
            value="1. Use `/upload_character_sheet` command\n2. Attach your PDF character sheet\n3. Wait for Donnie to analyze it (may take 30-60 seconds)\n4. Review the parsed information\n5. Click ✅ to confirm or ❌ to cancel",
            inline=False
        )
        
        embed.add_field(
            name="⚠️ Troubleshooting",
            value="• **AI Overloaded?** Wait 5-10 minutes and try again\n• **Text not readable?** Try a different PDF generator\n• **Missing information?** Use `/update_character` after upload\n• **Upload failed?** Use `/character` for manual registration",
            inline=False
        )
        
        embed.add_field(
            name="🎯 Best Practices",
            value="• Use official D&D character sheets when possible\n• Ensure all text is clear and readable\n• Fill out as much information as possible\n• Double-check the confirmation before accepting",
            inline=False
        )
        
        embed.add_field(
            name="🤖 About AI Service Issues",
            value="Sometimes Claude AI experiences high demand and becomes temporarily overloaded. This is normal and usually resolves within 5-10 minutes. You can always use `/character` for manual registration in the meantime.",
            inline=False
        )
        
        await interaction.response.send_message(embed=embed)


class CharacterConfirmationView(discord.ui.View):
    def __init__(self, pdf_commands, character_data, user_id, player_name):
        super().__init__(timeout=300)  # 5 minute timeout
        self.pdf_commands = pdf_commands
        self.character_data = character_data
        self.user_id = user_id
        self.player_name = player_name
        self.confirmation_id = None
    
    @discord.ui.button(label='✅ Confirm & Register', style=discord.ButtonStyle.green)
    async def confirm_character(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Confirm and register the character"""
        if str(interaction.user.id) != self.user_id:
            await interaction.response.send_message("❌ Only the person who uploaded the character sheet can confirm it!", ephemeral=True)
            return
        
        try:
            # Convert comprehensive data to legacy format for compatibility
            legacy_character_data = self._convert_to_legacy_format()
            
            # Create formatted character description for Claude
            character_description = self._create_character_description()
            
            # Store in campaign context
            self.pdf_commands.campaign_context["characters"][self.user_id] = character_description
            self.pdf_commands.campaign_context["players"][self.user_id] = {
                "user_id": self.user_id,
                "player_name": self.player_name,
                "character_data": legacy_character_data,
                "character_description": character_description,
                "comprehensive_data": self.character_data  # Store full data for future use
            }
            
            # Set guild_id if not set
            if self.pdf_commands.campaign_context["guild_id"] is None:
                self.pdf_commands.campaign_context["guild_id"] = str(interaction.guild.id)
            
            # Create success embed
            embed = discord.Embed(
                title="✅ Character Registered Successfully!",
                description=f"**{self.character_data['name']}** has been registered for Storm King's Thunder!",
                color=0x32CD32
            )
            
            embed.add_field(
                name="⚔️ Character Summary",
                value=f"**{self.character_data['race']} {self.character_data['class']}** (Level {self.character_data['level']})\n"
                      f"*{self.character_data.get('background', 'Unknown Background')}*\n"
                      f"👤 Player: {self.player_name}",
                inline=False
            )
            
            embed.add_field(
                name="🎮 Next Steps",
                value="• Use `/start_episode` to begin your adventure\n"
                      "• Use `/join_voice` for voice narration\n"
                      "• Use `/character_sheet` to view full details\n"
                      "• Use `/update_character` to modify any aspect",
                inline=False
            )
            
            embed.set_footer(text="All your character details have been saved! Ready for adventure!")
            
            # Clean up confirmation
            if self.confirmation_id and self.confirmation_id in self.pdf_commands.pending_confirmations:
                del self.pdf_commands.pending_confirmations[self.confirmation_id]
            
            # Update the message
            await interaction.response.edit_message(embed=embed, view=None)
            
        except Exception as e:
            print(f"Character confirmation error: {e}")
            await interaction.response.send_message("❌ Error registering character. Please try again or use manual registration.", ephemeral=True)
    
    @discord.ui.button(label='❌ Cancel', style=discord.ButtonStyle.red)
    async def cancel_character(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Cancel character registration"""
        if str(interaction.user.id) != self.user_id:
            await interaction.response.send_message("❌ Only the person who uploaded the character sheet can cancel it!", ephemeral=True)
            return
        
        embed = discord.Embed(
            title="❌ Character Registration Cancelled",
            description="Your character sheet upload has been cancelled. You can try uploading again or use `/character` for manual registration.",
            color=0xFF6B6B
        )
        
        # Clean up confirmation
        if self.confirmation_id and self.confirmation_id in self.pdf_commands.pending_confirmations:
            del self.pdf_commands.pending_confirmations[self.confirmation_id]
        
        await interaction.response.edit_message(embed=embed, view=None)
    
    async def on_timeout(self):
        """Handle timeout"""
        # Clean up confirmation
        if self.confirmation_id and self.confirmation_id in self.pdf_commands.pending_confirmations:
            del self.pdf_commands.pending_confirmations[self.confirmation_id]
    
    def _convert_to_legacy_format(self) -> Dict[str, Any]:
        """Convert comprehensive character data to legacy format"""
        # Create basic character profile compatible with existing system
        equipment_list = []
        
        # Combine equipment
        for category in ['weapons', 'armor', 'items', 'treasure']:
            items = self.character_data.get('equipment', {}).get(category, [])
            if items:
                equipment_list.extend(items)
        
        # Create spell list
        spell_list = []
        cantrips = self.character_data.get('spellcasting', {}).get('cantrips', [])
        if cantrips:
            spell_list.extend([f"Cantrip: {cantrip}" for cantrip in cantrips])
        
        spells_known = self.character_data.get('spellcasting', {}).get('spells_known', {})
        for level, spells in spells_known.items():
            if spells:
                spell_list.extend([f"{level.replace('_', ' ').title()}: {spell}" for spell in spells])
        
        # Create ability scores string
        abilities = self.character_data.get('ability_scores', {})
        stats_string = f"STR {abilities.get('strength', 10)}, DEX {abilities.get('dexterity', 10)}, CON {abilities.get('constitution', 10)}, INT {abilities.get('intelligence', 10)}, WIS {abilities.get('wisdom', 10)}, CHA {abilities.get('charisma', 10)}"
        
        # Create affiliations string
        affiliations_data = self.character_data.get('affiliations', {})
        affiliations_list = []
        for category, items in affiliations_data.items():
            if items:
                affiliations_list.extend(items)
        
        # Create personality string
        personality_data = self.character_data.get('personality', {})
        personality_parts = []
        if personality_data.get('personality_traits'):
            personality_parts.append(f"Traits: {', '.join(personality_data['personality_traits'])}")
        if personality_data.get('ideals'):
            personality_parts.append(f"Ideals: {', '.join(personality_data['ideals'])}")
        if personality_data.get('bonds'):
            personality_parts.append(f"Bonds: {', '.join(personality_data['bonds'])}")
        if personality_data.get('flaws'):
            personality_parts.append(f"Flaws: {', '.join(personality_data['flaws'])}")
        if personality_data.get('backstory'):
            personality_parts.append(f"Backstory: {personality_data['backstory']}")
        
        return {
            "name": self.character_data.get('name', 'Unknown'),
            "race": self.character_data.get('race', 'Unknown'),
            "class": self.character_data.get('class', 'Unknown'),
            "level": self.character_data.get('level', 1),
            "background": self.character_data.get('background', 'Unknown'),
            "stats": stats_string,
            "equipment": '; '.join(equipment_list) if equipment_list else "Basic adventuring gear",
            "spells": '; '.join(spell_list) if spell_list else "None",
            "affiliations": '; '.join(affiliations_list) if affiliations_list else "None",
            "personality": '; '.join(personality_parts) if personality_parts else "To be determined in play",
            "player_name": self.player_name,
            "discord_user_id": self.user_id
        }
    
    def _create_character_description(self) -> str:
        """Create character description for Claude AI"""
        # Create comprehensive description for Claude
        abilities = self.character_data.get('ability_scores', {})
        combat = self.character_data.get('combat_stats', {})
        
        description = f"""
NAME: {self.character_data.get('name', 'Unknown')}
PLAYER: {self.player_name} (Discord ID: {self.user_id})
RACE & CLASS: {self.character_data.get('race', 'Unknown')} {self.character_data.get('class', 'Unknown')} (Level {self.character_data.get('level', 1)})
BACKGROUND: {self.character_data.get('background', 'Unknown')}
ALIGNMENT: {self.character_data.get('alignment', 'Unknown')}

ABILITY SCORES: STR {abilities.get('strength', 10)} DEX {abilities.get('dexterity', 10)} CON {abilities.get('constitution', 10)} INT {abilities.get('intelligence', 10)} WIS {abilities.get('wisdom', 10)} CHA {abilities.get('charisma', 10)}

COMBAT STATS: AC {combat.get('armor_class', 10)}, HP {combat.get('hit_point_maximum', 8)}, Speed {combat.get('speed', '30 ft')}, Initiative {combat.get('initiative', '+0')}

PROFICIENCIES: {self.character_data.get('proficiencies', {}).get('proficiency_bonus', '+2')} proficiency bonus
- Saving Throws: {', '.join(self.character_data.get('proficiencies', {}).get('saving_throws', []))}
- Skills: {', '.join(self.character_data.get('proficiencies', {}).get('skills', []))}
- Languages: {', '.join(self.character_data.get('proficiencies', {}).get('languages', []))}

EQUIPMENT:
- Weapons: {', '.join(self.character_data.get('equipment', {}).get('weapons', []))}
- Armor: {', '.join(self.character_data.get('equipment', {}).get('armor', []))}
- Items: {', '.join(self.character_data.get('equipment', {}).get('items', []))}

SPELLCASTING: {self.character_data.get('spellcasting', {}).get('spellcasting_class', 'None')}
- Cantrips: {', '.join(self.character_data.get('spellcasting', {}).get('cantrips', []))}
- Spell Save DC: {self.character_data.get('spellcasting', {}).get('spell_save_dc', 'N/A')}

FEATURES & TRAITS:
- Racial: {', '.join(self.character_data.get('features_and_traits', {}).get('racial_traits', []))}
- Class: {', '.join(self.character_data.get('features_and_traits', {}).get('class_features', []))}
- Background: {', '.join(self.character_data.get('features_and_traits', {}).get('background_features', []))}

PERSONALITY:
- Traits: {', '.join(self.character_data.get('personality', {}).get('personality_traits', []))}
- Ideals: {', '.join(self.character_data.get('personality', {}).get('ideals', []))}
- Bonds: {', '.join(self.character_data.get('personality', {}).get('bonds', []))}
- Flaws: {', '.join(self.character_data.get('personality', {}).get('flaws', []))}

AFFILIATIONS:
- Organizations: {', '.join(self.character_data.get('affiliations', {}).get('organizations', []))}
- Allies: {', '.join(self.character_data.get('affiliations', {}).get('allies', []))}

PHYSICAL DESCRIPTION: Age {self.character_data.get('physical_description', {}).get('age', 'Unknown')}, {self.character_data.get('physical_description', {}).get('height', 'Unknown')} tall, {self.character_data.get('physical_description', {}).get('appearance', 'No description')}

ADDITIONAL NOTES: {self.character_data.get('additional_notes', 'None')}
"""
        return description.strip()