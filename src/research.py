"""
Research Module
------------
Generate research content for the podcast subject
"""

import os
import logging
import json
import requests
import time
from pathlib import Path


from src.utils.api_stats import handle_api_error

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
        
        start_time = time.time()
        success = False
        error_type = None
        tokens_in = len(prompt.split())
        tokens_out = 0
        
        try:
            response = requests.post(url, json=payload, headers=headers, timeout=60)
            response.raise_for_status()
            
            response_data = response.json()
            content = response_data["response"]
            tokens_out = len(content.split())
            success = True
            
            return content
            
        except requests.exceptions.Timeout:
            error_type = "timeout"
            logger.error(f"Timeout while connecting to Ollama API")
            raise TimeoutError(f"Timeout while connecting to Ollama API")
            
        except requests.exceptions.ConnectionError:
            error_type = "connection_error"
            logger.error(f"Could not connect to Ollama API. Is Ollama running?")
            raise ConnectionError(f"Could not connect to Ollama API. Is Ollama running?")
            
        except requests.exceptions.HTTPError as e:
            error_message, error_type = handle_api_error(response, "Ollama", "research generation")
            logger.error(error_message)
            raise Exception(error_message) from e
            
        except KeyError as e:
            error_type = "invalid_response"
            logger.error(f"Invalid response from Ollama API: {str(e)}")
            raise ValueError(f"Invalid response from Ollama API: {str(e)}")
            
        except Exception as e:
            error_type = "unknown"
            logger.error(f"Error generating content with Ollama: {str(e)}")
            raise
            
        finally:
            latency = time.time() - start_time
            self.api_stats.record_request(
                provider="ollama",
                model=self.model,
                request_type="research",
                success=success,
                error_type=error_type,
                tokens_in=tokens_in,
                tokens_out=tokens_out,
                latency=latency
            )
    
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
        
        start_time = time.time()
        success = False
        error_type = None
        tokens_in = len(prompt.split())
        tokens_out = 0
        
        try:
            response = requests.post(url, json=payload, headers=headers, timeout=120)
            response.raise_for_status()
            
            response_data = response.json()
            
            # Check for expected response format
            if "choices" not in response_data or not response_data["choices"]:
                raise ValueError("Invalid response format from OpenRouter API: 'choices' not found")
                
            content = response_data["choices"][0]["message"]["content"]
            
            # Get token usage if available
            if "usage" in response_data:
                tokens_in = response_data["usage"].get("prompt_tokens", tokens_in)
                tokens_out = response_data["usage"].get("completion_tokens", len(content.split()))
            else:
                tokens_out = len(content.split())
                
            success = True
            return content
            
        except requests.exceptions.Timeout:
            error_type = "timeout"
            logger.error(f"Timeout while connecting to OpenRouter API")
            raise TimeoutError(f"Timeout while connecting to OpenRouter API")
            
        except requests.exceptions.ConnectionError:
            error_type = "connection_error"
            logger.error(f"Could not connect to OpenRouter API")
            raise ConnectionError(f"Could not connect to OpenRouter API")
            
        except requests.exceptions.HTTPError as e:
            error_message, error_type = handle_api_error(response, "OpenRouter", "research generation")
            logger.error(error_message)
            raise Exception(error_message) from e
            
        except (KeyError, ValueError) as e:
            error_type = "invalid_response"
            logger.error(f"Invalid response from OpenRouter API: {str(e)}")
            raise ValueError(f"Invalid response from OpenRouter API: {str(e)}")
            
        except Exception as e:
            error_type = "unknown"
            logger.error(f"Error generating content with OpenRouter: {str(e)}")
            raise
            
        finally:
            latency = time.time() - start_time
            self.api_stats.record_request(
                provider="openrouter",
                model=self.model,
                request_type="research",
                success=success,
                error_type=error_type,
                tokens_in=tokens_in,
                tokens_out=tokens_out,
                latency=latency
            )
    
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
        
        start_time = time.time()
        success = False
        error_type = None
        tokens_in = len(prompt.split())
        tokens_out = 0
        
        try:
            response = requests.post(url, json=payload, headers=headers, timeout=120)
            response.raise_for_status()
            
            response_data = response.json()
            
            # Check for expected response format
            if "choices" not in response_data or not response_data["choices"]:
                raise ValueError("Invalid response format from DeepSeek API: 'choices' not found")
                
            content = response_data["choices"][0]["message"]["content"]
            
            # Get token usage if available
            if "usage" in response_data:
                tokens_in = response_data["usage"].get("prompt_tokens", tokens_in)
                tokens_out = response_data["usage"].get("completion_tokens", len(content.split()))
            else:
                tokens_out = len(content.split())
                
            success = True
            return content
            
        except requests.exceptions.Timeout:
            error_type = "timeout"
            logger.error(f"Timeout while connecting to DeepSeek API")
            raise TimeoutError(f"Timeout while connecting to DeepSeek API")
            
        except requests.exceptions.ConnectionError:
            error_type = "connection_error"
            logger.error(f"Could not connect to DeepSeek API")
            raise ConnectionError(f"Could not connect to DeepSeek API")
            
        except requests.exceptions.HTTPError as e:
            error_message, error_type = handle_api_error(response, "DeepSeek", "research generation")
            logger.error(error_message)
            raise Exception(error_message) from e
            
        except (KeyError, ValueError) as e:
            error_type = "invalid_response"
            logger.error(f"Invalid response from DeepSeek API: {str(e)}")
            raise ValueError(f"Invalid response from DeepSeek API: {str(e)}")
            
        except Exception as e:
            error_type = "unknown"
            logger.error(f"Error generating content with DeepSeek: {str(e)}")
            raise
            
        finally:
            latency = time.time() - start_time
            self.api_stats.record_request(
                provider="deepseek",
                model=self.model,
                request_type="research",
                success=success,
                error_type=error_type,
                tokens_in=tokens_in,
                tokens_out=tokens_out,
                latency=latency
            )


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
