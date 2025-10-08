"""
Test script for VoiceAgent orchestrator.

This script demonstrates basic usage and verifies that all components can be imported.
"""
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from loguru import logger

# Configure simple logging
logger.remove()
logger.add(sys.stderr, level="INFO")


def test_imports():
    """Test that all components can be imported."""
    logger.info("Testing imports...")
    
    try:
        from agent.orchestrator import VoiceAgent, InitializationError, create_voice_agent
        logger.info("✓ VoiceAgent imported")
        
        from audio.audio_manager import AudioManager
        logger.info("✓ AudioManager imported")
        
        from speech.elevenlabs_tts import ElevenLabsTTS
        logger.info("✓ ElevenLabsTTS imported")
        
        from stt.whisper_transcriber import WhisperTranscriber
        logger.info("✓ WhisperTranscriber imported")
        
        from conversation.state_manager import ConversationStateManager
        logger.info("✓ ConversationStateManager imported")
        
        from nlu.extractor import extract_booking_info
        logger.info("✓ NLU Extractor imported")
        
        from response.generator import generate_response
        logger.info("✓ Response Generator imported")
        
        from services.booking_service import BookingService
        logger.info("✓ BookingService imported")
        
        from notifications.sms import send_sms_confirmation
        logger.info("✓ SMS Service imported")
        
        from notifications.email import send_email_confirmation
        logger.info("✓ Email Service imported")
        
        logger.info("✓ All imports successful!")
        return True
        
    except Exception as e:
        logger.error(f"Import failed: {e}")
        return False


def test_voice_agent_creation():
    """Test creating VoiceAgent instance."""
    logger.info("\nTesting VoiceAgent creation...")
    
    try:
        from agent.orchestrator import VoiceAgent
        
        # Create agent without initializing (to avoid requiring hardware/API keys)
        agent = VoiceAgent()
        logger.info("✓ VoiceAgent created successfully")
        
        # Check attributes
        assert hasattr(agent, 'initialize')
        assert hasattr(agent, 'run')
        assert hasattr(agent, 'shutdown')
        logger.info("✓ VoiceAgent has expected methods")
        
        return True
        
    except Exception as e:
        logger.error(f"VoiceAgent creation failed: {e}")
        return False


def test_component_stubs():
    """Test that stub implementations work."""
    logger.info("\nTesting stub implementations...")
    
    try:
        import numpy as np
        
        # Test Whisper transcriber stub
        from stt.whisper_transcriber import WhisperTranscriber
        transcriber = WhisperTranscriber()
        dummy_audio = np.zeros(16000, dtype=np.float32)
        result = transcriber.transcribe(dummy_audio)
        logger.info(f"✓ Whisper stub returned: {result[:50]}...")
        
        # Test SMS stub
        from notifications.sms import send_sms_confirmation
        send_sms_confirmation("+1234567890", {"test": "data"})
        logger.info("✓ SMS stub executed")
        
        # Test Email stub
        from notifications.email import send_email_confirmation
        send_email_confirmation("test@example.com", {"test": "data"})
        logger.info("✓ Email stub executed")
        
        return True
        
    except Exception as e:
        logger.error(f"Stub test failed: {e}")
        return False


def main():
    """Run all tests."""
    logger.info("=" * 60)
    logger.info("VoiceAgent Orchestrator Test Suite")
    logger.info("=" * 60)
    
    results = []
    
    # Run tests
    results.append(("Import Test", test_imports()))
    results.append(("VoiceAgent Creation Test", test_voice_agent_creation()))
    results.append(("Stub Components Test", test_component_stubs()))
    
    # Summary
    logger.info("\n" + "=" * 60)
    logger.info("Test Summary")
    logger.info("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        logger.info(f"{status}: {name}")
    
    logger.info(f"\nTotal: {passed}/{total} tests passed")
    
    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
