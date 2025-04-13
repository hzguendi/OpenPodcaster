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
import inspect
import re
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
        stream_tokens = self.config["transcript"].get("stream_tokens", False)
        max_tokens = self.config["transcript"].get("max_tokens", 8000)
        
        progress = ProgressBar(
            total=1 if not stream_tokens else max_tokens, 
            desc="Generating transcript", 
            unit="step" if not stream_tokens else "tokens",
            stream_tokens=stream_tokens, 
            max_tokens=max_tokens
        )
        
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
            
            # Only update if not in streaming mode (streaming updates during processing)
            if not self.config["transcript"].get("stream_tokens", False):
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
        stream_tokens = self.config["transcript"].get("stream_tokens", False)
        max_tokens = self.config["transcript"].get("max_tokens", 8000)
        
        # Configure streaming based on config setting
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": stream_tokens,  # Enable streaming if configured
            "options": {
                "temperature": self.config["transcript"].get("temperature", 0.7),
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
            # Get timeout from config or use default 10 minutes (600 seconds)
            timeout = self.config.get("api_timeouts", {}).get("ollama_transcript", 600)
            logger.debug(f"Using timeout of {timeout} seconds for Ollama transcript request")
            
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
        total_progress = 0  # Track total progress updates
        max_tokens = self.config["transcript"].get("max_tokens", 8000)
        update_interval = 0.1  # seconds
        last_update_time = time.time()
        
        # Track batches of tokens for smoother progress updates
        token_batch = []
        
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
                                token_batch.append(token)
                                
                                # Always update the token display with latest token
                                # But only show display without updating progress counter
                                progress.update_token(token)
                                
                                # Update progress in batches for smoother display
                                current_time = time.time()
                                if current_time - last_update_time >= update_interval:
                                    # Update progress with batch size
                                    batch_size = len(token_batch)
                                    if batch_size > 0:
                                        # Calculate percentage of max_tokens
                                        progress_step = min(batch_size, max_tokens - total_progress)
                                        if progress_step > 0:
                                            progress.update(progress_step)
                                            total_progress += progress_step
                                            token_batch = []
                                            last_update_time = current_time
                            
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
                                        token_batch.append(token)
                                        
                                        # Always update the token display with latest token
                                        progress.update_token(token)
                                        
                                        # Update progress in batches for smoother display
                                        current_time = time.time()
                                        if current_time - last_update_time >= update_interval:
                                            # Update progress with batch size
                                            batch_size = len(token_batch)
                                            if batch_size > 0:
                                                # Calculate percentage of max_tokens
                                                progress_step = min(batch_size, max_tokens - total_progress)
                                                if progress_step > 0:
                                                    progress.update(progress_step)
                                                    total_progress += progress_step
                                                    token_batch = []
                                                    last_update_time = current_time
                    except json.JSONDecodeError as e:
                        logger.warning(f"Failed to decode JSON from {provider} stream: {e}")
                        continue
                    except Exception as e:
                        logger.warning(f"Error processing {provider} stream line: {e}")
                        continue
            
            # Process any remaining tokens in the batch
            if token_batch:
                batch_size = len(token_batch)
                progress_step = min(batch_size, max_tokens - total_progress)
                if progress_step > 0:
                    progress.update(progress_step)
                    total_progress += progress_step
            
            # Set progress to 100% when complete
            remaining_progress = max_tokens - total_progress
            if remaining_progress > 0:
                progress.update(remaining_progress)
            
            progress.pbar.set_description("Transcript generation completed")
            return response_text
                
        except Exception as e:
            logger.error(f"Error processing streaming response from {provider}: {str(e)}")
            raise
    

    
    def _generate_openrouter(self, prompt):
        """Generate transcript using OpenRouter"""
        logger.debug("Generating transcript with OpenRouter")
        
        url = self.config.get("api_urls", {}).get("openrouter", "https://openrouter.ai/api/v1/chat/completions")
        stream_tokens = self.config["transcript"].get("stream_tokens", False)
        max_tokens = self.config["transcript"].get("max_tokens", 8000)
        
        # Configure streaming based on config setting
        payload = {
            "model": self.model,
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "temperature": self.config["transcript"].get("temperature", 0.7),
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
            logger.debug(f"Using timeout of {timeout} seconds for OpenRouter transcript request")
            
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
        stream_tokens = self.config["transcript"].get("stream_tokens", False)
        max_tokens = self.config["transcript"].get("max_tokens", 8000)
        
        # Configure streaming based on config setting
        payload = {
            "model": self.model,
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "temperature": self.config["transcript"].get("temperature", 0.7),
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
            logger.debug(f"Using timeout of {timeout} seconds for DeepSeek transcript request")
            
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
        Validate and clean the transcript format according to new requirements:
        - Remove any markdown formatting
        - Validate section dividers and timestamps
        - Ensure proper speaker label formatting
        - Handle structured notes section
        
        Args:
            transcript (str): The generated transcript
            
        Returns:
            str: Validated and cleaned transcript
        """
        # Get speaker names from config
        host_name = self.config["transcript"].get("host_name", "Host")
        expert_name = self.config["transcript"].get("expert_name", "Expert") 
        beginner_name = self.config["transcript"].get("beginner_name", "Beginner")

        # 1. Remove any markdown formatting
        transcript = re.sub(r'\*\*', '', transcript)  # Remove bold
        transcript = re.sub(r'#+\s*', '', transcript)  # Remove headers

        # 2. Validate and format speaker labels
        expected_speakers = [host_name, expert_name, beginner_name]
        for speaker in expected_speakers:
            # Ensure exact match of speaker labels with colon
            transcript = re.sub(
                rf'(?i)^{re.escape(speaker)}\s*:?',
                f'{speaker}:',
                transcript,
                flags=re.MULTILINE
            )

        # 3. Validate section dividers and timestamps
        lines = []
        in_notes = False
        for line in transcript.split('\n'):
            # Remove section dividers but keep timestamps
            if line.startswith('---'):
                continue
                
            # Handle structured notes section
            if line.strip().startswith('<notes>'):
                in_notes = True
                continue
            if line.strip().startswith('</notes>'):
                in_notes = False
                continue
            if in_notes:
                continue

            # Keep timestamp lines but validate format
            if re.match(r'^\[\d{2}:\d{2}:\d{2}\]', line):
                if not re.match(r'^\[\d{2}:\d{2}:\d{2}\] [A-Z]', line):
                    logger.warning(f"Invalid timestamp format: {line}")
                lines.append(line)
            else:
                lines.append(line)

        transcript = '\n'.join(lines)

        # 4. Final validation checks
        required_patterns = [
            rf'^{host_name}:',
            rf'^{expert_name}:',
            rf'^{beginner_name}:',
            r'\[\d{2}:\d{2}:\d{2}\]'
        ]
        
        if not any(re.search(pattern, transcript, re.MULTILINE) for pattern in required_patterns):
            logger.error("Transcript missing required elements (speaker labels/timestamps)")

        # 5. Ensure proper line spacing
        transcript = re.sub(r'\n{3,}', '\n\n', transcript)  # Max 2 newlines
        transcript = transcript.strip() + '\n'  # Ensure ending newline

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
