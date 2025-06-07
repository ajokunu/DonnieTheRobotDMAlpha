# memory_validator.py - SAFE VERSION
from typing import List, Dict, Any
import re

class MemoryValidator:
    """Validates campaign memories while allowing D&D content"""
    
    def __init__(self):
        # Patterns that suggest false campaign memories
        self.suspicious_patterns = [
            r"remember when (you|we)",
            r"(you|we) already (fought|met|visited)",
            r"last session (you|we)",
            r"earlier (you|we) (defeated|encountered)",
            r"(you|we) previously"
        ]
        
        self.compiled_patterns = []
        for pattern in self.suspicious_patterns:
            try:
                self.compiled_patterns.append(re.compile(pattern, re.IGNORECASE))
            except re.error as e:
                print(f"⚠️ Invalid regex pattern: {pattern} - {e}")
    
    def validate_campaign_memory(self, memory) -> bool:
        """Check if campaign memory seems reliable"""
        try:
            summary = getattr(memory, 'summary', '')
            importance = getattr(memory, 'importance_score', 0.0)
            
            if not summary or len(summary.strip()) < 10:
                return False
            
            if importance < 0.6:
                return False
            
            # Check for suspicious patterns
            summary_lower = summary.lower()
            for pattern in self.compiled_patterns:
                if pattern.search(summary_lower):
                    print(f"⚠️ Rejected suspicious memory: {summary[:50]}...")
                    return False
            
            return True
            
        except Exception as e:
            print(f"⚠️ Memory validation error: {e}")
            return False
    
    def filter_reliable_memories(self, memories: List) -> List:
        """Filter memories to only include reliable ones"""
        if not memories:
            return []
        
        reliable = []
        for memory in memories:
            if self.validate_campaign_memory(memory):
                reliable.append(memory)
        
        print(f"📊 Memory filter: {len(memories)} → {len(reliable)} reliable")
        return reliable