"""
TTS (Text-to-Speech) Module
------------------------
Convert transcript to speech using various TTS providers
"""

import os
import logging
import json
import requests
import re
import tempfile
from pathlib import Path
from enum import Enum
import time

from src.utils.progress import ProgressBar
from src.utils.file_utils import ensure_directory


logger = logging.getLogger(__name__)


class Speaker(Enum):
    """Enum for speaker types"""
    HOST = "host"
    EXPERT = "expert"
    BEGINNER = "beginner"


class TTSGenerator:
    """Text-to-speech generator class"""
    
    def __init__(self, config):
        """
        Initialize the TTS generator
        
        Args:
            config (dict): Configuration dictionary
        """
        self.config = config
        self.provider = config["tts"]["provider"]
        self.api_key = config["api_keys"].get(self.provider)
        
        if not self.api_key:
            raise ValueError(f"API key for {self.provider} not found in configuration")
        
        # Configure voice settings for each speaker
        self.voice_settings = {}
        for speaker in Speaker:
            speaker_name = speaker.value
            self.voice_settings[speaker_name] = config["tts"].get(speaker_name, {})
        
        logger.debug(f"Initialized TTS generator with provider: {self.provider}")
    
    def generate(self, transcript, output_dir):
        """
        Generate speech audio from transcript
        
        Args:
            transcript (str): The podcast transcript
            output_dir (str or Path): Directory to save audio files
            
        Returns:
            list: List of audio file paths with metadata
        """
        logger.info("Generating speech from transcript")
        
        # Parse transcript into segments by speaker
        segments = self._parse_transcript(transcript)
        
        # Create output directory
        audio_dir = ensure_directory(Path(output_dir) / "audio_clips")
        
        # Create progress bar
        progress = ProgressBar(total=len(segments), desc="Generating speech", unit="segments")
        
        audio_files = []
        
        try:
            # Process each segment
            for i, (speaker, text) in enumerate(segments):
                speaker_type = self._get_speaker_type(speaker)
                
                # Generate speech based on provider
                output_file = audio_dir / f"{i:03d}_{speaker_type.value}.mp3"
                
                if self.provider == "elevenlabs":
                    self._generate_elevenlabs(text, output_file, speaker_type)
                elif self.provider == "gemini":
                    self._generate_gemini(text, output_file, speaker_type)
                else:
                    raise ValueError(f"Unsupported TTS provider: {self.provider}")
                
                # Add pause after segment
                pause_duration = self._get_pause_duration(text)
                
                # Add to our list with metadata
                audio_files.append({
                    "path": str(output_file),
                    "speaker": speaker_type.value,
                    "text": text,
                    "pause_after": pause_duration
                })
                
                progress.update(1, f"Generated {speaker} speech")
                
                # Avoid rate limiting
                time.sleep(0.5)
            
            logger.info(f"Generated {len(audio_files)} audio segments")
            return audio_files
            
        except Exception as e:
            logger.error(f"Error generating speech: {str(e)}")
            raise
        finally:
            progress.close()
    
    def _parse_transcript(self, transcript):
        """
        Parse transcript into segments by speaker
        
        Args:
            transcript (str): The podcast transcript
            
        Returns:
            list: List of (speaker, text) tuples
        """
        # Get speaker names from config
        host_name = self.config["transcript"].get("host_name", "HOST").upper()
        expert_name = self.config["transcript"].get("expert_name", "EXPERT").upper()
        beginner_name = self.config["transcript"].get("beginner_name", "BEGINNER").upper()
        
        # Split by speaker blocks
        lines = transcript.strip().split('\n')
        segments = []
        
        current_speaker = None
        current_text = []
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # Check if this line starts a new speaker section
            if line.startswith(f"{host_name}:"):
                # Save previous segment if it exists
                if current_speaker and current_text:
                    segments.append((current_speaker, ' '.join(current_text)))
                
                # Start new segment
                current_speaker = host_name
                current_text = [line[len(host_name) + 1:].strip()]
                
            elif line.startswith(f"{expert_name}:"):
                # Save previous segment if it exists
                if current_speaker and current_text:
                    segments.append((current_speaker, ' '.join(current_text)))
                
                # Start new segment
                current_speaker = expert_name
                current_text = [line[len(expert_name) + 1:].strip()]
                
            elif line.startswith(f"{beginner_name}:"):
                # Save previous segment if it exists
                if current_speaker and current_text:
                    segments.append((current_speaker, ' '.join(current_text)))
                
                # Start new segment
                current_speaker = beginner_name
                current_text = [line[len(beginner_name) + 1:].strip()]
                
            # Check if this is a pause marker
            elif line.startswith("[pause:") and current_speaker and current_text:
                # Extract pause duration and add it to the text
                pause_match = re.search(r'\[pause:([\d\.]+)\]', line)
                if pause_match:
                    # Just append the pause marker to the current text
                    current_text.append(line)
                
            elif current_speaker and current_text:
                # Continue current segment
                current_text.append(line)
        
        # Add the last segment
        if current_speaker and current_text:
            segments.append((current_speaker, ' '.join(current_text)))
            
        logger.debug(f"Parsed transcript into {len(segments)} segments")
        return segments
    
    def _get_speaker_type(self, speaker_name):
        """
        Convert speaker name to Speaker enum type
        
        Args:
            speaker_name (str): Speaker name from transcript
            
        Returns:
            Speaker: Speaker enum type
        """
        host_name = self.config["transcript"].get("host_name", "HOST").upper()
        expert_name = self.config["transcript"].get("expert_name", "EXPERT").upper()
        beginner_name = self.config["transcript"].get("beginner_name", "BEGINNER").upper()
        
        if speaker_name == host_name:
            return Speaker.HOST
        elif speaker_name == expert_name:
            return Speaker.EXPERT
        elif speaker_name == beginner_name:
            return Speaker.BEGINNER
        else:
            logger.warning(f"Unknown speaker: {speaker_name}, defaulting to HOST")
            return Speaker.HOST
    
    def _get_pause_duration(self, text):
        """
        Get pause duration from text
        
        Args:
            text (str): Text to check for pause markers
            
        Returns:
            float: Pause duration in seconds
        """
        # Default pause durations
        default_pauses = {
            ".": 0.5,   # End of sentence
            "?": 0.6,   # Question
            "!": 0.6,   # Exclamation
            ",": 0.2,   # Comma
            ";": 0.3,   # Semicolon
            ":": 0.3,   # Colon
        }
        
        # Check for explicit pause marker
        pause_match = re.search(r'\[pause:([\d\.]+)\]', text)
        if pause_match:
            try:
                return float(pause_match.group(1))
            except (ValueError, IndexError):
                pass
        
        # Check for punctuation at the end
        for punct, duration in default_pauses.items():
            if text.rstrip().endswith(punct):
                return duration
        
        # Default pause
        return 0.3
    
    def _generate_elevenlabs(self, text, output_file, speaker_type):
        """
        Generate speech using ElevenLabs API
        
        Args:
            text (str): Text to convert to speech
            output_file (Path): Path to save the audio file
            speaker_type (Speaker): Speaker type enum
        """
        logger.debug(f"Generating speech with ElevenLabs for {speaker_type.value}")
        
        # Remove pause markers from text
        clean_text = re.sub(r'\[pause:[\d\.]+\]', '', text).strip()
        
        # Get speaker-specific settings
        voice_id = self.voice_settings[speaker_type.value].get("voice_id")
        if not voice_id:
            raise ValueError(f"Voice ID not found for {speaker_type.value}")
        
        # Set up API call
        url = self.config.get("api_urls", {}).get(
            "elevenlabs", 
            "https://api.elevenlabs.io/v1/text-to-speech"
        ) + f"/{voice_id}"
        
        # Configure voice settings
        voice_settings = {
            "stability": self.voice_settings[speaker_type.value].get("stability", 0.5),
            "similarity_boost": self.voice_settings[speaker_type.value].get("similarity_boost", 0.75),
        }
        
        # Configure voice model
        model_id = self.config["tts"].get("model_id", "eleven_multilingual_v2")
        
        payload = {
            "text": clean_text,
            "model_id": model_id,
            "voice_settings": voice_settings
        }
        
        headers = {
            "Content-Type": "application/json",
            "xi-api-key": self.api_key
        }
        
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()
        
        # Save audio file
        with open(output_file, "wb") as f:
            f.write(response.content)
        
        logger.debug(f"Saved audio to {output_file}")
    
    def _generate_gemini(self, text, output_file, speaker_type):
        """
        Generate speech using Gemini API
        
        Args:
            text (str): Text to convert to speech
            output_file (Path): Path to save the audio file
            speaker_type (Speaker): Speaker type enum
        """
        logger.debug(f"Generating speech with Gemini for {speaker_type.value}")
        
        # Remove pause markers from text
        clean_text = re.sub(r'\[pause:[\d\.]+\]', '', text).strip()
        
        # Get speaker-specific settings
        voice_name = self.voice_settings[speaker_type.value].get("voice_name")
        if not voice_name:
            # Use default voices based on speaker type
            default_voices = {
                Speaker.HOST: "en-US-Studio-O",
                Speaker.EXPERT: "en-US-Neural2-D",
                Speaker.BEGINNER: "en-US-Neural2-F"
            }
            voice_name = default_voices.get(speaker_type, "en-US-Studio-O")
        
        # Set up API call
        url = self.config.get("api_urls", {}).get(
            "gemini", 
            "https://texttospeech.googleapis.com/v1/text:synthesize"
        )
        
        # Configure voice settings
        speaking_rate = self.voice_settings[speaker_type.value].get("speaking_rate", 1.0)
        pitch = self.voice_settings[speaker_type.value].get("pitch", 0.0)
        
        payload = {
            "input": {"text": clean_text},
            "voice": {
                "languageCode": self.voice_settings[speaker_type.value].get("language_code", "en-US"),
                "name": voice_name,
                "ssmlGender": self.voice_settings[speaker_type.value].get("gender", "NEUTRAL")
            },
            "audioConfig": {
                "audioEncoding": "MP3",
                "speakingRate": speaking_rate,
                "pitch": pitch
            }
        }
        
        headers = {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": self.api_key
        }
        
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()
        
        # Decode the base64 audio content
        import base64
        audio_content = base64.b64decode(response.json()["audioContent"])
        
        # Save audio file
        with open(output_file, "wb") as f:
            f.write(audio_content)
        
        logger.debug(f"Saved audio to {output_file}")


def generate_speech(transcript, output_dir, config):
    """
    Generate speech from transcript and save audio files
    
    Args:
        transcript (str): The podcast transcript
        output_dir (str or Path): Directory to save audio files
        config (dict): Configuration dictionary
    
    Returns:
        list: List of audio file paths with metadata
    """
    generator = TTSGenerator(config)
    audio_files = generator.generate(transcript, output_dir)
    
    logger.info(f"Generated {len(audio_files)} audio segments")
    return audio_files
