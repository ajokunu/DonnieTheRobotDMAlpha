"""
Character snapshot utilities for tracking character state changes
"""
from datetime import datetime
from typing import Dict, Any, Optional

class CharacterSnapshotManager:
    """Manages character state snapshots"""
    
    def __init__(self):
        pass
    
    def create_snapshot(self, character_data: Dict[str, Any], 
                       snapshot_type: str = "manual",
                       notes: Optional[str] = None) -> Dict[str, Any]:
        """Create a character snapshot"""
        snapshot = {
            "timestamp": datetime.utcnow(),
            "snapshot_type": snapshot_type,
            "character_state": character_data.copy(),
            "notes": notes or "",
            "version": "1.0"
        }
        
        return snapshot
    
    def compare_snapshots(self, old_snapshot: Dict[str, Any], 
                         new_snapshot: Dict[str, Any]) -> Dict[str, Any]:
        """Compare two character snapshots and return differences"""
        differences = {}
        
        old_char = old_snapshot.get("character_state", {})
        new_char = new_snapshot.get("character_state", {})
        
        # Compare key character attributes
        comparable_fields = [
            "level", "stats", "equipment", "spells", 
            "affiliations", "personality", "current_hp", "max_hp"
        ]
        
        for field in comparable_fields:
            old_value = old_char.get(field)
            new_value = new_char.get(field)
            
            if old_value != new_value:
                differences[field] = {
                    "old": old_value,
                    "new": new_value,
                    "changed": True
                }
        
        return differences
    
    def generate_progression_summary(self, snapshots: list) -> str:
        """Generate a text summary of character progression from snapshots"""
        if not snapshots:
            return "No progression data available"
        
        if len(snapshots) == 1:
            char_data = snapshots[0].get("character_state", {})
            return f"Character created at level {char_data.get('level', 1)}"
        
        # Compare first and last snapshots
        first_snapshot = snapshots[0]
        last_snapshot = snapshots[-1]
        
        differences = self.compare_snapshots(first_snapshot, last_snapshot)
        
        summary_parts = []
        
        if "level" in differences:
            old_level = differences["level"]["old"]
            new_level = differences["level"]["new"]
            summary_parts.append(f"Advanced from level {old_level} to {new_level}")
        
        if "equipment" in differences:
            summary_parts.append("Equipment has been updated")
        
        if "spells" in differences:
            summary_parts.append("Spells have changed")
        
        if not summary_parts:
            summary_parts.append("Character state maintained")
        
        return ". ".join(summary_parts) + "."
    
    def validate_snapshot(self, snapshot: Dict[str, Any]) -> tuple[bool, str]:
        """Validate that a snapshot has required fields"""
        required_fields = ["timestamp", "snapshot_type", "character_state"]
        
        for field in required_fields:
            if field not in snapshot:
                return False, f"Missing required field: {field}"
        
        character_state = snapshot.get("character_state", {})
        if not isinstance(character_state, dict):
            return False, "Character state must be a dictionary"
        
        return True, "Valid snapshot"