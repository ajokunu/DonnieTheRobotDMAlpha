# audio_system/response_analyzer.py
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