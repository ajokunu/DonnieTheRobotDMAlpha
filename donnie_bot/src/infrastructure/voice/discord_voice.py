"""
Discord voice service implementation
"""
import discord
import asyncio
import tempfile
import os
from typing import Dict, List, Optional
from pathlib import Path

from ...domain.interfaces.voice_service import VoiceServiceInterface, VoiceConfig, AudioData
from ..config.settings import VoiceConfig as InfraVoiceConfig


class DiscordVoiceService(VoiceServiceInterface):
    """Discord voice service implementation"""
    
    def __init__(self, config: InfraVoiceConfig):
        self.config = config
        self.voice_clients: Dict[str, discord.VoiceClient] = {}
        self.audio_queue: Dict[str, asyncio.Queue] = {}
        
        # Ensure cache directory exists
        self.cache_dir = Path(config.cache_directory)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
    
    async def text_to_speech(self, text: str, config: VoiceConfig = None) -> AudioData:
        """Convert text to speech audio using system TTS"""
        
        if config is None:
            config = VoiceConfig()
        
        try:
            # For now, we'll create a simple placeholder audio file
            # In a real implementation, you'd integrate with a TTS service like:
            # - Azure Cognitive Services
            # - Google Cloud Text-to-Speech  
            # - Amazon Polly
            # - ElevenLabs
            
            # Create a temporary audio file (placeholder)
            # This would normally contain actual TTS audio
            temp_file = tempfile.NamedTemporaryFile(suffix='.mp3', delete=False)
            
            # For demonstration, create minimal MP3 header (won't actually play)
            # Replace this with actual TTS service integration
            placeholder_data = b'\xFF\xFB\x90\x00' + b'\x00' * 1000  # Minimal MP3 header + silence
            temp_file.write(placeholder_data)
            temp_file.close()
            
            # Read the audio data
            with open(temp_file.name, 'rb') as f:
                audio_data = f.read()
            
            # Clean up temp file
            os.unlink(temp_file.name)
            
            return AudioData(
                data=audio_data,
                format="mp3",
                duration_seconds=len(text) * 0.1,  # Rough estimate
                metadata={
                    "text": text[:100],
                    "voice_id": config.voice_id,
                    "speed": config.speed,
                    "source": "placeholder_tts"
                }
            )
            
        except Exception as e:
            # Return minimal audio data on error
            return AudioData(
                data=b'\xFF\xFB\x90\x00' + b'\x00' * 100,
                format="mp3",
                metadata={"error": str(e), "text": text[:50]}
            )
    
    async def play_audio(self, guild_id: str, audio_data: AudioData) -> bool:
        """Play audio in a voice channel"""
        
        if not self.config.enabled:
            return False
        
        voice_client = self.voice_clients.get(guild_id)
        if not voice_client or not voice_client.is_connected():
            return False
        
        try:
            # Save audio to temporary file
            temp_file = tempfile.NamedTemporaryFile(suffix=f'.{audio_data.format}', delete=False)
            temp_file.write(audio_data.data)
            temp_file.close()
            
            # Create FFmpeg audio source
            audio_source = discord.FFmpegPCMAudio(
                temp_file.name,
                before_options='-f mp3',  # Input format
                options='-vn'  # No video
            )
            
            # Play audio (this will block until finished)
            if not voice_client.is_playing():
                voice_client.play(audio_source)
                
                # Wait for playback to finish
                while voice_client.is_playing():
                    await asyncio.sleep(0.1)
            
            # Clean up temp file
            os.unlink(temp_file.name)
            
            return True
            
        except Exception as e:
            print(f"❌ Error playing audio in guild {guild_id}: {e}")
            return False
    
    async def join_voice_channel(self, guild_id: str, channel_id: str) -> bool:
        """Join a voice channel"""
        
        if not self.config.enabled:
            return False
        
        try:
            # Get the channel
            # Note: This requires access to the Discord client/bot instance
            # In a real implementation, you'd inject the bot instance
            
            # For now, we'll store the intent to join and handle it in the presentation layer
            # This is a limitation of the clean architecture approach with Discord.py
            
            # Store that we want to be connected to this channel
            self._mark_as_connected(guild_id, channel_id)
            
            return True
            
        except Exception as e:
            print(f"❌ Error joining voice channel {channel_id} in guild {guild_id}: {e}")
            return False
    
    async def leave_voice_channel(self, guild_id: str) -> None:
        """Leave the current voice channel"""
        
        voice_client = self.voice_clients.get(guild_id)
        if voice_client and voice_client.is_connected():
            try:
                await voice_client.disconnect()
                del self.voice_clients[guild_id]
            except Exception as e:
                print(f"❌ Error leaving voice channel in guild {guild_id}: {e}")
    
    async def is_connected(self, guild_id: str) -> bool:
        """Check if connected to a voice channel in guild"""
        
        voice_client = self.voice_clients.get(guild_id)
        return voice_client is not None and voice_client.is_connected()
    
    async def get_supported_voices(self) -> List[str]:
        """Get list of available voice IDs"""
        
        # Return placeholder voice IDs
        # In a real implementation, this would query your TTS service
        return [
            "default",
            "male_narrator",
            "female_narrator", 
            "dwarf_gruff",
            "elf_elegant",
            "dragon_deep",
            "goblin_squeaky"
        ]
    
    def register_voice_client(self, guild_id: str, voice_client: discord.VoiceClient):
        """Register a voice client from the Discord bot"""
        self.voice_clients[guild_id] = voice_client
        
        # Initialize audio queue for this guild
        if guild_id not in self.audio_queue:
            self.audio_queue[guild_id] = asyncio.Queue()
    
    def unregister_voice_client(self, guild_id: str):
        """Unregister a voice client"""
        if guild_id in self.voice_clients:
            del self.voice_clients[guild_id]
        
        if guild_id in self.audio_queue:
            del self.audio_queue[guild_id]
    
    def _mark_as_connected(self, guild_id: str, channel_id: str):
        """Mark that we intend to be connected to a channel"""
        # This is a workaround for the clean architecture limitation
        # The presentation layer will need to handle the actual connection
        pass
    
    async def cleanup_cache(self):
        """Clean up old cached audio files"""
        
        try:
            cache_size = 0
            files_to_delete = []
            
            # Calculate current cache size
            for file_path in self.cache_dir.glob("*"):
                if file_path.is_file():
                    cache_size += file_path.stat().st_size
            
            # Convert to MB
            cache_size_mb = cache_size / (1024 * 1024)
            
            if cache_size_mb > self.config.max_cache_size_mb:
                # Delete oldest files first
                files = list(self.cache_dir.glob("*"))
                files.sort(key=lambda x: x.stat().st_mtime)
                
                for file_path in files:
                    if cache_size_mb <= self.config.max_cache_size_mb:
                        break
                    
                    file_size_mb = file_path.stat().st_size / (1024 * 1024)
                    file_path.unlink()
                    cache_size_mb -= file_size_mb
            
        except Exception as e:
            print(f"❌ Error cleaning up audio cache: {e}")


# TTS Integration Examples (commented out - choose one to implement)

class ElevenLabsTTSMixin:
    """Mixin for ElevenLabs TTS integration"""
    
    async def _elevenlabs_tts(self, text: str, voice_id: str = "default") -> bytes:
        """Generate speech using ElevenLabs API"""
        # Implementation would go here
        # import elevenlabs
        # audio = elevenlabs.generate(text=text, voice=voice_id)
        # return audio
        pass


class AzureTTSMixin:
    """Mixin for Azure Cognitive Services TTS"""
    
    async def _azure_tts(self, text: str, voice: str = "en-US-AriaNeural") -> bytes:
        """Generate speech using Azure TTS"""
        # Implementation would go here
        # import azure.cognitiveservices.speech as speechsdk
        pass


class GoogleTTSMixin:
    """Mixin for Google Cloud Text-to-Speech"""
    
    async def _google_tts(self, text: str, voice_name: str = "en-US-Wavenet-D") -> bytes:
        """Generate speech using Google Cloud TTS"""
        # Implementation would go here  
        # from google.cloud import texttospeech
        pass