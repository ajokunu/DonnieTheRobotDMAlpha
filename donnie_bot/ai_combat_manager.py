# donnie_bot/ai_combat_manager.py
import json
import asyncio
import random
from typing import Dict, List, Optional, Tuple
import re

class AICombatManager:
    """Bridge between AI narrative and existing combat system"""
    
    def __init__(self, claude_client, campaign_context):
        self.claude_client = claude_client
        self.campaign_context = campaign_context
        
        # Combat trigger patterns
        self.combat_triggers = [
            r'\battack\b', r'\bfight\b', r'\bcombat\b', r'\binitiative\b',
            r'\bdraws? (?:weapon|sword|bow)\b', r'\bcasts? spell\b',
            r'\bhostile\b', r'\bambush\b', r'\broll for initiative\b',
            r'\benters? combat\b', r'\bbattle begins?\b', r'\bfight breaks? out\b'
        ]
        self.compiled_triggers = [re.compile(pattern, re.IGNORECASE) for pattern in self.combat_triggers]
        
        # Storm King's Thunder appropriate monsters by level
        self.skt_monsters_by_level = {
            1: [
                {"name": "Goblin Scout", "hp": 7, "base_init": 14, "cr": "1/4"},
                {"name": "Bandit", "hp": 11, "base_init": 12, "cr": "1/8"},
                {"name": "Dire Wolf", "hp": 37, "base_init": 14, "cr": "1"},
            ],
            2: [
                {"name": "Orc Warrior", "hp": 15, "base_init": 12, "cr": "1/2"},
                {"name": "Hobgoblin", "hp": 11, "base_init": 12, "cr": "1/2"},
                {"name": "Brown Bear", "hp": 34, "base_init": 10, "cr": "1"},
            ],
            3: [
                {"name": "Ogre", "hp": 59, "base_init": 8, "cr": "2"},
                {"name": "Owlbear", "hp": 59, "base_init": 13, "cr": "3"},
                {"name": "Hill Giant", "hp": 105, "base_init": 8, "cr": "5"},
            ],
            4: [
                {"name": "Stone Giant", "hp": 126, "base_init": 14, "cr": "7"},
                {"name": "Frost Giant", "hp": 138, "base_init": 9, "cr": "8"},
                {"name": "Fire Giant", "hp": 162, "base_init": 9, "cr": "9"},
            ],
            5: [
                {"name": "Cloud Giant", "hp": 200, "base_init": 12, "cr": "9"},
                {"name": "Storm Giant", "hp": 230, "base_init": 14, "cr": "13"},
                {"name": "Young Dragon", "hp": 178, "base_init": 14, "cr": "10"},
            ]
        }
        
        print("✅ AI Combat Manager initialized")
    
    def detect_combat_trigger(self, player_input: str, dm_response: str) -> bool:
        """Detect if combat should start based on text analysis"""
        try:
            combined_text = f"{player_input} {dm_response}"
            
            # Check for explicit combat triggers
            for pattern in self.compiled_triggers:
                if pattern.search(combined_text):
                    print(f"🎯 Combat trigger detected: {pattern.pattern}")
                    return True
            
            # Check for aggressive actions
            aggressive_words = ['kill', 'destroy', 'smash', 'charge', 'strike', 'slash', 'stab']
            if any(word in combined_text.lower() for word in aggressive_words):
                print("🎯 Combat trigger detected: aggressive action")
                return True
                
            return False
            
        except Exception as e:
            print(f"⚠️ Combat detection error: {e}")
            return False
    
    async def generate_context_appropriate_monsters(self, narrative_context: str, 
                                                   party_level: int, 
                                                   party_size: int = 1) -> Dict:
        """Generate monsters using AI based on narrative context"""
        
        try:
            # Get level-appropriate monsters for fallback
            fallback_monsters = self._get_fallback_monsters(party_level, party_size)
            
            prompt = f"""You are creating a D&D 5e encounter for Storm King's Thunder campaign.

NARRATIVE CONTEXT: {narrative_context[:400]}
PARTY LEVEL: {party_level}
PARTY SIZE: {party_size}

AVAILABLE MONSTERS for this level:
{self._format_available_monsters(party_level)}

Create 1-{min(party_size + 1, 3)} monsters that:
1. Make narrative sense in this context
2. Are appropriate difficulty for party level {party_level}
3. Fit Storm King's Thunder theme (giants, bandits, wild creatures)

Return ONLY this JSON format:
{{
    "monsters": [
        {{
            "name": "Goblin Scout",
            "initiative": 14,
            "hp": 7,
            "reason": "Why this monster appears here"
        }}
    ],
    "encounter_description": "One sentence describing how combat starts"
}}

Choose monsters that make SENSE in this specific situation. No random dragons in taverns!"""

            # Call Claude with timeout
            response = await asyncio.wait_for(
                asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: self.claude_client.messages.create(
                        model="claude-sonnet-4-20250514",
                        max_tokens=300,
                        temperature=0.7,  # Some creativity but not too much
                        messages=[{"role": "user", "content": prompt}]
                    )
                ),
                timeout=5.0
            )
            
            # Parse response
            response_text = response.content[0].text.strip()
            monsters_data = self._extract_json_from_response(response_text)
            
            if monsters_data and self._validate_monsters_data(monsters_data):
                print(f"✅ AI generated {len(monsters_data['monsters'])} monsters")
                return monsters_data
            else:
                print("⚠️ AI response invalid, using fallback")
                return fallback_monsters
                
        except asyncio.TimeoutError:
            print("⚠️ AI monster generation timeout, using fallback")
            return fallback_monsters
        except Exception as e:
            print(f"⚠️ AI monster generation error: {e}")
            return fallback_monsters
    
    def _get_fallback_monsters(self, party_level: int, party_size: int) -> Dict:
        """Get appropriate fallback monsters when AI fails"""
        
        # Clamp level to available ranges
        level_key = min(max(party_level, 1), 5)
        available_monsters = self.skt_monsters_by_level[level_key]
        
        # Select 1-2 monsters based on party size
        num_monsters = 1 if party_size <= 2 else min(2, party_size - 1)
        selected_monsters = random.sample(available_monsters, min(num_monsters, len(available_monsters)))
        
        monsters = []
        for monster in selected_monsters:
            # Add some initiative variance
            init_roll = random.randint(1, 20) + (monster["base_init"] - 10)
            monsters.append({
                "name": monster["name"],
                "initiative": max(1, init_roll),
                "hp": monster["hp"],
                "reason": f"Encounters party during the giant crisis"
            })
        
        return {
            "monsters": monsters,
            "encounter_description": f"{'A' if len(monsters) == 1 else 'Several'} {'hostile creature' if len(monsters) == 1 else 'creatures'} {'appears' if len(monsters) == 1 else 'appear'}!"
        }
    
    def _format_available_monsters(self, party_level: int) -> str:
        """Format available monsters for AI prompt"""
        level_key = min(max(party_level, 1), 5)
        monsters = self.skt_monsters_by_level[level_key]
        
        formatted = []
        for monster in monsters:
            formatted.append(f"- {monster['name']} (HP: {monster['hp']}, CR: {monster['cr']})")
        
        return "\n".join(formatted)
    
    def _extract_json_from_response(self, response_text: str) -> Optional[Dict]:
        """Extract JSON from AI response"""
        try:
            # Find JSON in response
            json_start = response_text.find('{')
            json_end = response_text.rfind('}') + 1
            
            if json_start >= 0 and json_end > json_start:
                json_text = response_text[json_start:json_end]
                return json.loads(json_text)
            else:
                print("⚠️ No valid JSON found in AI response")
                return None
                
        except json.JSONDecodeError as e:
            print(f"⚠️ JSON decode error: {e}")
            return None
        except Exception as e:
            print(f"⚠️ JSON extraction error: {e}")
            return None
    
    def _validate_monsters_data(self, monsters_data: Dict) -> bool:
        """Validate AI-generated monsters data"""
        try:
            if not isinstance(monsters_data, dict):
                return False
            
            if "monsters" not in monsters_data:
                return False
            
            monsters = monsters_data["monsters"]
            if not isinstance(monsters, list) or len(monsters) == 0:
                return False
            
            # Validate each monster
            for monster in monsters:
                if not isinstance(monster, dict):
                    return False
                
                required_fields = ["name", "initiative", "hp"]
                if not all(field in monster for field in required_fields):
                    return False
                
                # Validate types
                if not isinstance(monster["name"], str) or len(monster["name"]) == 0:
                    return False
                
                if not isinstance(monster["initiative"], int) or monster["initiative"] < 1:
                    return False
                
                if not isinstance(monster["hp"], int) or monster["hp"] < 1:
                    return False
            
            return True
            
        except Exception as e:
            print(f"⚠️ Monster validation error: {e}")
            return False
    
    def get_party_info(self) -> Tuple[int, int]:
        """Get current party level and size"""
        try:
            players = self.campaign_context.get("players", {})
            if not players:
                return 1, 1
            
            levels = []
            for player_data in players.values():
                char_data = player_data.get("character_data", {})
                level = char_data.get("level", 1)
                levels.append(level)
            
            party_size = len(levels)
            avg_level = sum(levels) // len(levels) if levels else 1
            
            return avg_level, party_size
            
        except Exception as e:
            print(f"⚠️ Error getting party info: {e}")
            return 1, 1

