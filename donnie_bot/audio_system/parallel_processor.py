# audio_system/parallel_processor.py
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