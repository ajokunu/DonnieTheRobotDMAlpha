# audio_system/enhanced_voice_manager.py
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
        """Wrapper for Claude API call - this will be set up in main.py"""
        # This gets replaced by the actual function in main.py
        return "Default response"
    
    async def _generate_tts_audio(self, text: str, **voice_params):
        """Wrapper for TTS generation - this will be set up in main.py"""
        # This gets replaced by the actual function in main.py
        return None
    
    async def play_sound_effect(self, guild_id: int, sound_file_path: str, voice_clients: Dict):
        """Play a sound effect in the voice channel"""
        if guild_id not in voice_clients:
            return
        
        voice_client = voice_clients[guild_id]
        if not voice_client or not voice_client.is_connected():
            return
        
        try:
            # Check if file exists
            if not os.path.exists(sound_file_path):
                return
            
            # Check if file has content (not empty placeholder)
            if os.path.getsize(sound_file_path) == 0:
                return
            
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