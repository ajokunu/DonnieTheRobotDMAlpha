# character_tracker/__init__.py
"""
Storm King's Thunder Character Progression Module
Provides character advancement tracking and progression management
"""

try:
    from .progression import CharacterProgressionCommands
    __all__ = ['CharacterProgressionCommands']
except ImportError as e:
    print(f"⚠️ Character progression not available: {e}")
    __all__ = []

# Version info
__version__ = "1.0.0"