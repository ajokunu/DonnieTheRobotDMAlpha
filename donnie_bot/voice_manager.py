# voice_manager.py - Enhanced Voice Integration for Donnie Bot
"""
Voice Manager that integrates the enhanced audio system with the main bot.
This replaces the accidentally deleted voice_manager.py and connects
the audio_system module with Discord voice functionality.
"""

import asyncio
import discord
import os
import tempfile
import io
from typing import Dict, Optional, Any
import aiohttp

class VoiceManager:
    """
    Manages voice functionality with enhanced audio system integration
    """
    
    def __init__(self, bot, openai_api_key: str):
        self.bot = bot
        self.openai_api_key = openai_api_key
        
        # Voice client storage
        self.voice_clients: Dict[int, discord.VoiceClient] = {}
        self.tts_enabled: Dict[int, bool] = {}
        self.voice_speed: Dict[int, float] = {}
        self.voice_quality: Dict[int, str] = {}  # "speed", "quality", "smart"
        self.voice_queue: Dict[int, list] = {}
        
        # Enhanced audio system integration
        self.enhanced_voice_manager = None
        self._initialize_enhanced_audio()
        
        print("✅ Voice Manager initialized")
    
    def _initialize_enhanced_audio(self):
        """Initialize enhanced audio system if available"""
        try:
            from audio_system import EnhancedVoiceManager
            
            # Create mock claude_client for enhanced voice manager
            class MockClaudeClient:
                def __init__(self):
                    pass
            
            self.enhanced_voice_manager = EnhancedVoiceManager(
                claude_client=MockClaudeClient(),
                openai_api_key=self.openai_api_key
            )
            print("✅ Enhanced audio system integrated")
            
        except ImportError as e:
            print(f"⚠️ Enhanced audio system not available: {e}")
            self.enhanced_voice_manager = None
        except Exception as e:
            print(f"⚠️ Failed to initialize enhanced audio: {e}")
            self.enhanced_voice_manager = None
    
    async def join_voice_channel(self, interaction: discord.Interaction) -> bool:
        """Join user's voice channel with enhanced error handling"""
        
        # Check FFmpeg availability
        if not self._check_ffmpeg():
            await interaction.response.send_message(
                "❌ FFmpeg is not installed! Voice features require FFmpeg.", 
                ephemeral=True
            )
            return False
        
        # Validate user and permissions
        if not isinstance(interaction.user, discord.Member):
            await interaction.response.send_message(
                "❌ This command can only be used in a server!", 
                ephemeral=True
            )
            return False
        
        if not interaction.user.voice or not interaction.user.voice.channel:
            await interaction.response.send_message(
                "❌ You need to be in a voice channel first!", 
                ephemeral=True
            )
            return False
        
        voice_channel = interaction.user.voice.channel
        guild_id = interaction.guild.id
        
        # Check bot permissions
        bot_member = interaction.guild.get_member(self.bot.user.id)
        if not bot_member:
            await interaction.response.send_message(
                "❌ Bot member not found!", 
                ephemeral=True
            )
            return False
        
        channel_perms = voice_channel.permissions_for(bot_member)
        if not channel_perms.connect or not channel_perms.speak:
            await interaction.response.send_message(
                "❌ I don't have permission to join/speak in that voice channel!", 
                ephemeral=True
            )
            return False
        
        try:
            # Clean up existing connection
            if guild_id in self.voice_clients:
                try:
                    if self.voice_clients[guild_id].is_connected():
                        await self.voice_clients[guild_id].disconnect()
                except:
                    pass
                finally:
                    del self.voice_clients[guild_id]
            
            # Connect with timeout
            voice_client = await asyncio.wait_for(
                voice_channel.connect(), 
                timeout=10.0
            )
            
            # Store connection and enable TTS
            self.voice_clients[guild_id] = voice_client
            self.tts_enabled[guild_id] = True
            self.voice_speed[guild_id] = 1.25  # Default speed
            self.voice_quality[guild_id] = "smart"  # Default quality
            self.voice_queue[guild_id] = []
            
            # Success response
            embed = discord.Embed(
                title="🎤 Donnie the DM Joins!",
                description=f"*Donnie's expressive voice echoes through {voice_channel.name}*",
                color=0x32CD32
            )
            
            embed.add_field(
                name="🗣️ Enhanced Voice Activated",
                value="Donnie will now narrate with optimized TTS and Continue buttons!",
                inline=False
            )
            
            if self.enhanced_voice_manager:
                embed.add_field(
                    name="⚡ Enhanced Audio Features",
                    value="• Dynamic voice styles based on content\n• Sound effects for actions\n• Optimized response splitting\n• Parallel audio processing",
                    inline=False
                )
            
            embed.add_field(
                name="🔧 Voice Controls",
                value="`/mute_donnie` - Disable TTS\n`/unmute_donnie` - Enable TTS\n`/leave_voice` - Leave channel\n`/donnie_speed <speed>` - Adjust speed\n`/voice_quality <mode>` - Set quality",
                inline=False
            )
            
            await interaction.response.send_message(embed=embed)
            
            # Play welcome message
            welcome_text = "Well, well. Another group of 'adventurers.' I'm Donnie, your DM, and I can already sense the chaos brewing. Let the Storm King's Thunder campaign begin!"
            await self.speak_text(guild_id, welcome_text, "Donnie")
            
            return True
            
        except asyncio.TimeoutError:
            await interaction.response.send_message(
                "❌ Timed out joining voice channel! Channel might be full.", 
                ephemeral=True
            )
            return False
        except Exception as e:
            await interaction.response.send_message(
                f"❌ Failed to join voice channel: {str(e)}", 
                ephemeral=True
            )
            return False
    
    async def leave_voice_channel(self, guild_id: int) -> bool:
        """Leave voice channel and cleanup"""
        try:
            if guild_id not in self.voice_clients:
                return False
            
            voice_client = self.voice_clients[guild_id]
            if voice_client.is_connected():
                await voice_client.disconnect()
            
            # Cleanup
            del self.voice_clients[guild_id]
            self.tts_enabled[guild_id] = False
            if guild_id in self.voice_speed:
                del self.voice_speed[guild_id]
            if guild_id in self.voice_quality:
                del self.voice_quality[guild_id]
            if guild_id in self.voice_queue:
                del self.voice_queue[guild_id]
            
            return True
            
        except Exception as e:
            print(f"❌ Error leaving voice channel: {e}")
            return False
    
    async def speak_text(self, guild_id: int, text: str, speaker: str = "Donnie") -> bool:
        """Speak text with enhanced audio processing if available"""
        
        if not self.is_voice_active(guild_id):
            return False
        
        try:
            # Use enhanced voice manager if available
            if self.enhanced_voice_manager:
                return await self._speak_with_enhanced_system(guild_id, text, speaker)
            else:
                return await self._speak_with_basic_system(guild_id, text)
                
        except Exception as e:
            print(f"❌ Error in speak_text: {e}")
            return False
    
    async def _speak_with_enhanced_system(self, guild_id: int, text: str, speaker: str) -> bool:
        """Use enhanced audio system for speaking"""
        try:
            # Add to voice queue for processing
            if guild_id not in self.voice_queue:
                self.voice_queue[guild_id] = []
            
            self.voice_queue[guild_id].append({
                'text': text,
                'speaker': speaker,
                'timestamp': asyncio.get_event_loop().time()
            })
            
            # Process queue if not already processing
            if len(self.voice_queue[guild_id]) == 1:
                asyncio.create_task(self._process_enhanced_voice_queue(guild_id))
            
            return True
            
        except Exception as e:
            print(f"❌ Enhanced voice system error: {e}")
            # Fallback to basic system
            return await self._speak_with_basic_system(guild_id, text)
    
    async def _speak_with_basic_system(self, guild_id: int, text: str) -> bool:
        """Basic TTS without enhanced features"""
        try:
            voice_client = self.voice_clients.get(guild_id)
            if not voice_client or not voice_client.is_connected():
                return False
            
            # Generate TTS audio
            speed = self.voice_speed.get(guild_id, 1.25)
            quality = self.voice_quality.get(guild_id, "smart")
            model = "tts-1-hd" if quality == "quality" else "tts-1"
            
            audio_data = await self._generate_tts_audio(text, speed=speed, model=model)
            if not audio_data:
                return False
            
            # Save to temp file and play
            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as temp_file:
                temp_file.write(audio_data.getvalue())
                temp_filename = temp_file.name
            
            try:
                # Wait for current audio to finish
                while voice_client.is_playing():
                    await asyncio.sleep(0.1)
                
                # Play audio
                audio_source = discord.FFmpegPCMAudio(temp_filename)
                voice_client.play(audio_source)
                
                # Wait for completion
                while voice_client.is_playing():
                    await asyncio.sleep(0.1)
                
                return True
                
            finally:
                # Cleanup temp file
                try:
                    os.unlink(temp_filename)
                except:
                    pass
            
        except Exception as e:
            print(f"❌ Basic voice system error: {e}")
            return False
    
    async def _process_enhanced_voice_queue(self, guild_id: int):
        """Process voice queue with enhanced audio features"""
        
        while guild_id in self.voice_queue and self.voice_queue[guild_id]:
            try:
                queue_item = self.voice_queue[guild_id].pop(0)
                text = queue_item['text']
                speaker = queue_item.get('speaker', 'Donnie')
                
                # Use enhanced voice manager features
                if self.enhanced_voice_manager:
                    try:
                        # Analyze text for voice styling
                        emotion = self.enhanced_voice_manager.voice_styles.analyze_response_emotion(text)
                        content_type = self.enhanced_voice_manager.voice_styles.analyze_content_type(text)
                        
                        # Get optimized voice parameters
                        base_speed = self.voice_speed.get(guild_id, 1.25)
                        voice_params = self.enhanced_voice_manager.voice_styles.get_voice_parameters(
                            emotion, content_type, base_speed
                        )
                        
                        # Optimize text for TTS
                        optimized_text = self.enhanced_voice_manager.response_analyzer.optimize_for_tts(text)
                        
                        # Generate and play audio with enhanced parameters
                        audio_data = await self._generate_tts_audio(
                            optimized_text, 
                            speed=voice_params['speed'],
                            voice=voice_params['voice'],
                            model=voice_params['model']
                        )
                        
                        if audio_data:
                            await self._play_audio_data(guild_id, audio_data)
                        
                        print(f"✅ Enhanced voice: {emotion} {content_type} at {voice_params['speed']:.2f}x")
                        
                    except Exception as e:
                        print(f"⚠️ Enhanced voice failed, using basic: {e}")
                        await self._speak_with_basic_system(guild_id, text)
                else:
                    # Fallback to basic system
                    await self._speak_with_basic_system(guild_id, text)
                
                # Small pause between items
                await asyncio.sleep(0.3)
                
            except Exception as e:
                print(f"❌ Voice queue processing error: {e}")
                break
    
    async def _generate_tts_audio(self, text: str, speed: float = 1.25, 
                                voice: str = "fable", model: str = "tts-1") -> Optional[io.BytesIO]:
        """Generate TTS audio using OpenAI API"""
        try:
            # Clean text for TTS
            clean_text = text.replace("**", "").replace("*", "").replace("_", "")
            
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=8)) as session:
                headers = {
                    "Authorization": f"Bearer {self.openai_api_key}",
                    "Content-Type": "application/json"
                }
                
                payload = {
                    "model": model,
                    "input": clean_text,
                    "voice": voice,
                    "response_format": "mp3",
                    "speed": speed
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
                        print(f"❌ OpenAI TTS API error: {response.status} - {error_text}")
                        return None
                        
        except Exception as e:
            print(f"❌ TTS generation error: {e}")
            return None
    
    async def _play_audio_data(self, guild_id: int, audio_data: io.BytesIO) -> bool:
        """Play audio data in voice channel"""
        try:
            voice_client = self.voice_clients.get(guild_id)
            if not voice_client or not voice_client.is_connected():
                return False
            
            # Save to temp file
            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as temp_file:
                temp_file.write(audio_data.getvalue())
                temp_filename = temp_file.name
            
            try:
                # Wait for current audio to finish
                while voice_client.is_playing():
                    await asyncio.sleep(0.05)
                
                # Play audio
                audio_source = discord.FFmpegPCMAudio(temp_filename)
                voice_client.play(audio_source)
                
                # Wait for completion
                while voice_client.is_playing():
                    await asyncio.sleep(0.1)
                
                return True
                
            finally:
                # Cleanup
                try:
                    os.unlink(temp_filename)
                except:
                    pass
            
        except Exception as e:
            print(f"❌ Audio playback error: {e}")
            return False
    
    def is_voice_active(self, guild_id: int) -> bool:
        """Check if voice is active for guild"""
        return (guild_id in self.voice_clients and 
                self.voice_clients[guild_id].is_connected() and 
                self.tts_enabled.get(guild_id, False))
    
    def set_voice_speed(self, guild_id: int, speed: float) -> bool:
        """Set voice speed for guild"""
        if 0.25 <= speed <= 4.0:
            self.voice_speed[guild_id] = speed
            return True
        return False
    
    def set_voice_quality(self, guild_id: int, quality: str) -> bool:
        """Set voice quality mode"""
        if quality in ["speed", "quality", "smart"]:
            self.voice_quality[guild_id] = quality
            return True
        return False
    
    def mute_voice(self, guild_id: int):
        """Mute voice for guild"""
        self.tts_enabled[guild_id] = False
    
    def unmute_voice(self, guild_id: int):
        """Unmute voice for guild"""
        if guild_id in self.voice_clients and self.voice_clients[guild_id].is_connected():
            self.tts_enabled[guild_id] = True
    
    def get_voice_status(self, guild_id: int) -> Dict[str, Any]:
        """Get voice status for guild"""
        if guild_id not in self.voice_clients:
            return {"connected": False, "enabled": False}
        
        voice_client = self.voice_clients[guild_id]
        return {
            "connected": voice_client.is_connected() if voice_client else False,
            "enabled": self.tts_enabled.get(guild_id, False),
            "speed": self.voice_speed.get(guild_id, 1.25),
            "quality": self.voice_quality.get(guild_id, "smart"),
            "queue_size": len(self.voice_queue.get(guild_id, [])),
            "enhanced_audio": self.enhanced_voice_manager is not None
        }
    
    async def play_thinking_sound(self, guild_id: int, character_name: str = "adventurer"):
        """Play a random DM thinking sound immediately to fill waiting time"""
        
        if not self.is_voice_active(guild_id):
            return
        
        # DM thinking sounds from original main.py
        thinking_sounds = [
            "...Hhhhhmm...",
            "...Aaahhh okay let's try",
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
        
        # Choose a random thinking sound
        import random
        thinking_sound = random.choice(thinking_sounds)
        
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
        await self._speak_thinking_sound_directly(guild_id, thinking_sound)
    
    async def _speak_thinking_sound_directly(self, guild_id: int, text: str):
        """Play thinking sound directly without queue system - for immediate feedback"""
        
        if not self.is_voice_active(guild_id):
            return
        
        voice_client = self.voice_clients.get(guild_id)
        if not voice_client or not voice_client.is_connected():
            return
        
        # Use faster speed for thinking sounds to keep them brief
        base_speed = self.voice_speed.get(guild_id, 1.25)
        thinking_speed = base_speed * 1.3  # 30% faster for thinking sounds
        
        try:
            # Generate TTS audio quickly with faster model
            audio_data = await self._generate_tts_audio(
                text, 
                speed=thinking_speed, 
                voice="fable", 
                model="tts-1"  # Use faster model for thinking sounds
            )
            
            if not audio_data:
                return
            
            # Save to temporary file
            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as temp_file:
                temp_file.write(audio_data.getvalue())
                temp_filename = temp_file.name
            
            try:
                # Play immediately if not currently playing
                if not voice_client.is_playing():
                    audio_source = discord.FFmpegPCMAudio(temp_filename)
                    voice_client.play(audio_source)
                    
                    # Wait for this short sound to finish
                    while voice_client.is_playing():
                        await asyncio.sleep(0.05)  # Reduced polling interval
                
            finally:
                # Clean up temp file
                try:
                    os.unlink(temp_filename)
                except:
                    pass
                    
        except Exception as e:
            print(f"❌ Thinking sound error: {e}")
    
    def optimize_text_for_tts(self, text: str) -> str:
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
    
    def _check_ffmpeg(self) -> bool:
        """Check if FFmpeg is available"""
        try:
            import subprocess
            subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True)
            return True
        except:
            return False
    
    async def add_to_voice_queue__legacy(self, guild_id: int, text: str, speaker: str, message=None):
        """Legacy compatibility method for add_to_voice_queue calls"""
        
        # Update message if provided
        if message and self.is_voice_active(guild_id):
            try:
                embed = message.embeds[0] if message.embeds else None
                if embed:
                    for i, field in enumerate(embed.fields):
                        if field.name == "🎤":
                            embed.set_field_at(i, name="🎤", value=f"*Donnie responds to {speaker}*", inline=False)
                            break
                    await message.edit(embed=embed)
            except Exception as e:
                print(f"⚠️ Message update failed: {e}")
        
        # Speak the text
        await self.speak_text(guild_id, text, speaker)
    
    def create_tts_version(self, dm_response: str) -> str:
        """Create TTS-optimized version of DM response (legacy compatibility)"""
        return self.optimize_text_for_tts(dm_response)
    
    async def cleanup(self):
        """Cleanup all voice connections"""
        for guild_id in list(self.voice_clients.keys()):
            await self.leave_voice_channel(guild_id)
        
        print("✅ Voice manager cleanup completed")

# Global voice manager instance
voice_manager_instance = None

def initialize_voice_manager(bot, openai_api_key: str) -> VoiceManager:
    """Initialize the global voice manager"""
    global voice_manager_instance
    
    voice_manager_instance = VoiceManager(bot, openai_api_key)
    return voice_manager_instance

def get_voice_manager() -> Optional[VoiceManager]:
    """Get the global voice manager instance"""
    return voice_manager_instance

# ===== LEGACY COMPATIBILITY FUNCTIONS =====
# These allow your existing main.py code to work without major changes

async def add_to_voice_queue(guild_id: int, text: str, speaker: str, message=None):
    """Legacy function for compatibility with existing main.py code"""
    if voice_manager_instance:
        await voice_manager_instance.add_to_voice_queue_legacy(guild_id, text, speaker, message)
    else:
        print("⚠️ Voice manager not available for add_to_voice_queue")

async def play_thinking_sound(guild_id: int, character_name: str = "adventurer"):
    """Legacy function for compatibility with existing main.py code"""
    if voice_manager_instance:
        await voice_manager_instance.play_thinking_sound(guild_id, character_name)
    else:
        print("⚠️ Voice manager not available for play_thinking_sound")

def create_tts_version(dm_response: str) -> str:
    """Legacy function for compatibility with existing main.py code"""
    if voice_manager_instance:
        return voice_manager_instance.create_tts_version(dm_response)
    else:
        # Fallback basic cleaning
        return dm_response.replace("**", "").replace("*", "")

def optimize_text_for_tts(text: str) -> str:
    """Legacy function for compatibility with existing main.py code"""
    if voice_manager_instance:
        return voice_manager_instance.optimize_text_for_tts(text)
    else:
        # Fallback basic cleaning
        return text.replace("**", "").replace("*", "")

def is_voice_active(guild_id: int) -> bool:
    """Legacy function to check if voice is active"""
    if voice_manager_instance:
        return voice_manager_instance.is_voice_active(guild_id)
    else:
        return False