"""
Dependency injection container for wiring all components
"""
import logging
from typing import Optional

from ..infrastructure.config.settings import settings
from ..infrastructure.database.sqlite_repository import SQLiteRepositoryFactory
from ..infrastructure.ai.claude_service import ClaudeService
from ..infrastructure.voice.discord_voice import DiscordVoiceService
from ..infrastructure.cache.memory_cache import MemoryCacheService

from ..domain.services import CharacterService, EpisodeService, MemoryService, CombatService
from ..application.use_cases import (
    ManageCharacterUseCase,
    StartEpisodeUseCase, 
    HandleActionUseCase,
    ProcessVoiceUseCase
)

logger = logging.getLogger(__name__)


class DependencyContainer:
    """Container for dependency injection"""
    
    def __init__(self):
        # Infrastructure
        self.repository_factory: Optional[SQLiteRepositoryFactory] = None
        self.ai_service: Optional[ClaudeService] = None
        self.voice_service: Optional[DiscordVoiceService] = None
        self.cache_service: Optional[MemoryCacheService] = None
        
        # Domain Services
        self.character_service: Optional[CharacterService] = None
        self.episode_service: Optional[EpisodeService] = None
        self.memory_service: Optional[MemoryService] = None
        self.combat_service: Optional[CombatService] = None
        
        # Use Cases
        self.character_use_case: Optional[ManageCharacterUseCase] = None
        self.episode_use_case: Optional[StartEpisodeUseCase] = None
        self.action_use_case: Optional[HandleActionUseCase] = None
        self.voice_use_case: Optional[ProcessVoiceUseCase] = None
    
    async def initialize(self):
        """Initialize all dependencies in correct order"""
        logger.info("🔧 Initializing dependency container...")
        
        try:
            # 1. Infrastructure Layer
            await self._initialize_infrastructure()
            
            # 2. Domain Services  
            await self._initialize_domain_services()
            
            # 3. Application Use Cases
            await self._initialize_use_cases()
            
            logger.info("✅ Dependency container initialized successfully")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize dependencies: {e}")
            raise
    
    async def _initialize_infrastructure(self):
        """Initialize infrastructure layer"""
        logger.info("Initializing infrastructure layer...")
        
        # Database repositories
        self.repository_factory = SQLiteRepositoryFactory(settings.database.path)
        logger.info(f"📁 Database path: {settings.database.path}")
        
        # AI service
        if settings.ai.api_key:
            self.ai_service = ClaudeService(settings.ai)
            logger.info(f"🤖 AI service initialized (model: {settings.ai.model})")
        else:
            logger.warning("⚠️ AI service not initialized - missing API key")
        
        # Voice service
        self.voice_service = DiscordVoiceService(settings.voice)
        if settings.voice.enabled:
            logger.info("🔊 Voice service initialized")
        else:
            logger.info("🔇 Voice service disabled")
        
        # Cache service
        self.cache_service = MemoryCacheService(settings.cache)
        if settings.cache.enabled:
            logger.info(f"💾 Cache service initialized (max size: {settings.cache.max_size})")
        else:
            logger.info("Cache service disabled")
    
    async def _initialize_domain_services(self):
        """Initialize domain services"""
        logger.info("Initializing domain services...")
        
        # Create repositories
        character_repo = await self.repository_factory.create_character_repository()
        episode_repo = await self.repository_factory.create_episode_repository()
        guild_repo = await self.repository_factory.create_guild_repository()
        memory_repo = await self.repository_factory.create_memory_repository()
        
        # Character service
        self.character_service = CharacterService(
            character_repo=character_repo,
            ai_service=self.ai_service
        )
        
        # Episode service  
        self.episode_service = EpisodeService(
            episode_repo=episode_repo,
            memory_repo=memory_repo,
            ai_service=self.ai_service
        )
        
        # Memory service
        self.memory_service = MemoryService(
            memory_repo=memory_repo,
            ai_service=self.ai_service
        )
        
        # Combat service
        self.combat_service = CombatService()
        
        logger.info("✅ Domain services initialized")
    
    async def _initialize_use_cases(self):
        """Initialize application use cases"""
        logger.info("Initializing use cases...")
        
        # Character management
        self.character_use_case = ManageCharacterUseCase(
            character_service=self.character_service,
            cache_service=self.cache_service
        )
        
        # Episode management
        self.episode_use_case = StartEpisodeUseCase(
            episode_service=self.episode_service,
            character_service=self.character_service,
            memory_service=self.memory_service,
            cache_service=self.cache_service
        )
        
        # Action handling
        self.action_use_case = HandleActionUseCase(
            episode_service=self.episode_service,
            character_service=self.character_service,
            ai_service=self.ai_service,
            memory_service=self.memory_service,
            combat_service=self.combat_service,
            cache_service=self.cache_service
        )
        
        # Voice processing
        self.voice_use_case = ProcessVoiceUseCase(
            voice_service=self.voice_service,
            cache_service=self.cache_service
        )
        
        logger.info("✅ Use cases initialized")
    
    async def cleanup(self):
        """Cleanup resources"""
        logger.info("🧹 Cleaning up dependencies...")
        
        # Voice cleanup
        if self.voice_service:
            await self.voice_service.cleanup_cache()
        
        # Cache cleanup  
        if self.cache_service:
            await self.cache_service.clear()
        
        logger.info("✅ Cleanup completed")


# Global container instance
container = DependencyContainer()