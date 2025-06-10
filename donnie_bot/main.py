#!/usr/bin/env python3
"""
Donnie the DM - AI-powered D&D Discord Bot
Main entry point with clean architecture
"""
import asyncio
import logging
import signal
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.infrastructure.config.logging import setup_logging
from src.infrastructure.config.settings import settings
from src.presentation.discord_bot import DonnieBot, CustomHelp


async def main():
    """Main application entry point"""
    
    # Setup logging
    log_file = "logs/donnie.log" if not settings.is_development() else None
    logger = setup_logging(
        level="DEBUG" if settings.is_development() else "INFO",
        log_file=log_file
    )
    
    logger.info("🎲 Starting Donnie the DM...")
    logger.info(f"📊 Environment: {settings.get_environment()}")
    logger.info(f"🗂️ Database: {settings.database.path}")
    logger.info(f"🤖 AI Model: {settings.ai.model}")
    logger.info(f"🔊 Voice Enabled: {settings.voice.enabled}")
    
    # Validate configuration
    if not settings.validate():
        logger.error("❌ Configuration validation failed")
        return 1
    
    # Create bot instance
    bot = DonnieBot()
    
    # Add custom help
    await bot.add_cog(CustomHelp(bot))
    
    # Setup graceful shutdown
    def signal_handler(signum, frame):
        logger.info(f"📡 Received signal {signum}")
        asyncio.create_task(bot.close())
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        # Start the bot
        logger.info("🚀 Connecting to Discord...")
        async with bot:
            await bot.start(settings.discord.token)
            
    except KeyboardInterrupt:
        logger.info("⌨️ Keyboard interrupt received")
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}", exc_info=True)
        return 1
    finally:
        logger.info("👋 Donnie the DM shutting down...")
    
    return 0


if __name__ == "__main__":
    # Ensure directories exist
    Path("logs").mkdir(exist_ok=True)
    Path("data").mkdir(exist_ok=True)
    
    # Run the bot
    exit_code = asyncio.run(main())
    sys.exit(exit_code)