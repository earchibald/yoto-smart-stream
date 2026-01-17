"""
AWS Polly Text-to-Speech service for generating high-quality audio.

This module provides TTS functionality using AWS Polly Neural voices.
"""

import logging
import os
import tempfile
from pathlib import Path
from typing import Optional, Tuple

logger = logging.getLogger(__name__)


class PollyTTSService:
    """Service for generating text-to-speech audio using AWS Polly."""

    def __init__(
        self,
        engine: str = "neural",
        voice_id: str = "Joanna",
        output_format: str = "mp3",
        sample_rate: str = "24000",
        s3_bucket: Optional[str] = None,
    ):
        """
        Initialize the Polly TTS service.

        Args:
            engine: Polly engine type ("neural" or "standard")
            voice_id: Voice ID to use (e.g., "Joanna", "Matthew", "Amy")
            output_format: Output audio format ("mp3", "ogg_vorbis", "pcm")
            sample_rate: Audio sample rate in Hz
            s3_bucket: Optional S3 bucket name for uploading generated audio
        """
        self.engine = engine
        self.voice_id = voice_id
        self.output_format = output_format
        self.sample_rate = sample_rate
        self.s3_bucket = s3_bucket
        self._polly_client = None
        self._s3_client = None
        self._enabled = True
        
        # Try to initialize boto3 clients
        try:
            import boto3
            self._polly_client = boto3.client('polly')
            if s3_bucket:
                self._s3_client = boto3.client('s3')
            logger.info(f"Polly TTS initialized: engine={engine}, voice={voice_id}")
        except Exception as e:
            logger.warning(f"Could not initialize AWS Polly client: {e}")
            self._enabled = False

    def synthesize_speech(
        self,
        text: str,
        output_path: Path,
        voice_id: Optional[str] = None,
    ) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Synthesize speech from text and save to file.

        Args:
            text: Text to convert to speech
            output_path: Path where audio file should be saved
            voice_id: Optional voice ID to override default

        Returns:
            Tuple of (success, s3_url, error_message)
            - success: True if synthesis and save succeeded
            - s3_url: S3 URL if uploaded, None otherwise
            - error_message: Error description if failed, None if successful
        """
        if not self._enabled or not self._polly_client:
            error_msg = "AWS Polly is not available. Falling back to gTTS."
            logger.warning(error_msg)
            return False, None, error_msg

        try:
            # Use provided voice or default
            voice = voice_id or self.voice_id
            
            logger.info(f"Synthesizing speech with Polly: {len(text)} chars, voice={voice}")
            
            # Call Polly to synthesize speech
            response = self._polly_client.synthesize_speech(
                Engine=self.engine,
                Text=text,
                VoiceId=voice,
                OutputFormat=self.output_format,
                SampleRate=self.sample_rate,
            )
            
            # Save audio stream to file
            if "AudioStream" in response:
                with open(output_path, "wb") as file:
                    file.write(response["AudioStream"].read())
                
                file_size = output_path.stat().st_size
                logger.info(f"✓ Polly synthesis complete: {output_path.name} ({file_size} bytes)")
                
                # Upload to S3 if bucket is configured
                s3_url = None
                if self._s3_client and self.s3_bucket:
                    try:
                        s3_key = output_path.name
                        self._s3_client.upload_file(
                            str(output_path),
                            self.s3_bucket,
                            s3_key,
                            ExtraArgs={'ContentType': 'audio/mpeg'}
                        )
                        s3_url = f"https://{self.s3_bucket}.s3.amazonaws.com/{s3_key}"
                        logger.info(f"✓ Uploaded to S3: {s3_url}")
                    except Exception as s3_error:
                        logger.warning(f"Could not upload to S3: {s3_error}")
                
                return True, s3_url, None
            else:
                error_msg = "No audio stream in Polly response"
                logger.error(error_msg)
                return False, None, error_msg
                
        except Exception as e:
            error_msg = f"Polly synthesis error: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return False, None, error_msg

    def is_available(self) -> bool:
        """Check if Polly TTS is available."""
        return self._enabled and self._polly_client is not None


# Global instance (lazy-loaded)
_polly_service: Optional[PollyTTSService] = None


def get_polly_service() -> PollyTTSService:
    """
    Get or create the global Polly TTS service instance.

    Returns:
        PollyTTSService instance
    """
    global _polly_service
    if _polly_service is None:
        # Get S3 bucket from environment
        s3_bucket = os.environ.get("S3_AUDIO_BUCKET")
        _polly_service = PollyTTSService(
            engine="neural",
            voice_id="Joanna",  # US English female voice
            output_format="mp3",
            sample_rate="24000",
            s3_bucket=s3_bucket,
        )
    return _polly_service
