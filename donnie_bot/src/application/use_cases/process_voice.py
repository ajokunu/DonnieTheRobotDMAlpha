"""
Voice processing use cases
"""
import logging
from typing import Optional

from ...domain.interfaces.voice_service import VoiceServiceInterface, VoiceConfig
from ...domain.interfaces.cache_service import CacheServiceInterface
from ..dto import VoiceCommand, VoiceResult

logger = logging.getLogger(__name__)


class ProcessVoiceUseCase:
    """Use case for voice-related operations"""
    
    def __init__(self,
                 voice_service: VoiceServiceInterface,
                 cache_service: Optional[CacheServiceInterface] = None):
        self.voice_service = voice_service
        self.cache_service = cache_service
    
    async def join_voice_channel(self, command: VoiceCommand) -> VoiceResult:
        """Join a voice channel"""
        try:
            logger.info(f"Joining voice channel {command.channel_id} in guild {command.guild_id}")
            
            if not command.channel_id:
                return VoiceResult.failure("Channel ID is required to join voice channel")
            
            # Check if already connected
            is_connected = await self.voice_service.is_connected(command.guild_id)
            if is_connected:
                return VoiceResult.connection_success(
                    is_connected=True,
                    message="Already connected to a voice channel in this server"
                )
            
            # Join the channel
            success = await self.voice_service.join_voice_channel(
                command.guild_id,
                command.channel_id
            )
            
            if success:
                logger.info(f"Successfully joined voice channel {command.channel_id}")
                return VoiceResult.connection_success(
                    is_connected=True,
                    message="🔊 Joined voice channel! Ready for audio responses."
                )
            else:
                return VoiceResult.failure("Failed to join voice channel")
            
        except Exception as e:
            logger.error(f"Error joining voice channel: {e}")
            return VoiceResult.failure(f"Failed to join voice: {str(e)}")
    
    async def leave_voice_channel(self, command: VoiceCommand) -> VoiceResult:
        """Leave the current voice channel"""
        try:
            logger.info(f"Leaving voice channel in guild {command.guild_id}")
            
            # Check if connected
            is_connected = await self.voice_service.is_connected(command.guild_id)
            if not is_connected:
                return VoiceResult.connection_success(
                    is_connected=False,
                    message="Not connected to any voice channel"
                )
            
            # Leave the channel
            await self.voice_service.leave_voice_channel(command.guild_id)
            
            logger.info(f"Successfully left voice channel")
            return VoiceResult.connection_success(
                is_connected=False,
                message="🔇 Left voice channel"
            )
            
        except Exception as e:
            logger.error(f"Error leaving voice channel: {e}")
            return VoiceResult.failure(f"Failed to leave voice: {str(e)}")
    
    async def speak_text(self, command: VoiceCommand) -> VoiceResult:
        """Convert text to speech and play in voice channel"""
        try:
            logger.info(f"Speaking text in guild {command.guild_id}: {command.text_to_speak[:50]}...")
            
            if not command.text_to_speak:
                return VoiceResult.failure("No text provided to speak")
            
            # Check if connected to voice
            is_connected = await self.voice_service.is_connected(command.guild_id)
            if not is_connected:
                return VoiceResult.failure("Not connected to a voice channel. Join one first!")
            
            # Limit text length for TTS
            max_length = 500
            text_to_speak = command.text_to_speak
            if len(text_to_speak) > max_length:
                text_to_speak = text_to_speak[:max_length] + "..."
                logger.warning(f"Truncated TTS text to {max_length} characters")
            
            # Use provided voice config or default
            voice_config = command.voice_config or VoiceConfig()
            
            # Generate TTS audio
            audio_data = await self.voice_service.text_to_speech(
                text=text_to_speak,
                config=voice_config
            )
            
            # Play audio in voice channel
            success = await self.voice_service.play_audio(command.guild_id, audio_data)
            
            if success:
                logger.info(f"Successfully played TTS audio")
                return VoiceResult.success_with_audio(
                    audio_data=audio_data,
                    message=f"🗣️ Spoke: {text_to_speak[:100]}{'...' if len(text_to_speak) > 100 else ''}"
                )
            else:
                return VoiceResult.failure("Failed to play audio in voice channel")
            
        except Exception as e:
            logger.error(f"Error speaking text: {e}")
            return VoiceResult.failure(f"Failed to speak: {str(e)}")
    
    async def get_voice_status(self, guild_id: str) -> VoiceResult:
        """Get current voice connection status"""
        try:
            logger.info(f"Getting voice status for guild {guild_id}")
            
            is_connected = await self.voice_service.is_connected(guild_id)
            
            if is_connected:
                message = "🔊 Connected to voice channel"
            else:
                message = "🔇 Not connected to voice channel"
            
            return VoiceResult.connection_success(
                is_connected=is_connected,
                message=message
            )
            
        except Exception as e:
            logger.error(f"Error getting voice status: {e}")
            return VoiceResult.failure(f"Failed to get voice status: {str(e)}")
    
    async def list_available_voices(self) -> VoiceResult:
        """Get list of available TTS voices"""
        try:
            logger.info("Getting available voices")
            
            voices = await self.voice_service.get_supported_voices()
            
            voices_text = "🎭 **Available Voices:**\n" + "\n".join([f"• {voice}" for voice in voices])
            
            return VoiceResult(
                success=True,
                message=voices_text,
                metadata={"voices": voices}
            )
            
        except Exception as e:
            logger.error(f"Error getting available voices: {e}")
            return VoiceResult.failure(f"Failed to get voices: {str(e)}")
    
    async def change_voice_settings(self, command: VoiceCommand) -> VoiceResult:
        """Change voice settings for future TTS"""
        try:
            logger.info(f"Changing voice settings in guild {command.guild_id}")
            
            if not command.voice_config:
                return VoiceResult.failure("No voice configuration provided")
            
            # In a real implementation, you might save these settings per-guild
            # For now, we'll just acknowledge the change
            
            settings_text = f"🎛️ **Voice Settings Updated:**\n"
            settings_text += f"• Voice: {command.voice_config.voice_id}\n"
            settings_text += f"• Speed: {command.voice_config.speed}x\n"
            settings_text += f"• Pitch: {command.voice_config.pitch}\n"
            settings_text += f"• Volume: {command.voice_config.volume}"
            
            return VoiceResult(
                success=True,
                message=settings_text,
                metadata={"voice_config": command.voice_config.__dict__}
            )
            
        except Exception as e:
            logger.error(f"Error changing voice settings: {e}")
            return VoiceResult.failure(f"Failed to change settings: {str(e)}")