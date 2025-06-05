"""
DM Donnie Combat System Package
Enhanced combat tracking with auto-updating displays and state management
"""

from .combat_manager import CombatManager, CombatPhase, Combatant
from .combat_display import CombatDisplayManager, CombatDisplay
from .combat_integration import CombatIntegration, initialize_combat_system, get_combat_integration

__version__ = "1.0.0"
__author__ = "DM Donnie Bot Team"

__all__ = [
    'CombatManager',
    'CombatPhase', 
    'Combatant',
    'CombatDisplayManager',
    'CombatDisplay',
    'CombatIntegration',
    'initialize_combat_system',
    'get_combat_integration'
]

print("✅ Combat System package loaded")