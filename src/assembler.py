"""
Podcast Assembler Module
---------------------
Assemble audio segments into a complete podcast
"""

import os
import logging
import tempfile
import subprocess
from pathlib import Path

# Handle Python 3.13+ compatibility
try:
    import pydub
    from pydub import AudioSegment
    from pydub.silence import generate_silence
    PYDUB_AVAILABLE = True
except (ImportError, ModuleNotFoundError):
    PYDUB_AVAILABLE = False
    # Define fallback class for when pydub is not available
    class AudioSegment:
        @staticmethod
        def silent(duration=0):
            return AudioSegment(0)
            
        @staticmethod
        def from_file(file_path, format=None):
            return AudioSegment(os.path.getsize(file_path))
            
        def __init__(self, size=0):
            self.size = size
            self.dBFS = -20  # Default value
            
        def __add__(self, other):
            if isinstance(other, AudioSegment):
                return AudioSegment(self.size + other.size)
            return self
            
        def apply_gain(self, gain):
            return self
            
        def fade_in(self, duration):
            return self
            
        def fade_out(self, duration):
            return self
            
        def export(self, out_f, format=None, bitrate=None, parameters=None):
            with open(out_f, 'wb') as f:
                f.write(b'')
            return out_f
            
        def __len__(self):
            return self.size

    def generate_silence(duration=1000):
        return AudioSegment(duration)

from src.utils.progress import ProgressBar


logger = logging.getLogger(__name__)


