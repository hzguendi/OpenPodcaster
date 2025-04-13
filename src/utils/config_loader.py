"""
Configuration Loader Module
--------------------------
Loads configuration from conf.yml and .env files
"""

import os
import yaml
from pathlib import Path
from dotenv import load_dotenv


def load_config():
    """
    Load configuration from conf.yml and environment variables (.env)
    
    Returns:
        dict: Combined configuration dictionary
    """
    # Load .env file
    load_dotenv()
    
    # Get base directory
    base_dir = Path(__file__).parent.parent.parent
    
    # Load YAML config
    config_path = base_dir / "config" / "conf.yml"
    
    try:
        with open(config_path, "r") as config_file:
            config = yaml.safe_load(config_file)
    except FileNotFoundError:
        raise FileNotFoundError(f"Configuration file not found: {config_path}")
    except yaml.YAMLError as e:
        raise ValueError(f"Error parsing configuration file: {str(e)}")
    
    # Override with environment variables where applicable
    if "api_keys" not in config:
        config["api_keys"] = {}
    
    # Map environment variables to config
    env_mapping = {
        "OLLAMA_API_KEY": ("api_keys", "ollama"),
        "OPENROUTER_API_KEY": ("api_keys", "openrouter"),
        "DEEPSEEK_API_KEY": ("api_keys", "deepseek"),
        "GEMINI_API_KEY": ("api_keys", "gemini"),
        "ELEVENLABS_API_KEY": ("api_keys", "elevenlabs"),
    }
    
    for env_var, config_path in env_mapping.items():
        env_value = os.getenv(env_var)
        if env_value:
            # Create nested dictionaries if needed
            current = config
            for part in config_path[:-1]:
                if part not in current:
                    current[part] = {}
                current = current[part]
            
            # Set the value
            current[config_path[-1]] = env_value
    
    return config
