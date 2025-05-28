# File: audio_system/sound_effects.py
import random
import os
import asyncio
import tempfile
from pathlib import Path
from typing import Dict, List, Optional
import discord

class SoundEffectManager:
    """Manages realistic DM sound effects"""
    
    def __init__(self):
        self.sound_library = {
            "dice_rolls": [
                "d20_roll_1.mp3", "d20_roll_2.mp3", "d20_roll_3.mp3",
                "multi_dice_1.mp3", "multi_dice_2.mp3"
            ],
            "papers": [
                "page_turn_1.mp3", "page_turn_2.mp3", 
                "paper_rustle_1.mp3", "paper_rustle_2.mp3",
                "book_flip_1.mp3"
            ],
            "dm_reactions": [
                "throat_clear_1.mp3", "throat_clear_2.mp3",
                "sharp_breath_1.mp3", "sharp_breath_2.mp3", 
                "thinking_hum_1.mp3", "thinking_hum_2.mp3",
                "tongue_click_1.mp3"
            ],
            "ambient": [
                "chair_creak_1.mp3", "chair_creak_2.mp3",
                "quiet_movement_1.mp3", "room_tone_1.mp3"
            ]
        }
        
        # Contextual sound pools
        self.context_sounds = {
            "combat": ["dice_rolls", "dm_reactions"],
            "exploration": ["papers", "dm_reactions", "ambient"],
            "social": ["dm_reactions", "ambient"],
            "general": ["dm_reactions"]
        }
    
    def get_contextual_interruption(self, context: str) -> Optional[str]:
        """Get a random sound effect appropriate for the context"""
        # 25% chance of interruption
        if random.random() > 0.25:
            return None
            
        available_categories = self.context_sounds.get(context, ["dm_reactions"])
        category = random.choice(available_categories)
        sound_file = random.choice(self.sound_library[category])
        
        return f"audio_assets/{category}/{sound_file}"
    
    def detect_action_context(self, action_text: str) -> str:
        """Analyze player action to determine context"""
        action_lower = action_text.lower()
        
        combat_keywords = ["attack", "hit", "damage", "fight", "cast", "spell", "sword", "bow"]
        exploration_keywords = ["look", "search", "investigate", "move", "go", "enter", "examine"]
        social_keywords = ["talk", "say", "ask", "persuade", "intimidate", "convince", "speak"]
        
        if any(keyword in action_lower for keyword in combat_keywords):
            return "combat"
        elif any(keyword in action_lower for keyword in exploration_keywords):
            return "exploration"
        elif any(keyword in action_lower for keyword in social_keywords):
            return "social"
        else:
            return "general"

# File: audio_system/voice_styles.py
import asyncio
import aiohttp
import io
from typing import Dict, Tuple, Optional

class VoiceStyleManager:
    """Manages different voice styles for Donnie"""
    
    def __init__(self):
        self.voice_styles = {
            "standard": {
                "speed": 1.22,
                "voice": "fable",
                "model": "tts-1-hd"
            },
            "excited": {
                "speed": 1.30,
                "voice": "fable", 
                "model": "tts-1-hd"
            },
            "dramatic": {
                "speed": 1.15,
                "voice": "fable",
                "model": "tts-1-hd"
            }
        }
    
    def analyze_response_emotion(self, response_text: str) -> str:
        """Determine the emotional tone of the response"""
        text_lower = response_text.lower()
        
        # Excitement triggers
        excitement_words = [
            "critical hit", "natural 20", "you succeed", "excellent", 
            "perfect", "amazing", "incredible", "you hit", "critical"
        ]
        
        # Dramatic triggers  
        dramatic_words = [
            "initiative", "saving throw", "you take", "damage", 
            "suddenly", "you see", "looming", "massive", "threat"
        ]
        
        # Check for excitement first (more specific)
        if any(word in text_lower for word in excitement_words):
            return "excited"
        elif any(word in text_lower for word in dramatic_words):
            return "dramatic"
        else:
            return "standard"
    
    def analyze_content_type(self, response_text: str) -> str:
        """Determine the type of content for specialized delivery"""
        text_lower = response_text.lower()
        
        # Numbers and stats
        if any(word in text_lower for word in ["roll", "dc", "damage", "d20", "d6", "d8", "d10", "d12"]):
            return "stats"
        
        # Dialog
        if '"' in response_text or "says" in text_lower or "tells you" in text_lower:
            return "dialog"
        
        # Action sequences
        if any(word in text_lower for word in ["attack", "hits", "misses", "combat", "initiative"]):
            return "action"
        
        # Default to flavor text
        return "flavor"
    
    def get_voice_parameters(self, emotion: str, content_type: str, base_speed: float = 1.25) -> Dict:
        """Get TTS parameters based on emotion and content"""
        style = self.voice_styles[emotion].copy()
        
        # Adjust for content type
        if content_type == "stats":
            style["speed"] = max(0.9, style["speed"] - 0.2)  # Slower for numbers
        elif content_type == "action":
            style["speed"] = min(1.6, style["speed"] + 0.15)  # Faster for action
        elif content_type == "dialog":
            style["speed"] = style["speed"]  # Keep character-appropriate
        
        # Apply user's base speed preference
        speed_multiplier = base_speed / 1.25  # 1.25 is our default
        style["speed"] *= speed_multiplier
        
        return style