class PodcastAssembler:
    """Podcast assembler class"""
    
    def __init__(self, config):
        """
        Initialize the podcast assembler
        
        Args:
            config (dict): Configuration dictionary
        """
        self.config = config
        
        # Get audio settings
        self.audio_settings = config.get("assembler", {})
        self.sample_rate = self.audio_settings.get("sample_rate", 44100)
        self.bitrate = self.audio_settings.get("bitrate", "192k")
        
        logger.debug("Initialized podcast assembler")
        
        # Check if pydub is available
        if not PYDUB_AVAILABLE:
            logger.warning("pydub library not fully available. Using fallback mode with limited functionality.")
            logger.warning("For full audio processing support, consider using Python 3.8-3.12 or install pyaudioop package.")
    
    def assemble(self, audio_files, output_file):
        """
        Assemble audio segments into a complete podcast
        
        Args:
            audio_files (list): List of audio file dictionaries with metadata
            output_file (Path): Path to save the assembled podcast
        """
        logger.info("Assembling podcast audio")
        
        # Check if there are any audio files to process
        if not audio_files:
            logger.error("No audio files to assemble")
            raise ValueError("Cannot assemble empty list of audio files")
        
        # Create progress bar
        progress = ProgressBar(
            total=len(audio_files) + 2,  # Files + intro + outro
            desc="Assembling podcast", 
            unit="segments"
        )
        
        try:
            # Create empty audio segment
            podcast = AudioSegment.silent(duration=0)
            
            # Add intro music if specified
            if "intro_music" in self.audio_settings:
                intro_path = self.audio_settings["intro_music"]
                if os.path.exists(intro_path):
                    logger.debug(f"Adding intro music: {intro_path}")
                    intro = AudioSegment.from_file(intro_path)
                    
                    # Apply fade in/out to intro
                    fade_in = self.audio_settings.get("intro_fade_in", 1000)
                    fade_out = self.audio_settings.get("intro_fade_out", 2000)
                    intro = intro.fade_in(fade_in).fade_out(fade_out)
                    
                    # Add intro to podcast
                    podcast += intro
                    
                    # Add silence after intro
                    silence_after_intro = self.audio_settings.get("silence_after_intro", 1000)
                    podcast += generate_silence(silence_after_intro)
                    
                    progress.update(1, "Added intro music")
                else:
                    logger.warning(f"Intro music file not found: {intro_path}")
                    progress.update(1, "Skipped intro music (file not found)")
            else:
                progress.update(1, "No intro music specified")
            
            # Process each audio file
            for i, file_info in enumerate(audio_files):
                file_path = file_info["path"]
                speaker = file_info["speaker"]
                pause_after = file_info.get("pause_after", 0.3)
                
                try:
                    # Load audio file
                    segment = AudioSegment.from_file(file_path)
                    
                    # Apply volume normalization if enabled
                    if self.audio_settings.get("normalize_volume", True):
                        target_dBFS = self.audio_settings.get("target_dBFS", -16)
                        change_in_dBFS = target_dBFS - segment.dBFS
                        segment = segment.apply_gain(change_in_dBFS)
                    
                    # Add segment to podcast
                    podcast += segment
                    
                    # Add pause after segment
                    pause_ms = int(pause_after * 1000)
                    podcast += generate_silence(pause_ms)
                    
                    progress.update(1, f"Added {speaker} segment {i+1}/{len(audio_files)}")
                    
                except Exception as e:
                    logger.error(f"Error processing audio file {file_path}: {str(e)}")
                    progress.update(1, f"Error adding segment {i+1}")
            
            # Add outro music if specified
            if "outro_music" in self.audio_settings:
                outro_path = self.audio_settings["outro_music"]
                if os.path.exists(outro_path):
                    logger.debug(f"Adding outro music: {outro_path}")
                    outro = AudioSegment.from_file(outro_path)
                    
                    # Apply fade in/out to outro
                    fade_in = self.audio_settings.get("outro_fade_in", 2000)
                    fade_out = self.audio_settings.get("outro_fade_out", 5000)
                    outro = outro.fade_in(fade_in).fade_out(fade_out)
                    
                    # Add silence before outro
                    silence_before_outro = self.audio_settings.get("silence_before_outro", 1000)
                    podcast += generate_silence(silence_before_outro)
                    
                    # Add outro to podcast
                    podcast += outro
                    
                    progress.update(1, "Added outro music")
                else:
                    logger.warning(f"Outro music file not found: {outro_path}")
                    progress.update(1, "Skipped outro music (file not found)")
            else:
                progress.update(1, "No outro music specified")
            
            # Export final podcast
            logger.info(f"Exporting podcast to {output_file}")
            
            # If pydub isn't available, use ffmpeg directly via subprocess as a fallback
            if not PYDUB_AVAILABLE:
                self._fallback_concat_files(audio_files, output_file)
            else:
                podcast.export(
                    output_file,
                    format="mp3",
                    bitrate=self.bitrate,
                    parameters=["-ar", str(self.sample_rate)]
                )
            
            # Calculate duration
            if PYDUB_AVAILABLE:
                duration_sec = len(podcast) / 1000
                duration_min = duration_sec / 60
                logger.info(f"Podcast duration: {duration_min:.2f} minutes ({duration_sec:.2f} seconds)")
            
            return output_file
            
        except Exception as e:
            logger.error(f"Error assembling podcast: {str(e)}")
            raise
        finally:
            progress.close()
    
    def _fallback_concat_files(self, audio_files, output_file):
        """
        Fallback method to concatenate audio files using ffmpeg directly
        
        Args:
            audio_files (list): List of audio file dictionaries with metadata
            output_file (Path): Path to save the assembled podcast
        """
        logger.info("Using ffmpeg directly to concatenate audio files (fallback mode)")
        
        # Check if there are any audio files to process
        if not audio_files:
            logger.error("No audio files to concatenate")
            raise ValueError("Cannot concatenate empty list of audio files")
            
        # First verify that all files exist
        missing_files = []
        for file_info in audio_files:
            file_path = file_info["path"]
            if not os.path.exists(file_path):
                missing_files.append(file_path)
        
        if missing_files:
            logger.error(f"Missing {len(missing_files)} audio files: {missing_files[:3]}...")
            raise FileNotFoundError(f"Missing {len(missing_files)} audio files. First few: {missing_files[:3]}")
        
        # Option 1: Try concat demuxer first (faster but requires compatible formats)
        try:
            self._concat_with_concat_demuxer(audio_files, output_file)
            return
        except Exception as e:
            logger.warning(f"Concat demuxer failed: {str(e)}. Trying filter_complex method...")
        
        # Option 2: Try filter_complex method (more compatible but slower)
        try:
            self._concat_with_filter_complex(audio_files, output_file)
        except Exception as e:
            logger.error(f"All ffmpeg concatenation methods failed: {str(e)}")
            raise
    
    def _concat_with_concat_demuxer(self, audio_files, output_file):
        """Concatenate using ffmpeg concat demuxer"""
        # Check if there are any audio files to process
        if not audio_files:
            logger.error("No audio files to concatenate")
            raise ValueError("Cannot concatenate empty list of audio files")
            
        # Create a temporary file list for ffmpeg
        with tempfile.NamedTemporaryFile('w', suffix='.txt', delete=False) as f:
            file_list_path = f.name
            for file_info in audio_files:
                file_path = file_info["path"]
                f.write(f"file '{os.path.abspath(file_path)}'\n")
        
        try:
            # Use ffmpeg to concatenate the files
            cmd = [
                'ffmpeg', '-y', '-f', 'concat', '-safe', '0', 
                '-i', file_list_path, '-c', 'copy', str(output_file)
            ]
            
            # Run with detailed output to diagnose issues
            result = subprocess.run(cmd, check=False, capture_output=True, text=True)
            
            if result.returncode != 0:
                logger.warning(f"ffmpeg concat demuxer returned code {result.returncode}")
                logger.debug(f"ffmpeg stderr: {result.stderr}")
                raise subprocess.CalledProcessError(result.returncode, cmd, 
                                                  output=result.stdout, stderr=result.stderr)
                
            logger.info(f"Successfully concatenated {len(audio_files)} audio files with concat demuxer")
            
        finally:
            # Clean up the temporary file
            if os.path.exists(file_list_path):
                os.remove(file_list_path)
    
    def _concat_with_filter_complex(self, audio_files, output_file):
        """Concatenate using ffmpeg filter_complex (more compatible)"""
        # Check if there are any audio files to process
        if not audio_files:
            logger.error("No audio files to concatenate")
            raise ValueError("Cannot concatenate empty list of audio files")
            
        # Build the filter_complex command
        inputs = []
        for file_info in audio_files:
            file_path = file_info["path"]
            inputs.extend(['-i', file_path])
        
        # Create the filter_complex string
        filter_parts = []
        for i in range(len(audio_files)):
            filter_parts.append(f"[{i}:0]")
        
        filter_complex = ''.join(filter_parts) + f"concat=n={len(audio_files)}:v=0:a=1[out]"
        
        # Assemble the full command
        cmd = [
            'ffmpeg', '-y',
            *inputs,
            '-filter_complex', filter_complex,
            '-map', '[out]',
            '-ar', str(self.sample_rate),
            '-b:a', self.bitrate,
            str(output_file)
        ]
        
        # Run with detailed output
        result = subprocess.run(cmd, check=False, capture_output=True, text=True)
        
        if result.returncode != 0:
            logger.error(f"ffmpeg filter_complex failed with code {result.returncode}")
            logger.debug(f"ffmpeg stderr: {result.stderr}")
            raise subprocess.CalledProcessError(result.returncode, cmd, 
                                              output=result.stdout, stderr=result.stderr)
            
        logger.info(f"Successfully concatenated {len(audio_files)} audio files with filter_complex")


def assemble_podcast(audio_files, output_file, config):
    """
    Assemble audio segments into a complete podcast
    
    Args:
        audio_files (list): List of audio file paths with metadata
        output_file (str or Path): Path to save the assembled podcast
        config (dict): Configuration dictionary
    
    Returns:
        Path: Path to the assembled podcast
    """
    assembler = PodcastAssembler(config)
    return assembler.assemble(audio_files, output_file)
