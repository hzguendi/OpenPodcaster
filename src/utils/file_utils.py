"""
File Utilities
-----------
Utilities for file operations
"""

import os
import logging
from pathlib import Path


logger = logging.getLogger(__name__)


def ensure_directory(directory):
    """
    Ensure a directory exists, create it if it doesn't
    
    Args:
        directory (str or Path): Directory path
    
    Returns:
        Path: Path object for the directory
    """
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def save_text_file(content, file_path):
    """
    Save text content to a file
    
    Args:
        content (str): Content to save
        file_path (str or Path): Path to save the file
    """
    file_path = Path(file_path)
    ensure_directory(file_path.parent)
    
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        logger.debug(f"Saved file: {file_path}")
    except Exception as e:
        logger.error(f"Error saving file {file_path}: {str(e)}")
        raise


def read_text_file(file_path):
    """
    Read text content from a file
    
    Args:
        file_path (str or Path): Path to the file
    
    Returns:
        str: File content
    """
    file_path = Path(file_path)
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        logger.debug(f"Read file: {file_path}")
        return content
    except Exception as e:
        logger.error(f"Error reading file {file_path}: {str(e)}")
        raise


def get_prompt_content(prompt_name):
    """
    Get the content of a prompt template
    
    Args:
        prompt_name (str): Name of the prompt file (without extension)
    
    Returns:
        str: Prompt content
    """
    base_dir = Path(__file__).parent.parent.parent
    prompt_path = base_dir / "config" / "prompts" / f"{prompt_name}.txt"
    
    return read_text_file(prompt_path)
