"""
Main entry point for restaurant booking voice agent.

This script initializes and runs the voice agent for handling
restaurant reservations through natural voice conversation.
"""
import sys
from pathlib import Path

from loguru import logger

# Configure logging
logger.remove()  # Remove default handler
logger.add(
    sys.stderr,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
    level="INFO"
)
logger.add(
    "logs/agent_{time:YYYY-MM-DD}.log",
    rotation="00:00",  # Rotate at midnight
    retention="30 days",
    compression="zip",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
    level="DEBUG"
)

from agent.orchestrator import VoiceAgent, InitializationError


def main():
    """
    Main entry point for the voice agent application.
    """
    logger.info("=" * 80)
    logger.info("Restaurant Booking Voice Agent")
    logger.info("=" * 80)
    
    # Create logs directory if it doesn't exist
    Path("logs").mkdir(exist_ok=True)
    
    try:
        # Create and initialize agent
        logger.info("Creating VoiceAgent...")
        agent = VoiceAgent()
        
        logger.info("Initializing components...")
        agent.initialize()
        
        logger.info("Starting conversation...")
        success = agent.run()
        
        if success:
            logger.info("✓ Booking completed successfully!")
            return 0
        else:
            logger.info("Conversation ended without completing booking")
            return 1
            
    except InitializationError as e:
        logger.error(f"Failed to initialize agent: {e}")
        logger.error("Please check:")
        logger.error("  - Audio devices are available and accessible")
        logger.error("  - API keys are configured in .env file")
        logger.error("  - Database is running and accessible")
        return 2
    
    except KeyboardInterrupt:
        logger.info("Application interrupted by user")
        return 130
    
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        return 3
    
    finally:
        logger.info("Application shutting down...")


if __name__ == "__main__":
    sys.exit(main())
