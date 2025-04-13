"""
Coqui-specific Transcript Generator
-----------------------------------
Creates transcripts specifically formatted for optimal Coqui TTS processing
"""

import os
import logging
import re
import json
import tempfile
from pathlib import Path

from src.transcript import generate_transcript as original_generate_transcript

logger = logging.getLogger(__name__)


def generate_coqui_transcript(topic, research_file, output_dir, config):
    """
    Generate a transcript specially formatted for Coqui TTS
    
    Args:
        topic (str): The podcast topic
        research_file (str or Path): Path to the research file
        output_dir (str or Path): Directory to save the transcript
        config (dict): Configuration dictionary
    
    Returns:
        str: The generated transcript text
    """
    logger.info("Generating Coqui-specific transcript")
    
    # Load research content if it's a file path
    if isinstance(research_file, (str, Path)) and os.path.isfile(research_file):
        with open(research_file, 'r', encoding='utf-8') as f:
            research = f.read()
    else:
        # It might already be the content
        research = str(research_file)
    
    # Check if we should use a specialized prompt
    original_prompt_path = config.get("prompt_paths", {}).get("transcript")
    
    # Handle the case where prompt_paths is not configured
    if original_prompt_path is None:
        # Look in common locations for the prompt
        possible_paths = [
            "config/prompts/transcript_prompt.txt",
            "./config/prompts/transcript_prompt.txt"
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                original_prompt_path = path
                break
        
        if original_prompt_path is None:
            logger.warning("Could not find transcript prompt path in config")
            original_prompt_path = "config/prompts/transcript_prompt.txt"  # Default fallback
    
    # Look for Coqui-specific prompt
    coqui_prompt_dir = os.path.join(os.path.dirname(original_prompt_path), "coqui")
    coqui_prompt_path = os.path.join(coqui_prompt_dir, "transcript_prompt.txt")
    
    if os.path.exists(coqui_prompt_path):
        logger.info(f"Using Coqui-specific transcript prompt: {coqui_prompt_path}")
        # Temporarily override the prompt path
        original_path = config.get("prompt_paths", {}).get("transcript")
        if "prompt_paths" not in config:
            config["prompt_paths"] = {}
        config["prompt_paths"]["transcript"] = coqui_prompt_path
        
        # Generate the transcript using the original function but with the Coqui prompt
        transcript_file = Path(output_dir) / "transcript.txt"
        try:
            transcript = original_generate_transcript(research_file, transcript_file, config)
            logger.info("Successfully generated transcript using Coqui prompt")
        except Exception as e:
            logger.error(f"Error generating transcript with Coqui prompt: {str(e)}")
            # Fall back to standard transcript if Coqui prompt fails
            config["prompt_paths"]["transcript"] = original_path
            transcript_file = Path(output_dir) / "transcript.txt"
            transcript = original_generate_transcript(research_file, transcript_file, config)
            transcript = convert_to_coqui_format(transcript, config)
        
        # Restore the original prompt path
        config["prompt_paths"]["transcript"] = original_path
    else:
        logger.warning(f"Coqui-specific prompt not found at {coqui_prompt_path}, converting standard transcript instead")
        # Generate a standard transcript and convert it
        transcript_file = Path(output_dir) / "transcript.txt"
        transcript = original_generate_transcript(research_file, transcript_file, config)
        transcript = convert_to_coqui_format(transcript, config)
    
    # Save as a Coqui-specific transcript
    output_path = Path(output_dir) / "transcript_coqui.txt"
    
    # Always convert to Coqui format to ensure it's properly formatted
    # This handles cases where the LLM didn't follow the XML tag format
    transcript = convert_to_coqui_format(transcript, config)
    
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(transcript)
    
    logger.info(f"Saved Coqui transcript to {output_path}")
    return transcript


def convert_to_coqui_format(standard_transcript, config):
    """
    Convert a standard transcript to Coqui-specific format
    
    Args:
        standard_transcript (str): Standard transcript text or path to transcript file
        config (dict): Configuration dictionary
    
    Returns:
        str: Coqui-formatted transcript
    """
    logger.info("Converting standard transcript to Coqui format")
    
    # Check if standard_transcript is a file path or actual text
    if isinstance(standard_transcript, (str, Path)) and os.path.isfile(standard_transcript):
        with open(standard_transcript, 'r', encoding='utf-8') as f:
            standard_transcript = f.read()
    
    # Get speaker names from config
    host_name = config["transcript"].get("host_name", "HOST").upper()
    expert_name = config["transcript"].get("expert_name", "EXPERT").upper()
    beginner_name = config["transcript"].get("beginner_name", "BEGINNER").upper()
    
    # Remove timestamps and section headers
    transcript = re.sub(r'\[\d{2}:\d{2}:\d{2}\] [A-Z ]+\n', '', standard_transcript)
    transcript = re.sub(r'^---$', '', transcript, flags=re.MULTILINE)
    
    # Convert speaker tags to XML format
    transcript = re.sub(rf'^{host_name}: (.+?)(?=\n\n|$)', r'<host>\1</host>', 
                        transcript, flags=re.MULTILINE | re.DOTALL)
    transcript = re.sub(rf'^{expert_name}: (.+?)(?=\n\n|$)', r'<expert>\1</expert>', 
                        transcript, flags=re.MULTILINE | re.DOTALL)
    transcript = re.sub(rf'^{beginner_name}: (.+?)(?=\n\n|$)', r'<beginner>\1</beginner>', 
                        transcript, flags=re.MULTILINE | re.DOTALL)
    
    # Convert pause markers
    transcript = re.sub(r'\[pause:([\d\.]+)\]', r'<pause sec="\1" />', transcript)
    
    # Remove extra newlines
    transcript = re.sub(r'\n\n+', '\n', transcript)
    
    # Add emphasis to important words
    important_words = ["critical", "important", "essential", "key", "crucial", "significant"]
    for word in important_words:
        transcript = re.sub(rf'\b({word})\b', r'<emphasis>\1</emphasis>', 
                           transcript, flags=re.IGNORECASE)
    
    return transcript
