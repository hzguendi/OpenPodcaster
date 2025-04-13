"""
Coqui-specific Text-to-Speech Module
-----------------------------------
Specialized processing for Coqui TTS to create more natural-sounding voices
"""

import os
import sys
import logging
import re
import tempfile
from pathlib import Path
import xml.etree.ElementTree as ET
from enum import Enum
import time
import torch
import numpy as np

from src.utils.api_stats import handle_api_error, APIStatsTracker
from src.utils.progress import ProgressBar
from src.utils.file_utils import ensure_directory
from src.tts import TTSGenerator, Speaker

logger = logging.getLogger(__name__)


class CoquiTTSGenerator(TTSGenerator):
    """Specialized text-to-speech generator for Coqui"""
    
    def __init__(self, config):
        """
        Initialize the specialized Coqui TTS generator
        
        Args:
            config (dict): Configuration dictionary
        """
        super().__init__(config)
        
        if self.provider != "coqui":
            logger.warning("CoquiTTSGenerator initialized with non-Coqui provider")
        
        # Get Coqui-specific configuration
        self.coqui_config = config["tts"].get("coqui_config", {})
        self.suppress_output = self.coqui_config.get("suppress_cli_output", True)
        self.use_gpu_setting = self.coqui_config.get("use_gpu", "auto")
        self.show_progress = self.coqui_config.get("progress_bar", False)
        
        logger.debug(f"Initialized Coqui TTS generator")
    
    def generate(self, transcript, output_dir):
        """
        Generate speech audio from transcript specially formatted for Coqui
        
        Args:
            transcript (str): The podcast transcript with Coqui-specific formatting
            output_dir (str or Path): Directory to save audio files
            
        Returns:
            list: List of audio file paths with metadata
        """
        logger.info("Generating speech from Coqui-formatted transcript")
        
        # Parse transcript into segments by speaker using XML-like tags
        segments = self._parse_coqui_transcript(transcript)
        
        # Create output directory
        audio_dir = ensure_directory(Path(output_dir) / "audio_clips")
        
        # Create progress bar
        progress = ProgressBar(total=len(segments), desc="Generating speech", unit="segments")
        
        audio_files = []
        
        try:
            # Process each segment
            for i, (speaker_type, text, pause_after) in enumerate(segments):
                # Generate speech for this segment
                output_file = audio_dir / f"{i:03d}_{speaker_type.value}.mp3"
                
                # Use the specialized Coqui generator
                self._generate_coqui_speech(text, output_file, speaker_type)
                
                # Add to our list with metadata
                audio_files.append({
                    "path": str(output_file),
                    "speaker": speaker_type.value,
                    "text": text,
                    "pause_after": pause_after
                })
                
                progress.update(1, f"Generated {speaker_type.value} speech")
                
                # Avoid rate limiting
                time.sleep(0.5)
            
            logger.info(f"Generated {len(audio_files)} audio segments")
            return audio_files
            
        except Exception as e:
            logger.error(f"Error generating speech: {str(e)}")
            raise
        finally:
            progress.close()
    
    def _parse_coqui_transcript(self, transcript):
        """
        Parse transcript with Coqui-specific XML-like tags or standard format
        
        Args:
            transcript (str): The podcast transcript with Coqui-specific formatting or standard format
            
        Returns:
            list: List of (speaker_type, text, pause_after) tuples
        """
        # Get speaker names from config for fallback parsing
        host_name = self.config["transcript"].get("host_name", "HOST").upper()
        expert_name = self.config["transcript"].get("expert_name", "EXPERT").upper()
        beginner_name = self.config["transcript"].get("beginner_name", "BEGINNER").upper()
        
        # Also check for alternative naming in the transcript (e.g., BEN instead of BEGINNER)
        # First, look for common patterns like HOST/EXPERT/BEGINNER
        beginner_alternatives = ["BEN", "BEGINNER", "NOVICE", "LEARNER"]
        found_beginner = None
        
        for alt in beginner_alternatives:
            if alt + ":" in transcript.upper():
                found_beginner = alt.upper()
                logger.info(f"Found alternative beginner name: {found_beginner}")
                break
        
        if found_beginner and found_beginner != beginner_name:
            beginner_name = found_beginner
        
        segments = []
        
        # Check if transcript uses XML-style tags
        if "<host>" in transcript or "<expert>" in transcript or "<beginner>" in transcript:
            logger.info("Processing transcript with XML-style tags")
            
            # Use regex to extract segments while preserving special tags inside
            pattern = r'<(host|expert|beginner)>(.*?)</\1>'
            matches = re.findall(pattern, transcript, re.DOTALL)
            
            for speaker_tag, text in matches:
                # Convert to Speaker enum
                if speaker_tag == "host":
                    speaker_type = Speaker.HOST
                    speaker_name = host_name
                elif speaker_tag == "expert":
                    speaker_type = Speaker.EXPERT
                    speaker_name = expert_name
                elif speaker_tag == "beginner":
                    speaker_type = Speaker.BEGINNER
                    speaker_name = beginner_name
                else:
                    logger.warning(f"Unknown speaker tag: {speaker_tag}")
                    continue
                
                # Clean text and extract pause information
                text = text.strip()
                
                # Extract pause after this segment
                pause_match = re.search(r'<pause sec="([\d\.]+)" />', text)
                pause_after = float(pause_match.group(1)) if pause_match else 0.5
                
                # Add the segment
                segments.append((speaker_type, text, pause_after))
        else:
            # Fallback to standard format parsing
            logger.info("No XML tags found, using standard transcript format parsing")
            
            # Split by speaker lines
            lines = transcript.strip().split('\n')
            current_speaker = None
            current_text = []
            
            for line in lines:
                line = line.strip()
                
                # Skip timestamps, section markers and empty lines
                if not line or line.startswith('[') or line == '---':
                    continue
                
                # Check for speaker labels
                if line.startswith(f"{host_name}:"):
                    # Save previous segment if it exists
                    if current_speaker and current_text:
                        text = ' '.join(current_text)
                        pause_match = re.search(r'\[pause:([\d\.]+)\]', text)
                        pause_after = float(pause_match.group(1)) if pause_match else 0.5
                        segments.append((current_speaker, text, pause_after))
                    
                    # Start new segment
                    current_speaker = Speaker.HOST
                    current_text = [line[len(host_name) + 1:].strip()]
                    
                elif line.startswith(f"{expert_name}:"):
                    # Save previous segment if it exists
                    if current_speaker and current_text:
                        text = ' '.join(current_text)
                        pause_match = re.search(r'\[pause:([\d\.]+)\]', text)
                        pause_after = float(pause_match.group(1)) if pause_match else 0.5
                        segments.append((current_speaker, text, pause_after))
                    
                    # Start new segment
                    current_speaker = Speaker.EXPERT
                    current_text = [line[len(expert_name) + 1:].strip()]
                    
                elif line.startswith(f"{beginner_name}:"):
                    # Save previous segment if it exists
                    if current_speaker and current_text:
                        text = ' '.join(current_text)
                        pause_match = re.search(r'\[pause:([\d\.]+)\]', text)
                        pause_after = float(pause_match.group(1)) if pause_match else 0.5
                        segments.append((current_speaker, text, pause_after))
                    
                    # Start new segment
                    current_speaker = Speaker.BEGINNER
                    current_text = [line[len(beginner_name) + 1:].strip()]
                    
                elif current_speaker and current_text:
                    # Continue current segment
                    current_text.append(line)
            
            # Don't forget the last segment
            if current_speaker and current_text:
                text = ' '.join(current_text)
                pause_match = re.search(r'\[pause:([\d\.]+)\]', text)
                pause_after = float(pause_match.group(1)) if pause_match else 0.5
                segments.append((current_speaker, text, pause_after))
        
        if not segments:
            logger.warning("No segments found in transcript. Check transcript format.")
        else:
            logger.debug(f"Parsed transcript into {len(segments)} segments")
            
        return segments
    
    def _generate_coqui_speech(self, text, output_file, speaker_type):
        """
        Generate speech using Coqui TTS with specialized text processing
        
        Args:
            text (str): Text with special tags for Coqui
            output_file (Path): Path to save the audio file
            speaker_type (Speaker): Speaker type enum
        """
        logger.debug(f"Generating Coqui speech for {speaker_type.value}")
        
        # Get speaker-specific settings
        voice_settings = self.voice_settings[speaker_type.value]
        
        # Process the text for Coqui TTS
        processed_text = self._process_coqui_text(text, speaker_type)
        
        try:
            from TTS.api import TTS
            
            # Determine model name
            model_name = voice_settings.get("model", "tts_models/en/vctk/vits")
            
            # Determine GPU usage
            if self.use_gpu_setting == "auto":
                use_gpu = torch.cuda.is_available()
            else:
                use_gpu = self.use_gpu_setting == True
            
            # Suppress TTS output if specified
            original_stdout = sys.stdout
            null_device = open(os.devnull, 'w')
            
            try:
                # Redirect stdout to null device if suppressing output
                if self.suppress_output:
                    sys.stdout = null_device
                
                # Initialize TTS with appropriate settings
                tts = TTS(model_name=model_name,
                         progress_bar=self.show_progress,
                         gpu=use_gpu)
                
                # Prepare TTS arguments based on model type and available features
                tts_args = {
                    "text": processed_text,
                    "file_path": str(output_file),
                }
                
                # Add speaker if it's a multi-speaker model and the model supports it
                if voice_settings.get("speaker") and ("/vctk/" in model_name or "multi_speaker" in model_name):
                    tts_args["speaker"] = voice_settings.get("speaker")
                
                # Add speed/rate adjustment if supported by the model
                if voice_settings.get("speed") and hasattr(tts, "synthesizer") and hasattr(tts.synthesizer, "rate"):
                    tts.synthesizer.rate = voice_settings.get("speed")
                
                # Generate the speech
                tts.tts_to_file(**tts_args)
                
            finally:
                # Restore stdout
                if self.suppress_output:
                    sys.stdout = original_stdout
                    null_device.close()
            
            logger.debug(f"Saved Coqui audio to {output_file}")
            self._record_coqui_stats(success=True)
            
        except Exception as e:
            self._record_coqui_stats(success=False)
            logger.error(f"Error generating speech with Coqui TTS: {str(e)}")
            raise
    
    def _process_coqui_text(self, text, speaker_type):
        """
        Process text with special tags for Coqui TTS
        
        Args:
            text (str): Text with special tags
            speaker_type (Speaker): Speaker type enum
            
        Returns:
            str: Processed text for Coqui TTS
        """
        # Get speaker-specific characteristics
        voice_settings = self.voice_settings[speaker_type.value]
        
        # Convert <pause sec="X" /> to proper pauses
        # For Coqui, we'll just add commas and periods as Coqui doesn't directly support SSML
        processed_text = text
        
        # Remove XML-like tags while preserving the content
        # 1. Handle emphasis tags - we'll capitalize for emphasis
        processed_text = re.sub(r'<emphasis>(.*?)</emphasis>', 
                               lambda m: m.group(1).upper(), 
                               processed_text)
        
        # 2. Handle pause tags - replace with commas or periods based on duration
        processed_text = re.sub(r'<pause sec="([\d\.]+)" />', 
                               lambda m: "..." if float(m.group(1)) > 0.7 else ", ", 
                               processed_text)
        
        # 3. Handle break tags - replace with commas or periods based on strength
        processed_text = re.sub(r'<break strength="weak" />', ", ", processed_text)
        processed_text = re.sub(r'<break strength="medium" />', ". ", processed_text)
        processed_text = re.sub(r'<break strength="strong" />', ". ", processed_text)
        
        # Clean up the text
        processed_text = processed_text.strip()
        processed_text = re.sub(r' +', ' ', processed_text)
        processed_text = re.sub(r'\.\.\.\.+', '...', processed_text)
        processed_text = re.sub(r',,+', ',', processed_text)
        processed_text = re.sub(r'\.\.+', '.', processed_text)
        
        return processed_text


def generate_coqui_speech(transcript, output_dir, config):
    """
    Generate speech from transcript using Coqui-specific processing
    
    Args:
        transcript (str): The podcast transcript specially formatted for Coqui
        output_dir (str or Path): Directory to save audio files
        config (dict): Configuration dictionary
    
    Returns:
        list: List of audio file paths with metadata
    """
    generator = CoquiTTSGenerator(config)
    audio_files = generator.generate(transcript, output_dir)
    
    logger.info(f"Generated {len(audio_files)} audio segments with Coqui")
    return audio_files