# File: audio_system/response_analyzer.py
import re
from typing import List, Tuple, Dict

class ResponseAnalyzer:
    """Analyzes DM responses for smart windowing and content optimization"""
    
    def __init__(self):
        # Natural break points in DM responses
        self.break_patterns = [
            r'\.(\s+What do you do\?)',
            r'\.(\s+Roll (?:a|an|for) .+?\.)',
            r'\.(\s+Make (?:a|an) .+? (?:check|save)\.)', 
            r'\.(\s+(?:The|You see|Suddenly).+?\.)',
            r'\.(\s+(?:Meanwhile|At the same time|Also).+?)'
        ]
        
        # Response priority levels
        self.priority_content = [
            "immediate results",  # Hit/miss, success/failure
            "mechanical effects",  # Damage, conditions, rules
            "environmental changes",  # What happens in the world
            "npc reactions",  # How NPCs respond
            "future implications"  # What this means going forward
        ]
    
    def should_split_response(self, response: str) -> bool:
        """Determine if response should be split into multiple windows"""
        # Split if longer than 400 characters AND has natural break points
        if len(response) > 400:
            return any(re.search(pattern, response) for pattern in self.break_patterns)
        return False
    
    def find_natural_break_point(self, response: str) -> Tuple[str, str]:
        """Find the best place to split a response"""
        for pattern in self.break_patterns:
            match = re.search(pattern, response)
            if match:
                break_point = match.start() + 1  # Include the period
                first_part = response[:break_point].strip()
                second_part = response[break_point:].strip()
                return first_part, second_part
        
        # Fallback: split at roughly halfway point at sentence boundary
        sentences = response.split('. ')
        if len(sentences) > 2:
            mid_point = len(sentences) // 2
            first_part = '. '.join(sentences[:mid_point]) + '.'
            second_part = '. '.join(sentences[mid_point:])
            return first_part, second_part
        
        # If no good split point, return original
        return response, ""
    
    def optimize_for_tts(self, text: str) -> str:
        """Optimize text specifically for TTS delivery"""
        # Remove excessive formatting
        clean_text = text.replace("**", "").replace("*", "").replace("_", "")
        
        # Spell out dice notation for better pronunciation
        clean_text = re.sub(r'\b(\d+)d(\d+)\b', r'\1 dee \2', clean_text)
        clean_text = re.sub(r'\bDC\s*(\d+)\b', r'difficulty class \1', clean_text)
        
        # Add pauses for better flow
        clean_text = re.sub(r'\.(\s+)', r'.\n', clean_text)  # Paragraph breaks
        clean_text = re.sub(r',(\s+)', r', ', clean_text)  # Comma pauses
        
        return clean_text.strip()

# File: audio_system/parallel_processor.py
import asyncio
from typing import Callable, Optional, Dict, Any
import logging