class CombatInitiator:
    """Handles the actual combat initiation with your existing combat system"""
    
    def __init__(self, ai_combat_manager):
        self.ai_combat_manager = ai_combat_manager
    
    async def initiate_ai_combat(self, channel_id: int, narrative_context: str) -> Optional[Dict]:
        """Start combat with AI-generated monsters"""
        try:
            # Import your existing combat system
            from combat_system.combat_integration import get_combat_integration
            
            combat = get_combat_integration()
            if not combat:
                print("❌ Combat integration not available")
                return None
            
            # Get party info
            party_level, party_size = self.ai_combat_manager.get_party_info()
            
            # Generate monsters
            monsters_data = await self.ai_combat_manager.generate_context_appropriate_monsters(
                narrative_context=narrative_context,
                party_level=party_level,
                party_size=party_size
            )
            
            # Add monsters to combat system
            added_monsters = []
            for monster in monsters_data["monsters"]:
                success = await combat.add_enemy_to_combat(
                    channel_id=channel_id,
                    enemy_name=monster["name"],
                    initiative=monster["initiative"],
                    hp=monster["hp"]
                )
                
                if success:
                    added_monsters.append(monster["name"])
                    print(f"✅ Added {monster['name']} to combat")
                else:
                    print(f"❌ Failed to add {monster['name']} to combat")
            
            # Start combat if we added monsters
            if added_monsters:
                combat_started = await combat.start_combat_with_announcement(channel_id)
                if combat_started:
                    print(f"✅ Combat started with {len(added_monsters)} monsters")
                    return {
                        "monsters_added": added_monsters,
                        "encounter_description": monsters_data.get("encounter_description", "Combat begins!"),
                        "combat_started": True
                    }
                else:
                    print("❌ Failed to start combat")
                    return None
            else:
                print("❌ No monsters were added to combat")
                return None
                
        except Exception as e:
            print(f"❌ Combat initiation error: {e}")
            import traceback
            traceback.print_exc()
            return None