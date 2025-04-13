#!/usr/bin/env python3
"""
Podcast Generator - Create educational podcasts from a given subject
-------------------------------------------------------------------
This script generates an educational podcast with a host, expert, and beginner
discussing a given subject. It follows several steps:
1. Research the subject
2. Generate a transcript
3. Convert the transcript to speech
4. Assemble the final podcast audio

Usage:
    python main.py "Subject to discuss"
"""

import os
import sys
import argparse
import time
import logging
import platform
from datetime import datetime
from pathlib import Path

from src.utils.config_loader import load_config
from src.utils.logging_utils import setup_logging
from src.research import generate_research
from src.transcript import generate_transcript
from src.tts import generate_speech
from src.assembler import assemble_podcast
from src.utils.api_stats import validate_api_key

# Import Coqui-specific modules
from src.coqui.transcript import generate_coqui_transcript
from src.coqui.tts import generate_coqui_speech


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Generate an educational podcast on a given subject")
    parser.add_argument("subject", help="The subject to discuss in the podcast")
    
    return parser.parse_args()


def check_python_version():
    """Check Python version and warn if using 3.13+."""
    py_version = platform.python_version_tuple()
    
    if int(py_version[0]) == 3 and int(py_version[1]) >= 13:
        print("\n⚠️  WARNING: Running with Python 3.13+ detected.")
        print("    Some audio processing features may be limited due to module changes.")
        print("    Core functionality will work as long as FFmpeg is installed.\n")


def main():
    """Main execution function."""
    # Check Python version
    check_python_version()
    
    # Parse arguments
    args = parse_args()
    
    # Create timestamp folder
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    output_dir = Path(f"data/{timestamp}")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Setup basic logging first so we can log config errors
    log_file = output_dir / "processing.log"
    setup_logging("INFO", log_file)
    
    logger = logging.getLogger(__name__)
    
    # Load configuration
    try:
        config = load_config()
        
        # Ensure prompt_paths exists in config
        if "prompt_paths" not in config:
            config["prompt_paths"] = {}
            # Look for common prompt locations
            if os.path.exists("config/prompts/research_prompt.txt"):
                config["prompt_paths"]["research"] = "config/prompts/research_prompt.txt"
            if os.path.exists("config/prompts/transcript_prompt.txt"):
                config["prompt_paths"]["transcript"] = "config/prompts/transcript_prompt.txt"
            
            logger.warning("prompt_paths not found in config, using defaults")
        
        # Update logging level based on config
        setup_logging(config["logging"]["level"], log_file)
    except Exception as e:
        print(f"Error loading configuration: {str(e)}")
        sys.exit(1)

    # Validate API keys
    try:
        # Verify API keys section exists
        if "api_keys" not in config:
            raise ValueError("Missing 'api_keys' section in configuration")
            
        # Validate required API keys
        validate_api_key(config["api_keys"].get("openrouter"), "OpenRouter")
        validate_api_key(config["api_keys"].get("elevenlabs"), "ElevenLabs")
    except ValueError as e:
        logger.error(f"API validation failed: {str(e)}")
        print(f"\n❌ Configuration Error: {str(e)}")
        print("    Please check your config file and .env settings")
        sys.exit(1)
        
    logger.info(f"Starting podcast generation for subject: {args.subject}")
    logger.info(f"Output directory: {output_dir}")
    
    try:
        # Step 1: Research the subject
        logger.info("Step 1: Researching the subject")
        research_file = output_dir / "research.md"
        generate_research(args.subject, research_file, config)
        
        # Step 2: Generate transcript
        logger.info("Step 2: Generating the transcript")
        transcript_file = output_dir / "transcript.txt"
        
        # Check if we're using Coqui TTS
        using_coqui = config["tts"]["provider"].lower() == "coqui"
        
        if using_coqui:
            # Use Coqui-specific transcript generation
            logger.info("Using Coqui-specific transcript generation")
            transcript = generate_coqui_transcript(args.subject, research_file, output_dir, config)
        else:
            # Use standard transcript generation
            transcript = generate_transcript(research_file, transcript_file, config)
        
        # Step 3: Generate speech
        logger.info("Step 3: Generating speech")
        
        if using_coqui:
            # Use Coqui-specific speech generation
            logger.info("Using Coqui-specific speech generation")
            audio_files = generate_coqui_speech(transcript, output_dir, config)
        else:
            # Use standard speech generation
            audio_files = generate_speech(transcript, output_dir, config)
        
        # Step 4: Assemble podcast
        logger.info("Step 4: Assembling the podcast")
        podcast_file = output_dir / "podcast.mp3"
        assemble_podcast(audio_files, podcast_file, config)
        
        logger.info(f"Podcast generated successfully: {podcast_file}")
        print(f"\nPodcast generated successfully: {podcast_file}")
        
    except Exception as e:
        logger.error(f"Error during podcast generation: {str(e)}", exc_info=True)
        print(f"\nError: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
