# combat_manager.py
"""
DM Donnie Combat Manager - Core State Management (CORRECTED VERSION)
Tracks combat state from DM responses without interfering with narrative
REMOVED: Auto scene changes, auto enemy generation, battlefield extraction
KEPT: Initiative, HP, positions, conditions tracking
"""

import re
from typing import Dict, List, Optional
from dataclasses import dataclass, field
from enum import Enum
import time

class CombatPhase(Enum):
    SETUP = "setup"
    ACTIVE = "active"
    ENDED = "ended"

@dataclass
class Combatant:
    """Minimal combatant info for speed"""
    id: str
    name: str
    is_player: bool = False
    current_hp: Optional[int] = None
    max_hp: Optional[int] = None
    initiative: Optional[int] = None
    conditions: List[str] = field(default_factory=list)
    position: Optional[str] = None

class CombatManager:
    """Combat state manager WITHOUT narrative interference"""
    
    def __init__(self, channel_id: int):
        self.channel_id = channel_id
        self.phase = CombatPhase.SETUP
        self.round_number = 0
        self.turn_index = 0
        
        # State tracking ONLY
        self.combatants: Dict[str, Combatant] = {}
        self.initiative_order: List[str] = []
        self.last_dm_response = ""
        
        # Pre-compiled regex for speed
        self._hp_pattern = re.compile(r'(\w+)[^\d]*(\d+)[^\d]*(?:hp|hit points?)', re.IGNORECASE)
        self._initiative_pattern = re.compile(r'(\w+)[^\d]*initiative[^\d]*(\d+)', re.IGNORECASE)
        self._round_pattern = re.compile(r'round\s*(\d+)', re.IGNORECASE)
        self._position_pattern = re.compile(r'(\w+).*?(\d+)\s*(?:feet?|ft\.?)', re.IGNORECASE)
        
        # Performance tracking
        self._processing_times = []
    
    def quick_parse_dm_response(self, dm_response: str) -> bool:
        """Fast parsing - extract critical info, return if combat detected"""
        start_time = time.time()
        
        self.last_dm_response = dm_response
        response_lower = dm_response.lower()
        
        # Quick combat detection
        combat_detected = any(word in response_lower for word in [
            'initiative', 'combat', 'attack', 'round', 'turn', 'damage', 'hp', 'roll'
        ])
        
        if not combat_detected:
            return False
        
        # Parse based on phase
        if self.phase == CombatPhase.SETUP:
            if 'initiative' in response_lower or 'combat begins' in response_lower:
                self.phase = CombatPhase.ACTIVE
                self.round_number = 1
        
        elif self.phase == CombatPhase.ACTIVE:
            self._update_hp(dm_response)
            self._update_positions(dm_response)
            self._update_conditions(dm_response)
            
            # Check for round changes
            round_match = self._round_pattern.search(dm_response)
            if round_match:
                self.round_number = int(round_match.group(1))
        
        # Performance monitoring
        elapsed = time.time() - start_time
        self._processing_times.append(elapsed)
        if elapsed > 0.1:
            print(f"⚠️ Slow combat parsing: {elapsed:.3f}s")
        
        return True
    
    def _update_hp(self, text: str):
        """Fast HP extraction"""
        hp_matches = self._hp_pattern.findall(text)
        
        for name, hp_str in hp_matches:
            try:
                hp = int(hp_str)
                for combatant in self.combatants.values():
                    if name.lower() in combatant.name.lower() or combatant.name.lower() in name.lower():
                        combatant.current_hp = hp
                        if combatant.max_hp is None:
                            combatant.max_hp = hp
                        break
            except ValueError:
                continue
    
    def _update_positions(self, text: str):
        """Extract position information"""
        response_lower = text.lower()
        
        # Look for distance mentions
        matches = self._position_pattern.findall(response_lower)
        for name, distance in matches:
            for combatant in self.combatants.values():
                if name.lower() in combatant.name.lower() or combatant.name.lower() in name.lower():
                    combatant.position = f"{distance}ft"
                    break
        
        # Look for descriptive positions
        position_descriptions = [
            ("behind cover", "cover"),
            ("in melee", "melee"),
            ("at range", "ranged"),
            ("prone", "prone"),
            ("standing", "standing"),
            ("crouched", "crouched"),
            ("elevated", "elevated"),
            ("high ground", "high ground"),
            ("low ground", "low ground")
        ]
        
        for full_desc, short_desc in position_descriptions:
            if full_desc in response_lower:
                pattern = rf"(\w+).*?{re.escape(full_desc)}"
                match = re.search(pattern, response_lower)
                if match:
                    name = match.group(1)
                    for combatant in self.combatants.values():
                        if name.lower() in combatant.name.lower() or combatant.name.lower() in name.lower():
                            combatant.position = short_desc
                            break
    
    def _update_conditions(self, text: str):
        """Extract condition information"""
        conditions = [
            "poisoned", "charmed", "frightened", "paralyzed", "stunned",
            "prone", "restrained", "grappled", "blinded", "deafened",
            "exhausted", "incapacitated", "unconscious"
        ]
        
        response_lower = text.lower()
        
        for condition in conditions:
            if condition in response_lower:
                pattern = rf"(\w+).*?{re.escape(condition)}"
                match = re.search(pattern, response_lower)
                if match:
                    name = match.group(1)
                    for combatant in self.combatants.values():
                        if name.lower() in combatant.name.lower() or combatant.name.lower() in name.lower():
                            if condition not in combatant.conditions:
                                combatant.conditions.append(condition)
                            break
    
    def add_player(self, user_id: str, name: str, initiative: int):
        """Add player combatant"""
        self.combatants[user_id] = Combatant(
            id=user_id,
            name=name,
            is_player=True,
            initiative=initiative
        )
        self._rebuild_initiative_order()
    
    def add_enemy_manually(self, enemy_name: str, initiative: int, hp: Optional[int] = None):
        """Manually add enemy (DM controlled)"""
        enemy_id = f"enemy_{len([c for c in self.combatants.values() if not c.is_player])}"
        self.combatants[enemy_id] = Combatant(
            id=enemy_id,
            name=enemy_name,
            is_player=False,
            initiative=initiative,
            current_hp=hp,
            max_hp=hp
        )
        self._rebuild_initiative_order()
        print(f"✅ Enemy added manually: {enemy_name} (Init: {initiative})")
    
    def _rebuild_initiative_order(self):
        """Sort by initiative"""
        combatants_with_init = [
            (id, c.initiative or 0) for id, c in self.combatants.items() 
            if c.initiative is not None
        ]
        combatants_with_init.sort(key=lambda x: x[1], reverse=True)
        self.initiative_order = [id for id, _ in combatants_with_init]
    
    def get_current_combatant(self) -> Optional[Combatant]:
        """Get current turn combatant"""
        if not self.initiative_order or self.turn_index >= len(self.initiative_order):
            return None
        return self.combatants.get(self.initiative_order[self.turn_index])
    
    def advance_turn(self):
        """Advance to next turn"""
        self.turn_index += 1
        if self.turn_index >= len(self.initiative_order):
            self.turn_index = 0
            self.round_number += 1
    
    def get_minimal_context(self) -> str:
        """Generate minimal context for DM (under 200 chars)"""
        if self.phase != CombatPhase.ACTIVE or not self.initiative_order:
            return ""
        
        current = self.get_current_combatant()
        if not current:
            return ""
        
        context_parts = [f"Round {self.round_number} - {current.name}'s turn"]
        
        if len(self.combatants) <= 4:
            alive_combatants = []
            for id in self.initiative_order:
                c = self.combatants[id]
                if c.current_hp is None or c.current_hp > 0:
                    hp_info = f"({c.current_hp}hp)" if c.current_hp else ""
                    alive_combatants.append(f"{c.name}{hp_info}")
            
            if alive_combatants:
                context_parts.append(f"Active: {', '.join(alive_combatants)}")
        
        result = " | ".join(context_parts)
        return result[:200]
    
    def is_active(self) -> bool:
        """Check if combat is active"""
        return self.phase == CombatPhase.ACTIVE
    
    # === COMPATIBILITY METHODS FOR COMBAT_INTEGRATION ===
    
    def is_combat_active(self) -> bool:
        """Alias for is_active()"""
        return self.is_active()
    
    def get_round_number(self) -> int:
        """Get current round number"""
        return self.round_number
    
    def get_current_turn(self) -> Optional[str]:
        """Get current turn character name"""
        current = self.get_current_combatant()
        return current.name if current else None
    
    def get_character_status(self, character_name: str) -> List[str]:
        """Get status effects for character"""
        for combatant in self.combatants.values():
            if combatant.name.lower() == character_name.lower():
                status_effects = []
                
                if combatant.conditions:
                    status_effects.extend(combatant.conditions)
                
                if combatant.position:
                    status_effects.append(combatant.position)
                
                if combatant.current_hp is not None and combatant.max_hp is not None:
                    hp_percent = combatant.current_hp / combatant.max_hp
                    if hp_percent <= 0.25:
                        status_effects.append("critically wounded")
                    elif hp_percent <= 0.5:
                        status_effects.append("bloodied")
                
                return status_effects
        
        return []
    
    def start_combat(self):
        """Start combat"""
        if self.phase == CombatPhase.SETUP:
            self.phase = CombatPhase.ACTIVE
            if self.round_number == 0:
                self.round_number = 1
            print(f"🎯 Combat started in channel {self.channel_id}")
    
    def end_combat(self):
        """End combat"""
        self.phase = CombatPhase.ENDED
        return {"rounds": self.round_number, "combatants": len(self.combatants)}