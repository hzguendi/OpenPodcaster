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
import inspect
from pathlib import Path


from src.utils.api_stats import handle_api_error, APIStatsTracker

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
        
        if not self.api_key and self.provider != "ollama":
            raise ValueError(f"API key for {self.provider} not found in configuration")
        
        # Get the prompt template
        self.prompt_template = get_prompt_content("research_prompt")
        
        # Initialize API stats tracker
        self.api_stats = APIStatsTracker(config)
        
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
        stream_tokens = self.config["research"].get("stream_tokens", False)
        max_tokens = self.config["research"].get("max_tokens", 4000)
        
        progress = ProgressBar(
            total=1 if not stream_tokens else max_tokens, 
            desc="Researching", 
            unit="step" if not stream_tokens else "tokens",
            stream_tokens=stream_tokens, 
            max_tokens=max_tokens
        )
        
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
            
            # Only update if not in streaming mode (streaming updates during processing)
            if not self.config["research"].get("stream_tokens", False):
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
        stream_tokens = self.config["research"].get("stream_tokens", False)
        max_tokens = self.config["research"].get("max_tokens", 4000)
        
        # Configure streaming based on config setting
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": stream_tokens,  # Enable streaming if configured
            "options": {
                "temperature": self.config["research"].get("temperature", 0.7),
                "max_tokens": max_tokens
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
            # Get timeout from config or use default 5 minutes (300 seconds)
            timeout = self.config.get("api_timeouts", {}).get("ollama_research", 300)
            logger.debug(f"Using timeout of {timeout} seconds for Ollama research request")
            
            if stream_tokens:
                # Handle streaming responses
                content = self._handle_streaming(url, payload, headers, timeout, provider="ollama")
                tokens_out = len(content.split())
                success = True
                return content
            else:
                # Handle non-streaming responses (original implementation)
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
    
    def _handle_streaming(self, url, payload, headers, timeout, provider="ollama"):
        """Handle streaming responses from any provider API
        
        Args:
            url (str): API endpoint URL
            payload (dict): Request payload
            headers (dict): Request headers
            timeout (int): Request timeout in seconds
            provider (str): Provider name (ollama, openrouter, deepseek)
            
        Returns:
            str: Accumulated response text from streaming
        """
        logger.debug(f"Handling streaming response from {provider.capitalize()}")
        
        # Get progress bar instance
        progress = None
        for frame_info in inspect.stack():
            frame = frame_info.frame
            if 'progress' in frame.f_locals and isinstance(frame.f_locals['progress'], ProgressBar):
                progress = frame.f_locals['progress']
                break
        
        if not progress:
            logger.warning("Could not find progress bar for streaming updates")
            # Create a dummy progress bar that does nothing
            progress = type('DummyProgress', (), {'update_token': lambda self, token: None, 'update': lambda self, n, desc=None, token=None: None})()
        
        # Initialize response
        response_text = ""
        token_count = 0
        max_tokens = self.config["research"].get("max_tokens", 4000)
        last_update_time = time.time()
        
        try:
            with requests.post(url, json=payload, headers=headers, timeout=timeout, stream=True) as response:
                response.raise_for_status()
                
                # Process the stream line by line
                for line in response.iter_lines():
                    if not line:
                        continue
                        
                    try:
                        # Process based on provider's format
                        if provider == "ollama":
                            # Ollama format: direct JSON objects
                            data = json.loads(line.decode('utf-8'))
                            
                            # Extract token
                            if 'response' in data:
                                token = data['response']
                                response_text += token
                                token_count += 1
                                
                                # Update progress bar
                                self._update_stream_progress(progress, token, token_count, last_update_time)
                                last_update_time = time.time()
                            
                            # Check for end of stream
                            if data.get('done', False):
                                break
                        else:
                            # OpenRouter/DeepSeek format (OpenAI SSE format)
                            line_str = line.decode('utf-8').strip()
                            
                            # SSE format: lines start with "data: "
                            if line_str.startswith('data: '):
                                # Remove "data: " prefix
                                json_str = line_str[6:]
                                
                                # Check for end marker
                                if json_str == "[DONE]":
                                    break
                                    
                                # Parse JSON payload    
                                data = json.loads(json_str)
                                
                                # Extract token from choices/delta structure
                                if 'choices' in data and data['choices'] and 'delta' in data['choices'][0]:
                                    delta = data['choices'][0]['delta']
                                    if 'content' in delta and delta['content']:
                                        token = delta['content']
                                        response_text += token
                                        token_count += 1
                                        
                                        # Update progress bar
                                        self._update_stream_progress(progress, token, token_count, last_update_time)
                                        last_update_time = time.time()
                    except json.JSONDecodeError as e:
                        logger.warning(f"Failed to decode JSON from {provider} stream: {e}")
                        continue
                    except Exception as e:
                        logger.warning(f"Error processing {provider} stream line: {e}")
                        continue
            
            # Final progress update
            progress.update(max_tokens - token_count, desc="Research completed")
            return response_text
                
        except Exception as e:
            logger.error(f"Error processing streaming response from {provider}: {str(e)}")
            raise
    
    def _update_stream_progress(self, progress, token, token_count, last_update_time):
        """Helper method to update the progress bar for streaming tokens
        
        Args:
            progress: Progress bar instance
            token: Current token
            token_count: Current token count
            last_update_time: Last time progress was updated
        """
        # Update progress bar at a reasonable interval
        current_time = time.time()
        if current_time - last_update_time >= 0.1:  # Update every 0.1 seconds
            progress.update(1, token=token)
        else:
            # Just update the token display without incrementing the counter
            progress.update_token(token)
    
    def _generate_openrouter(self, prompt):
        """Generate content using OpenRouter"""
        logger.debug("Generating content with OpenRouter")
        
        url = self.config.get("api_urls", {}).get("openrouter", "https://openrouter.ai/api/v1/chat/completions")
        stream_tokens = self.config["research"].get("stream_tokens", False)
        max_tokens = self.config["research"].get("max_tokens", 4000)
        
        # Configure streaming based on config setting
        payload = {
            "model": self.model,
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "temperature": self.config["research"].get("temperature", 0.7),
            "max_tokens": max_tokens,
            "stream": stream_tokens  # Enable streaming if configured
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
            logger.debug(f"Using timeout of {timeout} seconds for OpenRouter research request")
            
            if stream_tokens:
                # Handle streaming responses
                content = self._handle_streaming(url, payload, headers, timeout, provider="openrouter")
                tokens_out = len(content.split())
                success = True
                return content
            else:
                # Handle non-streaming responses (original implementation)
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
        stream_tokens = self.config["research"].get("stream_tokens", False)
        max_tokens = self.config["research"].get("max_tokens", 4000)
        
        # Configure streaming based on config setting
        payload = {
            "model": self.model,
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "temperature": self.config["research"].get("temperature", 0.7),
            "max_tokens": max_tokens,
            "stream": stream_tokens  # Enable streaming if configured
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
            logger.debug(f"Using timeout of {timeout} seconds for DeepSeek research request")
            
            if stream_tokens:
                # Handle streaming responses
                content = self._handle_streaming(url, payload, headers, timeout, provider="deepseek")
                tokens_out = len(content.split())
                success = True
                return content
            else:
                # Handle non-streaming responses (original implementation)
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