class ParallelResponseProcessor:
    """Handles parallel processing of Claude responses and TTS generation"""
    
    def __init__(self, 
                 claude_response_func: Callable,
                 tts_generation_func: Callable,
                 sound_effect_manager,
                 voice_style_manager,
                 response_analyzer):
        self.claude_response_func = claude_response_func
        self.tts_generation_func = tts_generation_func
        self.sound_effects = sound_effect_manager
        self.voice_styles = voice_style_manager
        self.response_analyzer = response_analyzer
        
    async def process_action_with_parallel_audio(self, 
                                               user_id: str, 
                                               action_text: str,
                                               guild_id: int,
                                               base_voice_speed: float = 1.25) -> Dict[str, Any]:
        """
        Process a player action with parallel audio generation
        Returns: {
            'response_text': str,
            'follow_up_text': str (if split),
            'tts_audio': BytesIO,
            'follow_up_audio': BytesIO (if split),
            'interruption_sound': str (file path)
        }
        """
        
        # 1. Immediate context analysis and sound effect
        context = self.sound_effects.detect_action_context(action_text)
        interruption_sound = self.sound_effects.get_contextual_interruption(context)
        
        # 2. Start Claude response in background
        claude_task = asyncio.create_task(
            self.claude_response_func(user_id, action_text)
        )
        
        # 3. Play interruption sound immediately (if any)
        if interruption_sound:
            # This would trigger immediate sound playback
            pass
        
        # 4. Wait for Claude response
        full_response = await claude_task
        
        # 5. Analyze response for splitting and styling
        should_split = self.response_analyzer.should_split_response(full_response)
        
        if should_split:
            first_part, second_part = self.response_analyzer.find_natural_break_point(full_response)
        else:
            first_part = full_response
            second_part = ""
        
        # 6. Analyze emotional tone and content type
        emotion = self.voice_styles.analyze_response_emotion(first_part)
        content_type = self.voice_styles.analyze_content_type(first_part)
        
        # 7. Generate TTS parameters
        voice_params = self.voice_styles.get_voice_parameters(emotion, content_type, base_voice_speed)
        
        # 8. Optimize text for TTS
        tts_text = self.response_analyzer.optimize_for_tts(first_part)
        
        # 9. Generate TTS audio
        main_audio = await self.tts_generation_func(tts_text, **voice_params)
        
        # 10. Generate follow-up audio if needed
        follow_up_audio = None
        if second_part:
            follow_up_emotion = self.voice_styles.analyze_response_emotion(second_part)
            follow_up_content = self.voice_styles.analyze_content_type(second_part)
            follow_up_params = self.voice_styles.get_voice_parameters(follow_up_emotion, follow_up_content, base_voice_speed)
            follow_up_tts_text = self.response_analyzer.optimize_for_tts(second_part)
            follow_up_audio = await self.tts_generation_func(follow_up_tts_text, **follow_up_params)
        
        return {
            'response_text': first_part,
            'follow_up_text': second_part if second_part else None,
            'tts_audio': main_audio,
            'follow_up_audio': follow_up_audio,
            'interruption_sound': interruption_sound,
            'emotion': emotion,
            'content_type': content_type
        }

# File: audio_system/enhanced_voice_manager.py
from .sound_effects import SoundEffectManager
from .voice_styles import VoiceStyleManager  
from .response_analyzer import ResponseAnalyzer
from .parallel_processor import ParallelResponseProcessor
import discord
import asyncio
import os
import tempfile
from typing import Dict, Optional, Callable

class EnhancedVoiceManager:
    """Main interface for the enhanced voice system"""
    
    def __init__(self, claude_client, openai_api_key: str):
        self.claude_client = claude_client
        self.openai_api_key = openai_api_key
        
        # Initialize subsystems
        self.sound_effects = SoundEffectManager()
        self.voice_styles = VoiceStyleManager()
        self.response_analyzer = ResponseAnalyzer()
        
        # Initialize parallel processor
        self.parallel_processor = ParallelResponseProcessor(
            claude_response_func=self._get_claude_response,
            tts_generation_func=self._generate_tts_audio,
            sound_effect_manager=self.sound_effects,
            voice_style_manager=self.voice_styles,
            response_analyzer=self.response_analyzer
        )
    
    async def _get_claude_response(self, user_id: str, player_input: str) -> str:
        """Wrapper for Claude API call - implement with your existing logic"""
        # This would use your existing get_claude_dm_response function
        pass
    
    async def _generate_tts_audio(self, text: str, **voice_params):
        """Wrapper for TTS generation - implement with your existing logic"""
        # This would use your existing generate_tts_audio function with voice_params
        pass
    
    async def play_sound_effect(self, guild_id: int, sound_file_path: str, voice_clients: Dict):
        """Play a sound effect in the voice channel"""
        if guild_id not in voice_clients:
            return
        
        voice_client = voice_clients[guild_id]
        if not voice_client or not voice_client.is_connected():
            return
        
        try:
            # Wait for any current audio to finish
            while voice_client.is_playing():
                await asyncio.sleep(0.1)
            
            # Play sound effect
            audio_source = discord.FFmpegPCMAudio(sound_file_path)
            voice_client.play(audio_source)
            
            # Wait for sound to finish
            while voice_client.is_playing():
                await asyncio.sleep(0.1)
                
        except Exception as e:
            print(f"Sound effect error: {e}")
    
    async def process_player_action(self, 
                                  user_id: str,
                                  action_text: str, 
                                  guild_id: int,
                                  voice_clients: Dict,
                                  tts_enabled: Dict,
                                  voice_speed: Dict,
                                  campaign_context: Dict) -> Dict:
        """
        Main entry point for processing player actions with enhanced voice
        """
        base_speed = voice_speed.get(guild_id, 1.25)
        voice_active = (guild_id in voice_clients and 
                       voice_clients[guild_id].is_connected() and 
                       tts_enabled.get(guild_id, False))
        
        # Process with parallel audio
        result = await self.parallel_processor.process_action_with_parallel_audio(
            user_id, action_text, guild_id, base_speed
        )
        
        # Play interruption sound immediately if voice is active
        if voice_active and result['interruption_sound']:
            await self.play_sound_effect(guild_id, result['interruption_sound'], voice_clients)
        
        return result