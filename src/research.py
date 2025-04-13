"""
Research Module
------------
Generate research content for the podcast subject
"""

import os
import logging
import json
import requests
from pathlib import Path

from src.utils.file_utils import save_text_file, get_prompt_content
from src.utils.progress import ProgressBar


logger = logging.getLogger(__name__)


class ResearchGenerator:
    """Research content generator class"""
    
    def __init__(self, config):
        """
        Initialize the research generator
        
        Args:
            config (dict): Configuration dictionary
        """
        self.config = config
        self.provider = config["research"]["provider"]
        self.model = config["research"]["model"]
        self.api_key = config["api_keys"].get(self.provider)
        
        if not self.api_key:
            raise ValueError(f"API key for {self.provider} not found in configuration")
        
        # Get the prompt template
        self.prompt_template = get_prompt_content("research_prompt")
        
        logger.debug(f"Initialized research generator with provider: {self.provider}, model: {self.model}")
    
    def generate(self, subject):
        """
        Generate research content for the given subject
        
        Args:
            subject (str): The subject to research
            
        Returns:
            str: The generated research content
        """
        logger.info(f"Generating research for subject: {subject}")
        
        # Format the prompt
        prompt = self.prompt_template.format(subject=subject)
        
        # Create progress bar
        progress = ProgressBar(total=1, desc="Researching", unit="step")
        
        try:
            # Generate content based on the provider
            if self.provider == "ollama":
                content = self._generate_ollama(prompt)
            elif self.provider == "openrouter":
                content = self._generate_openrouter(prompt)
            elif self.provider == "deepseek":
                content = self._generate_deepseek(prompt)
            else:
                raise ValueError(f"Unsupported provider: {self.provider}")
            
            progress.update(1, "Research completed")
            return content
            
        except Exception as e:
            logger.error(f"Error generating research: {str(e)}")
            raise
        finally:
            progress.close()
    
    def _generate_ollama(self, prompt):
        """Generate content using Ollama"""
        logger.debug("Generating content with Ollama")
        
        url = self.config.get("api_urls", {}).get("ollama", "http://localhost:11434/api/generate")
        
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": self.config["research"].get("temperature", 0.7),
                "max_tokens": self.config["research"].get("max_tokens", 4000)
            }
        }
        
        headers = {
            "Content-Type": "application/json"
        }
        
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()
        
        return response.json()["response"]
    
    def _generate_openrouter(self, prompt):
        """Generate content using OpenRouter"""
        logger.debug("Generating content with OpenRouter")
        
        url = self.config.get("api_urls", {}).get("openrouter", "https://openrouter.ai/api/v1/chat/completions")
        
        payload = {
            "model": self.model,
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "temperature": self.config["research"].get("temperature", 0.7),
            "max_tokens": self.config["research"].get("max_tokens", 4000)
        }
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
            "HTTP-Referer": self.config.get("api_urls", {}).get("referer", "http://localhost")
        }
        
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()
        
        return response.json()["choices"][0]["message"]["content"]
    
    def _generate_deepseek(self, prompt):
        """Generate content using DeepSeek"""
        logger.debug("Generating content with DeepSeek")
        
        url = self.config.get("api_urls", {}).get("deepseek", "https://api.deepseek.com/v1/chat/completions")
        
        payload = {
            "model": self.model,
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "temperature": self.config["research"].get("temperature", 0.7),
            "max_tokens": self.config["research"].get("max_tokens", 4000)
        }
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()
        
        return response.json()["choices"][0]["message"]["content"]


def generate_research(subject, output_file, config):
    """
    Generate research content for the given subject and save to file
    
    Args:
        subject (str): The subject to research
        output_file (str or Path): Path to save the research content
        config (dict): Configuration dictionary
    
    Returns:
        str: Path to the saved research file
    """
    generator = ResearchGenerator(config)
    content = generator.generate(subject)
    
    # Save the content to a file
    save_text_file(content, output_file)
    
    logger.info(f"Research content saved to {output_file}")
    return output_file
