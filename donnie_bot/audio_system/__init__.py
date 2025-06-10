# audio_system/__init__.py
"""
Audio System Module for Enhanced Donnie Voice
"""

from .sound_effects import SoundEffectManager
from .voice_styles import VoiceStyleManager
from .response_analyzer import ResponseAnalyzer
from .parallel_processor import ParallelResponseProcessor

__all__ = [
    'SoundEffectManager', 
    'VoiceStyleManager',
    'ResponseAnalyzer',
    'ParallelResponseProcessor'
]