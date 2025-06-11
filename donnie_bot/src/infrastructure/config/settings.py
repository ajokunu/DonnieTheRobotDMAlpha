"""
Configuration management for infrastructure components.
"""
import os
from dataclasses import dataclass
from typing import Optional
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # dotenv is optional


@dataclass
class DatabaseConfig:
    """Database configuration"""
    path: str = "data/donnie.db"
    backup_path: str = "data/backups"
    auto_backup: bool = True
    backup_interval_hours: int = 24
    
    def __post_init__(self):
        # Ensure database directory exists
        db_dir = Path(self.path).parent
        db_dir.mkdir(parents=True, exist_ok=True)
        
        if self.auto_backup:
            backup_dir = Path(self.backup_path)
            backup_dir.mkdir(parents=True, exist_ok=True)


@dataclass 
class AIConfig:
    """AI service configuration"""
    api_key: str = ""
    model: str = "claude-3-sonnet-20240229"
    max_tokens: int = 1000
    temperature: float = 0.7
    timeout_seconds: int = 30
    
    def __post_init__(self):
        if not self.api_key:
            self.api_key = os.getenv("ANTHROPIC_API_KEY", "")
        
        # Don't raise error here - let the bot start without AI
        # We'll validate when AI features are actually used
    
    def is_available(self) -> bool:
        """Check if AI service is available"""
        return bool(self.api_key.strip())


@dataclass
class VoiceConfig:
    """Voice service configuration"""
    enabled: bool = True
    default_speed: float = 1.25
    default_quality: str = "smart"
    cache_directory: str = "data/audio_cache"
    max_cache_size_mb: int = 500
    cleanup_interval_hours: int = 168  # 1 week
    
    def __post_init__(self):
        if self.enabled:
            cache_dir = Path(self.cache_directory)
            cache_dir.mkdir(parents=True, exist_ok=True)


@dataclass
class DiscordConfig:
    """Discord bot configuration"""
    token: str = ""
    command_prefix: str = "!"
    intents_all: bool = False
    
    def __post_init__(self):
        if not self.token:
            self.token = os.getenv("DISCORD_TOKEN", "")
        
        # Don't raise error here either - we'll check this in main.py


@dataclass
class CacheConfig:
    """Cache configuration"""
    enabled: bool = True
    max_size: int = 1000
    ttl_seconds: int = 3600  # 1 hour default
    character_ttl: int = 1800  # 30 minutes
    episode_ttl: int = 600    # 10 minutes
    memory_ttl: int = 7200    # 2 hours


class Settings:
    """Application settings with environment variable support"""
    
    def __init__(self):
        self.database = DatabaseConfig()
        self.ai = AIConfig()
        self.voice = VoiceConfig()
        self.discord = DiscordConfig()
        self.cache = CacheConfig()
        
        # Environment overrides
        self._apply_env_overrides()
    
    def _apply_env_overrides(self):
        """Apply environment variable overrides"""
        
        # Database overrides
        if db_path := os.getenv("DB_PATH"):
            self.database.path = db_path
        
        # AI overrides
        if model := os.getenv("AI_MODEL"):
            self.ai.model = model
        
        if max_tokens := os.getenv("AI_MAX_TOKENS"):
            try:
                self.ai.max_tokens = int(max_tokens)
            except ValueError:
                pass
        
        if temperature := os.getenv("AI_TEMPERATURE"):
            try:
                self.ai.temperature = float(temperature)
            except ValueError:
                pass
        
        # Voice overrides
        if voice_enabled := os.getenv("VOICE_ENABLED"):
            self.voice.enabled = voice_enabled.lower() in ("true", "1", "yes")
        
        # Discord overrides  
        if prefix := os.getenv("COMMAND_PREFIX"):
            self.discord.command_prefix = prefix
    
    def validate(self) -> tuple[bool, list[str]]:
        """Validate all configuration and return (is_valid, errors)"""
        errors = []
        
        try:
            # Check required Discord token
            if not self.discord.token:
                errors.append("DISCORD_TOKEN environment variable is required")
            
            # AI is optional - just warn if missing
            if not self.ai.is_available():
                errors.append("ANTHROPIC_API_KEY not set - AI features will be disabled")
            
            # Validate ranges
            if not (0.0 <= self.ai.temperature <= 2.0):
                errors.append("AI temperature must be between 0.0 and 2.0")
            
            if self.ai.max_tokens < 1:
                errors.append("AI max_tokens must be positive")
            
            return len(errors) == 0 or (len(errors) == 1 and "AI features will be disabled" in errors[0]), errors
            
        except Exception as e:
            errors.append(f"Configuration validation error: {e}")
            return False, errors
    
    def get_environment(self) -> str:
        """Get current environment (dev/prod)"""
        return os.getenv("ENVIRONMENT", "development").lower()
    
    def is_development(self) -> bool:
        """Check if running in development mode"""
        return self.get_environment() == "development"
    
    def is_production(self) -> bool:
        """Check if running in production mode"""
        return self.get_environment() == "production"


# Global settings instance
settings = Settings()