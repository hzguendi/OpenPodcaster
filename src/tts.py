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
import base64
from pathlib import Path
from enum import Enum
import time


from src.utils.api_stats import handle_api_error, APIStatsTracker

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
        
        # Coqui doesn't require an API key
        if self.provider != "coqui":
            self.api_key = config["api_keys"].get(self.provider)
            if not self.api_key:
                raise ValueError(f"API key for {self.provider} not found in configuration")
        
        # Configure voice settings for each speaker
        self.voice_settings = {}
        for speaker in Speaker:
            speaker_name = speaker.value
            self.voice_settings[speaker_name] = config["tts"].get(speaker_name, {})
        
        # Initialize API stats tracker
        self.api_stats = APIStatsTracker(config)
        
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
                elif self.provider == "coqui":
                    self._generate_coqui(text, output_file, speaker_type)
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
            
            # Skip timestamp and section headers
            if line.startswith('[TIMESTAMP]') or line.startswith('[00:') or line == '---':
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
        
        # Check for explicit pause marker in new format
        pause_match = re.search(r'<<PAUSE:([\d\.]+)>>', text)
        if pause_match:
            try:
                return float(pause_match.group(1))
            except (ValueError, IndexError):
                pass
            
        # Check for old format (fallback)
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
        
        # Remove markup tags
        clean_text = self._clean_markup_for_elevenlabs(text)
        
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
        
        start_time = time.time()
        success = False
        error_type = None
        text_length = len(clean_text)
        audio_size = 0
        
        try:
            response = requests.post(url, json=payload, headers=headers, timeout=60)
            response.raise_for_status()
            
            # Save audio file
            with open(output_file, "wb") as f:
                f.write(response.content)
            
            audio_size = len(response.content)
            success = True
            logger.debug(f"Saved audio to {output_file}")
            
        except requests.exceptions.Timeout:
            error_type = "timeout"
            logger.error(f"Timeout while connecting to ElevenLabs API")
            raise TimeoutError(f"Timeout while connecting to ElevenLabs API")
            
        except requests.exceptions.ConnectionError:
            error_type = "connection_error"
            logger.error(f"Could not connect to ElevenLabs API")
            raise ConnectionError(f"Could not connect to ElevenLabs API")
            
        except requests.exceptions.HTTPError as e:
            error_message, error_type = handle_api_error(response, "ElevenLabs", "speech generation")
            logger.error(error_message)
            raise Exception(error_message) from e
            
        except Exception as e:
            error_type = "unknown"
            logger.error(f"Error generating speech with ElevenLabs: {str(e)}")
            raise
            
        finally:
            latency = time.time() - start_time
            self.api_stats.record_request(
                provider="elevenlabs",
                model=model_id,
                request_type="tts",
                success=success,
                error_type=error_type,
                tokens_in=text_length,
                tokens_out=audio_size,
                latency=latency
            )
    
    def _clean_markup_for_elevenlabs(self, text):
        """Clean special markup tags for ElevenLabs"""
        # Replace pause markers
        text = re.sub(r'<<PAUSE:[\d\.]+>>', '', text)
        text = re.sub(r'\[pause:[\d\.]+\]', '', text)
        
        # Replace emphasis tags
        text = re.sub(r'<<EMPHASIS>>(.*?)<<EMPHASIS_END>>', r'*\1*', text)
        
        # Replace tone tags
        text = re.sub(r'<<TONE:\w+>>(.*?)<<TONE_END>>', r'\1', text)
        
        return text.strip()
    
    def _generate_coqui(self, text, output_file, speaker_type):
        """
        Generate speech using Coqui TTS with enhanced natural speech capabilities
        
        Args:
            text (str): Text to convert to speech
            output_file (Path): Path to save the audio file
            speaker_type (Speaker): Speaker type enum
        """
        logger.debug(f"Generating speech with Coqui TTS for {speaker_type.value}")
        
        # Process text with custom markup for Coqui
        processed_text = self._process_coqui_markup(text, speaker_type)
        
        try:
            from TTS.api import TTS
            
            # Get Coqui-specific configuration
            coqui_config = self.config["tts"].get("coqui_config", {})
            suppress_output = coqui_config.get("suppress_cli_output", True)
            use_gpu_setting = coqui_config.get("use_gpu", "auto")
            show_progress = coqui_config.get("progress_bar", False)
            
            # Determine GPU usage
            if use_gpu_setting == "auto":
                import torch
                use_gpu = torch.cuda.is_available()
            else:
                use_gpu = use_gpu_setting == True
            
            # Get speaker-specific settings
            voice_settings = self.voice_settings[speaker_type.value]
            model_name = voice_settings.get("model", "tts_models/en/vctk/vits")
            
            # Suppress TTS output if specified
            import sys
            original_stdout = sys.stdout
            null_device = open(os.devnull, 'w')
            
            try:
                # Redirect stdout to null device if suppressing output
                if suppress_output:
                    sys.stdout = null_device
                
                # Initialize TTS with appropriate settings
                tts = TTS(model_name=model_name,
                         progress_bar=show_progress,
                         gpu=use_gpu)
                
                # Prepare TTS arguments based on model type and available features
                tts_args = {
                    "text": processed_text,
                    "file_path": str(output_file),
                }
                
                # Add speaker if it's a multi-speaker model and the model supports it
                if voice_settings.get("speaker") and ("/vctk/" in model_name or "multi_speaker" in model_name):
                    tts_args["speaker"] = voice_settings.get("speaker")
                
                # Add language only for explicitly multilingual models
                if voice_settings.get("language") and any(x in model_name.lower() for x in ["multilingual", "xtts", "your_tts"]):
                    tts_args["language"] = voice_settings.get("language")
                    
                # Add speed/rate adjustment if supported by the model
                if voice_settings.get("speed") and hasattr(tts, "synthesizer") and hasattr(tts.synthesizer, "rate"):
                    tts.synthesizer.rate = voice_settings.get("speed")
                    
                # Some models support emotion and style parameters
                if "xtts" in model_name or "vits" in model_name:
                    # If emotion strength is specified and the model supports it
                    if voice_settings.get("emotion_strength") and hasattr(tts, "synthesizer") and hasattr(tts.synthesizer, "emotion_strength"):
                        tts.synthesizer.emotion_strength = voice_settings.get("emotion_strength")
                    
                    # If style is specified and the model supports it
                    if voice_settings.get("style") and hasattr(tts, "synthesizer") and hasattr(tts.synthesizer, "style"):
                        tts_args["style"] = voice_settings.get("style")
                
                # Generate the speech with suppressed output
                tts.tts_to_file(**tts_args)
                
            finally:
                # Restore stdout
                if suppress_output:
                    sys.stdout = original_stdout
                    null_device.close()
            
            logger.debug(f"Saved audio to {output_file}")
            self._record_coqui_stats(success=True)
            
        except Exception as e:
            self._record_coqui_stats(success=False)
            logger.error(f"Error generating speech with Coqui TTS: {str(e)}")
            raise
    
    def _process_coqui_markup(self, text, speaker_type):
        """
        Process Coqui-specific markup to clean the text for TTS
        
        Args:
            text (str): Original text with markup
            speaker_type (Speaker): Type of speaker
            
        Returns:
            str: Processed text ready for Coqui TTS
        """
        # Get speaker-specific characteristics
        voice_settings = self.voice_settings[speaker_type.value]
        
        # Clean text of all markup tags first
        processed_text = text
        
        # Remove timestamp and section headers that might have been missed
        processed_text = re.sub(r'\[TIMESTAMP\].*?(?=\n|$)', '', processed_text)
        processed_text = re.sub(r'\[\d{2}:\d{2}:\d{2}\].*?(?=\n|$)', '', processed_text)
        
        # Replace pause markers with actual silences (remove them for now)
        processed_text = re.sub(r'<<PAUSE:[\d\.]+>>', '', processed_text)
        processed_text = re.sub(r'\[pause:[\d\.]+\]', '', processed_text)
        
        # Replace emphasis tags (remove the tags but keep the content)
        processed_text = re.sub(r'<<EMPHASIS>>(.*?)<<EMPHASIS_END>>', r'\1', processed_text)
        
        # Replace tone tags (remove the tags but keep the content)
        processed_text = re.sub(r'<<TONE:\w+>>(.*?)<<TONE_END>>', r'\1', processed_text)
        
        # Clean up multiple spaces
        processed_text = re.sub(r' +', ' ', processed_text)
        
        return processed_text.strip()
            
    def _record_coqui_stats(self, success=True):
        """Record statistics for Coqui TTS usage"""
        self.api_stats.record_request(
            provider="coqui",
            model="local",
            request_type="tts",
            success=success,
            error_type=None if success else "generation_error",
            tokens_in=0,  # Coqui doesn't use token billing
            tokens_out=0,
            latency=0  # Latency tracking not implemented for local inference
        )

    def _generate_gemini(self, text, output_file, speaker_type):
        """
        Generate speech using Gemini API
        
        Args:
            text (str): Text to convert to speech
            output_file (Path): Path to save the audio file
            speaker_type (Speaker): Speaker type enum
        """
        logger.debug(f"Generating speech with Gemini for {speaker_type.value}")
        
        # Remove markup tags
        clean_text = self._clean_markup_for_gemini(text)
        
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
        
        start_time = time.time()
        success = False
        error_type = None
        text_length = len(clean_text)
        audio_size = 0
        model_name = "google_tts"
        
        try:
            response = requests.post(url, json=payload, headers=headers, timeout=60)
            response.raise_for_status()
            
            response_data = response.json()
            
            # Check for expected response format
            if "audioContent" not in response_data:
                raise ValueError("Invalid response format from Gemini API: 'audioContent' not found")
            
            # Decode the base64 audio content
            audio_content = base64.b64decode(response_data["audioContent"])
            audio_size = len(audio_content)
            
            # Save audio file
            with open(output_file, "wb") as f:
                f.write(audio_content)
            
            success = True
            logger.debug(f"Saved audio to {output_file}")
            
        except requests.exceptions.Timeout:
            error_type = "timeout"
            logger.error(f"Timeout while connecting to Gemini API")
            raise TimeoutError(f"Timeout while connecting to Gemini API")
            
        except requests.exceptions.ConnectionError:
            error_type = "connection_error"
            logger.error(f"Could not connect to Gemini API")
            raise ConnectionError(f"Could not connect to Gemini API")
            
        except requests.exceptions.HTTPError as e:
            error_message, error_type = handle_api_error(response, "Gemini", "speech generation")
            logger.error(error_message)
            raise Exception(error_message) from e
            
        except (KeyError, ValueError) as e:
            error_type = "invalid_response"
            logger.error(f"Invalid response from Gemini API: {str(e)}")
            raise ValueError(f"Invalid response from Gemini API: {str(e)}")
            
        except Exception as e:
            error_type = "unknown"
            logger.error(f"Error generating speech with Gemini: {str(e)}")
            raise
            
        finally:
            latency = time.time() - start_time
            self.api_stats.record_request(
                provider="gemini",
                model=model_name,
                request_type="tts",
                success=success,
                error_type=error_type,
                tokens_in=text_length,
                tokens_out=audio_size,
                latency=latency
            )
            
    def _clean_markup_for_gemini(self, text):
        """Clean special markup tags for Gemini"""
        # Same as for ElevenLabs
        return self._clean_markup_for_elevenlabs(text)


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
