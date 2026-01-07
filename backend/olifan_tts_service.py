"""
Coqui TTS Service for Olifan Assistant
Provides high-quality multilingual text-to-speech capabilities
"""

import os
import io
import base64
import torch
import numpy as np
from typing import Optional
from TTS.api import TTS
from fastapi import HTTPException
import logging

logger = logging.getLogger(__name__)

class CoquiTTSService:
    def __init__(self):
        self.tts_model = None
        self.device = None
        self._initialize_tts()
    
    def _initialize_tts(self):
        """Initialize Coqui TTS model"""
        try:
            # Check if CUDA is available
            self.device = "cuda" if torch.cuda.is_available() else "cpu"
            logger.info(f"TTS using device: {self.device}")
            
            # Initialize XTTS model for multilingual support
            # Using XTTS v2 for best quality
            self.tts_model = TTS(model_name="tts_models/multilingual/multi-dataset/xtts_v2", 
                               progress_bar=False, 
                               gpu=self.device == "cuda")
            
            logger.info("✅ Coqui TTS XTTS v2 model initialized successfully")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize Coqui TTS: {str(e)}")
            self.tts_model = None
    
    def synthesize_speech(self, text: str, language: str = "fr", speaker_wav: Optional[str] = None) -> bytes:
        """
        Convert text to speech using Coqui TTS
        
        Args:
            text: Text to synthesize
            language: Language code (fr, en, es, etc.)
            speaker_wav: Path to reference audio for voice cloning (optional)
        
        Returns:
            Audio bytes in WAV format
        """
        if not self.tts_model:
            raise HTTPException(status_code=500, detail="TTS service not available")
        
        try:
            # Default speaker reference (you can add your own reference audio)
            default_speakers = {
                "fr": "female",  # French female voice
                "en": "female",  # English female voice
                "es": "female",  # Spanish female voice
            }
            
            speaker = default_speakers.get(language, "female")
            
            # Synthesize speech
            wav = self.tts_model.tts(
                text=text,
                speaker=speaker,
                language=language,
                file_path=None  # Return as bytes, don't save to file
            )
            
            # Convert to proper WAV format
            audio_bytes = self._convert_to_wav(wav)
            return audio_bytes
            
        except Exception as e:
            logger.error(f"TTS synthesis error: {str(e)}")
            raise HTTPException(status_code=500, detail=f"TTS synthesis failed: {str(e)}")
    
    def _convert_to_wav(self, audio_array: np.ndarray) -> bytes:
        """Convert numpy array to WAV bytes"""
        try:
            import wave
            
            # Normalize audio to 16-bit integers
            audio_array = np.array(audio_array)
            audio_array = audio_array / np.max(np.abs(audio_array))
            audio_int16 = (audio_array * 32767).astype(np.int16)
            
            # Create WAV in memory
            buffer = io.BytesIO()
            with wave.open(buffer, 'wb') as wav_file:
                wav_file.setnchannels(1)  # Mono
                wav_file.setsampwidth(2)  # 16-bit
                wav_file.setframerate(22050)  # Sample rate
                wav_file.writeframes(audio_int16.tobytes())
            
            return buffer.getvalue()
            
        except Exception as e:
            logger.error(f"WAV conversion error: {str(e)}")
            raise HTTPException(status_code=500, detail="Audio conversion failed")

# Global TTS service instance
tts_service = None

def get_tts_service():
    """Get or create TTS service instance"""
    global tts_service
    if tts_service is None:
        tts_service = CoquiTTSService()
    return tts_service

def synthesize_text_to_speech(text: str, language: str = "fr") -> bytes:
    """
    Convenience function to synthesize text to speech
    
    Args:
        text: Text to convert
        language: Language code
    
    Returns:
        WAV audio bytes
    """
    service = get_tts_service()
    return service.synthesize_speech(text, language)