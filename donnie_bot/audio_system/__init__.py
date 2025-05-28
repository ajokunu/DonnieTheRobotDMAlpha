# audio_system/__init__.py
"""
Audio System Module for Enhanced Donnie Voice
"""

from .enhanced_voice_manager import EnhancedVoiceManager
from .sound_effects import SoundEffectManager
from .voice_styles import VoiceStyleManager
from .response_analyzer import ResponseAnalyzer
from .parallel_processor import ParallelResponseProcessor

__all__ = [
    'EnhancedVoiceManager',
    'SoundEffectManager', 
    'VoiceStyleManager',
    'ResponseAnalyzer',
    'ParallelResponseProcessor'
]