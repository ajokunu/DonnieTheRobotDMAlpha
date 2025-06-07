"""
DM Donnie Combat Manager - CORRECTED Core State Management
FIXED: Phase transitions, initiative ordering, character data access, error handling
"""

import re
from typing import Dict, List, Optional
from dataclasses import dataclass, field
from enum import Enum
import time
import asyncio

class CombatPhase(Enum):
    SETUP = "setup"
    ACTIVE = "active"
    ENDED = "ended"

@dataclass
class Combatant:
    """Enhanced combatant info with better defaults"""
    id: str
    name: str
    is_player: bool = False
    current_hp: Optional[int] = None
    max_hp: Optional[int] = None
    initiative: Optional[int] = None
    conditions: List[str] = field(default_factory=list)
    position: Optional[str] = None
    
    def __post_init__(self):
        """Ensure conditions is always a list"""
        if self.conditions is None:
            self.conditions = []

class CombatManager:
    """FIXED Combat state manager with proper error handling"""
    
    def __init__(self, channel_id: int):
        self.channel_id = channel_id
        self.phase = CombatPhase.SETUP
        self.round_number = 0
        self.turn_index = 0
        
        # State tracking ONLY
        self.combatants: Dict[str, Combatant] = {}
        self.initiative_order: List[str] = []
        self.last_dm_response = ""
        
        # FIXED: Pre-compiled regex for speed with error handling
        try:
            self._hp_pattern = re.compile(r'(\w+)[^\d]*(\d+)[^\d]*(?:hp|hit points?)', re.IGNORECASE)
            self._initiative_pattern = re.compile(r'(\w+)[^\d]*initiative[^\d]*(\d+)', re.IGNORECASE)
            self._round_pattern = re.compile(r'round\s*(\d+)', re.IGNORECASE)
            self._position_pattern = re.compile(r'(\w+).*?(\d+)\s*(?:feet?|ft\.?)', re.IGNORECASE)
        except Exception as e:
            print(f"⚠️ Regex compilation error: {e}")
            # Fallback to simple patterns
            self._hp_pattern = re.compile(r'(\w+)\s*(\d+)\s*hp', re.IGNORECASE)
            self._initiative_pattern = re.compile(r'(\w+)\s*(\d+)', re.IGNORECASE)
            self._round_pattern = re.compile(r'round\s*(\d+)', re.IGNORECASE)
            self._position_pattern = re.compile(r'(\w+)\s*(\d+)\s*ft', re.IGNORECASE)
        
        # Performance tracking
        self._processing_times = []
        
        print(f"✅ Combat Manager initialized for channel {channel_id}")
    
    def add_player(self, user_id: str, name: str, initiative: int):
        """FIXED: Add player combatant with proper validation"""
        try:
            if not user_id or not name:
                print(f"❌ Invalid player data: user_id={user_id}, name={name}")
                return False
            
            if not isinstance(initiative, int):
                try:
                    initiative = int(initiative)
                except (ValueError, TypeError):
                    print(f"❌ Invalid initiative value: {initiative}")
                    return False
            
            # Create combatant
            self.combatants[user_id] = Combatant(
                id=user_id,
                name=name,
                is_player=True,
                initiative=initiative
            )
            
            print(f"✅ Added player {name} with initiative {initiative}")
            
            # Rebuild initiative order
            self._rebuild_initiative_order()
            
            # FIXED: Auto-start combat if we have players
            if self.phase == CombatPhase.SETUP and len(self.combatants) > 0:
                self._try_start_combat()
            
            return True
            
        except Exception as e:
            print(f"❌ Error adding player to combat: {e}")
            return False
    
    def add_enemy_manually(self, enemy_name: str, initiative: int, hp: Optional[int] = None):
        """FIXED: Manually add enemy with proper validation"""
        try:
            if not enemy_name:
                print(f"❌ Invalid enemy name: {enemy_name}")
                return False
            
            if not isinstance(initiative, int):
                try:
                    initiative = int(initiative)
                except (ValueError, TypeError):
                    print(f"❌ Invalid initiative value: {initiative}")
                    return False
            
            # Generate unique enemy ID
            enemy_id = f"enemy_{enemy_name.lower().replace(' ', '_')}_{len([c for c in self.combatants.values() if not c.is_player])}"
            
            self.combatants[enemy_id] = Combatant(
                id=enemy_id,
                name=enemy_name,
                is_player=False,
                initiative=initiative,
                current_hp=hp,
                max_hp=hp
            )
            
            print(f"✅ Enemy added: {enemy_name} (Init: {initiative}, HP: {hp})")
            
            # Rebuild initiative order
            self._rebuild_initiative_order()
            
            # Auto-start combat if we have combatants
            if self.phase == CombatPhase.SETUP and len(self.combatants) > 0:
                self._try_start_combat()
            
            return True
            
        except Exception as e:
            print(f"❌ Error adding enemy to combat: {e}")
            return False
    
    def _try_start_combat(self):
        """FIXED: Try to start combat if conditions are met"""
        try:
            if self.phase == CombatPhase.SETUP and len(self.combatants) > 0:
                # Check if we have at least one combatant with initiative
                combatants_with_init = [c for c in self.combatants.values() if c.initiative is not None]
                
                if len(combatants_with_init) > 0:
                    self.phase = CombatPhase.ACTIVE
                    self.round_number = 1
                    self.turn_index = 0
                    print(f"✅ Combat started! {len(combatants_with_init)} combatants ready")
                    return True
                else:
                    print(f"⚠️ Cannot start combat: no combatants have initiative")
                    return False
            
            return False
            
        except Exception as e:
            print(f"❌ Error starting combat: {e}")
            return False
    
    def _rebuild_initiative_order(self):
        """FIXED: Sort by initiative with proper error handling"""
        try:
            # Get all combatants with valid initiative
            combatants_with_init = []
            for combatant_id, combatant in self.combatants.items():
                if combatant.initiative is not None:
                    try:
                        init_value = int(combatant.initiative)
                        combatants_with_init.append((combatant_id, init_value))
                    except (ValueError, TypeError):
                        print(f"⚠️ Invalid initiative for {combatant.name}: {combatant.initiative}")
                        continue
            
            # Sort by initiative (highest first)
            combatants_with_init.sort(key=lambda x: x[1], reverse=True)
            
            # Update initiative order
            self.initiative_order = [combatant_id for combatant_id, _ in combatants_with_init]
            
            print(f"✅ Initiative order rebuilt: {len(self.initiative_order)} combatants")
            
            # Log the order for debugging
            for i, combatant_id in enumerate(self.initiative_order):
                combatant = self.combatants.get(combatant_id)
                if combatant:
                    print(f"  {i+1}. {combatant.name} (Init: {combatant.initiative})")
            
        except Exception as e:
            print(f"❌ Error rebuilding initiative order: {e}")
            self.initiative_order = []
    
    def get_current_combatant(self) -> Optional[Combatant]:
        """FIXED: Get current turn combatant with bounds checking"""
        try:
            if not self.initiative_order:
                return None
            
            if self.turn_index < 0 or self.turn_index >= len(self.initiative_order):
                print(f"⚠️ Invalid turn index: {self.turn_index} (max: {len(self.initiative_order)-1})")
                self.turn_index = 0  # Reset to start
                
            if self.turn_index < len(self.initiative_order):
                combatant_id = self.initiative_order[self.turn_index]
                return self.combatants.get(combatant_id)
            
            return None
            
        except Exception as e:
            print(f"❌ Error getting current combatant: {e}")
            return None
    
    def advance_turn(self):
        """FIXED: Advance to next turn with proper bounds checking"""
        try:
            if not self.initiative_order:
                print("⚠️ Cannot advance turn: no initiative order")
                return False
            
            self.turn_index += 1
            
            if self.turn_index >= len(self.initiative_order):
                self.turn_index = 0
                self.round_number += 1
                print(f"✅ New round: {self.round_number}")
            
            current = self.get_current_combatant()
            if current:
                print(f"✅ Turn advanced to: {current.name}")
            
            return True
            
        except Exception as e:
            print(f"❌ Error advancing turn: {e}")
            return False
    
    def quick_parse_dm_response(self, dm_response: str) -> bool:
        """FIXED: Fast parsing with better error handling"""
        start_time = time.time()
        
        try:
            self.last_dm_response = dm_response
            response_lower = dm_response.lower()
            
            # Quick combat detection
            combat_keywords = ['initiative', 'combat', 'attack', 'round', 'turn', 'damage', 'hp', 'roll']
            combat_detected = any(word in response_lower for word in combat_keywords)
            
            if not combat_detected:
                return False
            
            # Parse based on phase
            if self.phase == CombatPhase.SETUP:
                if 'initiative' in response_lower or 'combat begins' in response_lower:
                    if self._try_start_combat():
                        print("✅ Combat auto-started from DM response")
            
            elif self.phase == CombatPhase.ACTIVE:
                self._update_hp(dm_response)
                self._update_positions(dm_response)
                self._update_conditions(dm_response)
                
                # Check for round changes
                try:
                    round_match = self._round_pattern.search(dm_response)
                    if round_match:
                        new_round = int(round_match.group(1))
                        if new_round > self.round_number:
                            self.round_number = new_round
                            print(f"✅ Round updated to: {new_round}")
                except Exception as e:
                    print(f"⚠️ Error parsing round: {e}")
            
            # Performance monitoring
            elapsed = time.time() - start_time
            self._processing_times.append(elapsed)
            if elapsed > 0.1:
                print(f"⚠️ Slow combat parsing: {elapsed:.3f}s")
            
            return True
            
        except Exception as e:
            print(f"❌ Error in quick_parse_dm_response: {e}")
            return False
    
    def _update_hp(self, text: str):
        """FIXED: HP extraction with better error handling"""
        try:
            hp_matches = self._hp_pattern.findall(text)
            
            for name, hp_str in hp_matches:
                try:
                    hp = int(hp_str)
                    updated = False
                    
                    for combatant in self.combatants.values():
                        # Better name matching
                        if (name.lower() in combatant.name.lower() or 
                            combatant.name.lower() in name.lower() or
                            name.lower() == combatant.name.lower()):
                            
                            combatant.current_hp = hp
                            if combatant.max_hp is None:
                                combatant.max_hp = hp
                            updated = True
                            print(f"✅ Updated {combatant.name} HP: {hp}")
                            break
                    
                    if not updated:
                        print(f"⚠️ Could not match HP update for: {name}")
                        
                except ValueError:
                    print(f"⚠️ Invalid HP value: {hp_str}")
                    continue
                    
        except Exception as e:
            print(f"❌ Error updating HP: {e}")
    
    def _update_positions(self, text: str):
        """Extract position information with error handling"""
        try:
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
                                
        except Exception as e:
            print(f"❌ Error updating positions: {e}")
    
    def _update_conditions(self, text: str):
        """Extract condition information with error handling"""
        try:
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
                                    print(f"✅ Added condition {condition} to {combatant.name}")
                                break
                                
        except Exception as e:
            print(f"❌ Error updating conditions: {e}")
    
    def get_minimal_context(self) -> str:
        """FIXED: Generate minimal context with error handling"""
        try:
            if self.phase != CombatPhase.ACTIVE or not self.initiative_order:
                return ""
            
            current = self.get_current_combatant()
            if not current:
                return ""
            
            context_parts = [f"Round {self.round_number} - {current.name}'s turn"]
            
            if len(self.combatants) <= 4:
                alive_combatants = []
                for combatant_id in self.initiative_order:
                    combatant = self.combatants.get(combatant_id)
                    if combatant and (combatant.current_hp is None or combatant.current_hp > 0):
                        hp_info = f"({combatant.current_hp}hp)" if combatant.current_hp else ""
                        alive_combatants.append(f"{combatant.name}{hp_info}")
                
                if alive_combatants:
                    context_parts.append(f"Active: {', '.join(alive_combatants)}")
            
            result = " | ".join(context_parts)
            return result[:200]
            
        except Exception as e:
            print(f"❌ Error generating minimal context: {e}")
            return ""
    
    def is_active(self) -> bool:
        """Check if combat is active"""
        return self.phase == CombatPhase.ACTIVE
    
    def start_combat(self):
        """FIXED: Manually start combat with validation"""
        try:
            if self.phase == CombatPhase.SETUP:
                if len(self.combatants) > 0:
                    success = self._try_start_combat()
                    if success:
                        print(f"🎯 Combat manually started in channel {self.channel_id}")
                        return True
                    else:
                        print(f"⚠️ Cannot start combat: insufficient combatants or missing initiative")
                        return False
                else:
                    print(f"⚠️ Cannot start combat: no combatants")
                    return False
            else:
                print(f"⚠️ Combat already in phase: {self.phase}")
                return False
                
        except Exception as e:
            print(f"❌ Error starting combat: {e}")
            return False
    
    def end_combat(self):
        """FIXED: End combat with proper cleanup"""
        try:
            if self.phase == CombatPhase.ACTIVE:
                self.phase = CombatPhase.ENDED
                result = {
                    "rounds": self.round_number, 
                    "combatants": len(self.combatants),
                    "channel_id": self.channel_id
                }
                print(f"✅ Combat ended in channel {self.channel_id} after {self.round_number} rounds")
                return result
            else:
                print(f"⚠️ No active combat to end in channel {self.channel_id}")
                return None
                
        except Exception as e:
            print(f"❌ Error ending combat: {e}")
            return None
    
    def get_combat_status(self) -> Dict:
        """Get comprehensive combat status for debugging"""
        try:
            return {
                "channel_id": self.channel_id,
                "phase": self.phase.value,
                "round_number": self.round_number,
                "turn_index": self.turn_index,
                "combatants_count": len(self.combatants),
                "initiative_order_count": len(self.initiative_order),
                "current_combatant": self.get_current_combatant().name if self.get_current_combatant() else None,
                "combatants": {
                    cid: {
                        "name": c.name,
                        "initiative": c.initiative,
                        "is_player": c.is_player,
                        "hp": f"{c.current_hp}/{c.max_hp}" if c.current_hp is not None else "Unknown"
                    }
                    for cid, c in self.combatants.items()
                }
            }
        except Exception as e:
            print(f"❌ Error getting combat status: {e}")
            return {"error": str(e)}
    
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
        try:
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
            
        except Exception as e:
            print(f"❌ Error getting character status: {e}")
            return []