# episode_manager/__init__.py
"""
Storm King's Thunder Episode Management Module
Provides episode lifecycle management and story continuity
"""

try:
    from .episode_commands import EpisodeCommands
    __all__ = ['EpisodeCommands']
except ImportError as e:
    print(f"⚠️ Episode commands not available: {e}")
    __all__ = []

# Version info
__version__ = "1.0.0"