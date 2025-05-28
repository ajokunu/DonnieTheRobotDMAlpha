# audio_system/voice_styles.py
import asyncio
import aiohttp
import io
from typing import Dict, Tuple, Optional

class VoiceStyleManager:
    """Manages different voice styles for Donnie"""
    
    def __init__(self):
        self.voice_styles = {
            "standard": {
                "speed": 1.25,
                "voice": "fable",
                "model": "tts-1-hd"
            },
            "excited": {
                "speed": 1.45,
                "voice": "fable", 
                "model": "tts-1-hd"
            },
            "dramatic": {
                "speed": 1.05,
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