"""
Transcript Module
--------------
Generate podcast transcript from research content
"""

import os
import logging
import json
import requests
import time
from pathlib import Path


from src.utils.api_stats import handle_api_error, APIStatsTracker

from src.utils.file_utils import read_text_file, save_text_file, get_prompt_content
from src.utils.progress import ProgressBar


logger = logging.getLogger(__name__)


class TranscriptGenerator:
    """Podcast transcript generator class"""
    
    def __init__(self, config):
        """
        Initialize the transcript generator
        
        Args:
            config (dict): Configuration dictionary
        """
        self.config = config
        self.provider = config["transcript"]["provider"]
        self.model = config["transcript"]["model"]
        self.api_key = config["api_keys"].get(self.provider)
        
        if not self.api_key and self.provider != "ollama":
            raise ValueError(f"API key for {self.provider} not found in configuration")
        
        # Get the prompt template
        self.prompt_template = get_prompt_content("transcript_prompt")
        
        # Character limit for transcript
        self.char_limit = config["transcript"].get("character_limit", 10000)
        
        # Initialize API stats tracker
        self.api_stats = APIStatsTracker(config)
        
        logger.debug(f"Initialized transcript generator with provider: {self.provider}, model: {self.model}")
    
    def generate(self, research_content):
        """
        Generate podcast transcript from research content
        
        Args:
            research_content (str): The research content
            
        Returns:
            str: The generated transcript
        """
        logger.info("Generating podcast transcript")
        
        # Format the prompt with research content
        prompt = self.prompt_template.format(
            research=research_content,
            char_limit=self.char_limit,
            host_name=self.config["transcript"].get("host_name", "Host"),
            expert_name=self.config["transcript"].get("expert_name", "Expert"),
            beginner_name=self.config["transcript"].get("beginner_name", "Beginner")
        )
        
        # Create progress bar
        progress = ProgressBar(total=1, desc="Generating transcript", unit="step")
        
        try:
            # Generate transcript based on the provider
            if self.provider == "ollama":
                transcript = self._generate_ollama(prompt)
            elif self.provider == "openrouter":
                transcript = self._generate_openrouter(prompt)
            elif self.provider == "deepseek":
                transcript = self._generate_deepseek(prompt)
            else:
                raise ValueError(f"Unsupported provider: {self.provider}")
            
            progress.update(1, "Transcript generation completed")
            
            # Validate transcript format
            transcript = self._validate_transcript(transcript)
            
            return transcript
            
        except Exception as e:
            logger.error(f"Error generating transcript: {str(e)}")
            raise
        finally:
            progress.close()
    
    def _generate_ollama(self, prompt):
        """Generate transcript using Ollama"""
        logger.debug("Generating transcript with Ollama")
        
        url = self.config.get("api_urls", {}).get("ollama", "http://localhost:11434/api/generate")
        
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": self.config["transcript"].get("temperature", 0.7),
                "max_tokens": self.config["transcript"].get("max_tokens", 8000)
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
            # Get timeout from config or use default 10 minutes (600 seconds)
            timeout = self.config.get("api_timeouts", {}).get("ollama_transcript", 600)
            logger.debug(f"Using timeout of {timeout} seconds for Ollama transcript request")
            
            response = requests.post(url, json=payload, headers=headers, timeout=timeout)
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
            error_message, error_type = handle_api_error(response, "Ollama", "transcript generation")
            logger.error(error_message)
            raise Exception(error_message) from e
            
        except KeyError as e:
            error_type = "invalid_response"
            logger.error(f"Invalid response from Ollama API: {str(e)}")
            raise ValueError(f"Invalid response from Ollama API: {str(e)}")
            
        except Exception as e:
            error_type = "unknown"
            logger.error(f"Error generating transcript with Ollama: {str(e)}")
            raise
            
        finally:
            latency = time.time() - start_time
            self.api_stats.record_request(
                provider="ollama",
                model=self.model,
                request_type="transcript",
                success=success,
                error_type=error_type,
                tokens_in=tokens_in,
                tokens_out=tokens_out,
                latency=latency
            )
    
    def _generate_openrouter(self, prompt):
        """Generate transcript using OpenRouter"""
        logger.debug("Generating transcript with OpenRouter")
        
        url = self.config.get("api_urls", {}).get("openrouter", "https://openrouter.ai/api/v1/chat/completions")
        
        payload = {
            "model": self.model,
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "temperature": self.config["transcript"].get("temperature", 0.7),
            "max_tokens": self.config["transcript"].get("max_tokens", 8000)
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
            # Get timeout from config or use default 3 minutes (180 seconds)
            timeout = self.config.get("api_timeouts", {}).get("openrouter", 180) 
            logger.debug(f"Using timeout of {timeout} seconds for OpenRouter transcript request")
            
            response = requests.post(url, json=payload, headers=headers, timeout=timeout)
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
            error_message, error_type = handle_api_error(response, "OpenRouter", "transcript generation")
            logger.error(error_message)
            raise Exception(error_message) from e
            
        except (KeyError, ValueError) as e:
            error_type = "invalid_response"
            logger.error(f"Invalid response from OpenRouter API: {str(e)}")
            raise ValueError(f"Invalid response from OpenRouter API: {str(e)}")
            
        except Exception as e:
            error_type = "unknown"
            logger.error(f"Error generating transcript with OpenRouter: {str(e)}")
            raise
            
        finally:
            latency = time.time() - start_time
            self.api_stats.record_request(
                provider="openrouter",
                model=self.model,
                request_type="transcript",
                success=success,
                error_type=error_type,
                tokens_in=tokens_in,
                tokens_out=tokens_out,
                latency=latency
            )
    
    def _generate_deepseek(self, prompt):
        """Generate transcript using DeepSeek"""
        logger.debug("Generating transcript with DeepSeek")
        
        url = self.config.get("api_urls", {}).get("deepseek", "https://api.deepseek.com/v1/chat/completions")
        
        payload = {
            "model": self.model,
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "temperature": self.config["transcript"].get("temperature", 0.7),
            "max_tokens": self.config["transcript"].get("max_tokens", 8000)
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
            # Get timeout from config or use default 3 minutes (180 seconds)
            timeout = self.config.get("api_timeouts", {}).get("deepseek", 180)
            logger.debug(f"Using timeout of {timeout} seconds for DeepSeek transcript request")
            
            response = requests.post(url, json=payload, headers=headers, timeout=timeout)
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
            error_message, error_type = handle_api_error(response, "DeepSeek", "transcript generation")
            logger.error(error_message)
            raise Exception(error_message) from e
            
        except (KeyError, ValueError) as e:
            error_type = "invalid_response"
            logger.error(f"Invalid response from DeepSeek API: {str(e)}")
            raise ValueError(f"Invalid response from DeepSeek API: {str(e)}")
            
        except Exception as e:
            error_type = "unknown"
            logger.error(f"Error generating transcript with DeepSeek: {str(e)}")
            raise
            
        finally:
            latency = time.time() - start_time
            self.api_stats.record_request(
                provider="deepseek",
                model=self.model,
                request_type="transcript",
                success=success,
                error_type=error_type,
                tokens_in=tokens_in,
                tokens_out=tokens_out,
                latency=latency
            )
    
    def _validate_transcript(self, transcript):
        """
        Validate and clean the transcript format
        
        Args:
            transcript (str): The generated transcript
            
        Returns:
            str: Validated and cleaned transcript
        """
        # Basic validation to ensure proper speaker format
        host_name = self.config["transcript"].get("host_name", "Host").upper()
        expert_name = self.config["transcript"].get("expert_name", "Expert").upper()
        beginner_name = self.config["transcript"].get("beginner_name", "Beginner").upper()
        
        # Check if transcript contains expected speaker names
        if not any(f"{name}:" in transcript for name in [host_name, expert_name, beginner_name]):
            logger.warning("Transcript format may not be correct. Missing expected speaker labels.")
        
        # Ensure consistent formatting of speaker labels
        for name in [host_name, expert_name, beginner_name]:
            transcript = transcript.replace(f"{name.title()}:", f"{name}:")
            transcript = transcript.replace(f"{name.lower()}:", f"{name}:")
        
        # Ensure transcript ends with a newline
        if not transcript.endswith('\n'):
            transcript += '\n'
        
        return transcript


def generate_transcript(research_file, output_file, config):
    """
    Generate podcast transcript from research file and save to file
    
    Args:
        research_file (str or Path): Path to the research file
        output_file (str or Path): Path to save the transcript
        config (dict): Configuration dictionary
    
    Returns:
        str: The generated transcript
    """
    # Read the research content
    research_content = read_text_file(research_file)
    
    # Generate the transcript
    generator = TranscriptGenerator(config)
    transcript = generator.generate(research_content)
    
    # Save the transcript to a file
    save_text_file(transcript, output_file)
    
    logger.info(f"Transcript saved to {output_file}")
    return transcript
