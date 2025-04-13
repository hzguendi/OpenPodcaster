"""
API Statistics Tracker
-------------------
Utilities for tracking API usage statistics and managing error handling
"""

import os
import json
import time
import logging
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

class APIStatsTracker:
    """Track API usage and statistics"""
    
    def __init__(self, config):
        """
        Initialize the API statistics tracker
        
        Args:
            config (dict): Configuration dictionary
        """
        self.config = config
        self.stats_dir = Path(config.get("api_stats", {}).get("directory", "data/api_stats"))
        self.stats_dir.mkdir(parents=True, exist_ok=True)
        self.stats_file = self.stats_dir / "api_usage.json"
        self.current_stats = self._load_stats()
    
    def _load_stats(self):
        """Load existing stats or create empty stats"""
        if self.stats_file.exists():
            try:
                with open(self.stats_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Error loading API stats: {str(e)}")
                return self._create_empty_stats()
        else:
            return self._create_empty_stats()
    
    def _create_empty_stats(self):
        """Create an empty stats dictionary"""
        return {
            "total_requests": 0,
            "providers": {},
            "models": {},
            "request_types": {},
            "errors": {
                "total": 0,
                "by_provider": {},
                "by_error": {}
            },
            "last_updated": datetime.now().isoformat()
        }
    
    def _save_stats(self):
        """Save the current stats to file"""
        try:
            self.current_stats["last_updated"] = datetime.now().isoformat()
            with open(self.stats_file, 'w') as f:
                json.dump(self.current_stats, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving API stats: {str(e)}")
    
    def record_request(self, provider, model, request_type, success=True, error_type=None, tokens_in=0, tokens_out=0, latency=0):
        """
        Record API request statistics
        
        Args:
            provider (str): Provider name (e.g., "openai", "elevenlabs")
            model (str): Model name
            request_type (str): Type of request (e.g., "research", "transcript", "tts")
            success (bool): Whether the request was successful
            error_type (str, optional): Type of error if request failed
            tokens_in (int): Input tokens used (for LLM requests)
            tokens_out (int): Output tokens generated (for LLM requests)
            latency (float): Request latency in seconds
        """
        # Update total requests
        self.current_stats["total_requests"] += 1
        
        # Update provider stats
        if provider not in self.current_stats["providers"]:
            self.current_stats["providers"][provider] = {
                "requests": 0,
                "successful": 0,
                "failed": 0,
                "tokens_in": 0,
                "tokens_out": 0,
                "total_latency": 0
            }
        
        self.current_stats["providers"][provider]["requests"] += 1
        if success:
            self.current_stats["providers"][provider]["successful"] += 1
        else:
            self.current_stats["providers"][provider]["failed"] += 1
        
        self.current_stats["providers"][provider]["tokens_in"] += tokens_in
        self.current_stats["providers"][provider]["tokens_out"] += tokens_out
        self.current_stats["providers"][provider]["total_latency"] += latency
        
        # Update model stats
        model_key = f"{provider}/{model}"
        if model_key not in self.current_stats["models"]:
            self.current_stats["models"][model_key] = {
                "requests": 0,
                "successful": 0,
                "failed": 0,
                "tokens_in": 0,
                "tokens_out": 0,
                "total_latency": 0
            }
        
        self.current_stats["models"][model_key]["requests"] += 1
        if success:
            self.current_stats["models"][model_key]["successful"] += 1
        else:
            self.current_stats["models"][model_key]["failed"] += 1
        
        self.current_stats["models"][model_key]["tokens_in"] += tokens_in
        self.current_stats["models"][model_key]["tokens_out"] += tokens_out
        self.current_stats["models"][model_key]["total_latency"] += latency
        
        # Update request type stats
        if request_type not in self.current_stats["request_types"]:
            self.current_stats["request_types"][request_type] = {
                "requests": 0,
                "successful": 0,
                "failed": 0
            }
        
        self.current_stats["request_types"][request_type]["requests"] += 1
        if success:
            self.current_stats["request_types"][request_type]["successful"] += 1
        else:
            self.current_stats["request_types"][request_type]["failed"] += 1
        
        # Update error stats if applicable
        if not success:
            self.current_stats["errors"]["total"] += 1
            
            # By provider
            if provider not in self.current_stats["errors"]["by_provider"]:
                self.current_stats["errors"]["by_provider"][provider] = 0
            self.current_stats["errors"]["by_provider"][provider] += 1
            
            # By error type
            error_type = error_type or "unknown"
            if error_type not in self.current_stats["errors"]["by_error"]:
                self.current_stats["errors"]["by_error"][error_type] = 0
            self.current_stats["errors"]["by_error"][error_type] += 1
        
        # Save stats to file
        self._save_stats()
    
    def get_summary(self):
        """
        Get a summary of API usage statistics
        
        Returns:
            dict: Summary statistics
        """
        return {
            "total_requests": self.current_stats["total_requests"],
            "successful_requests": self.current_stats["total_requests"] - self.current_stats["errors"]["total"],
            "failed_requests": self.current_stats["errors"]["total"],
            "providers": {
                provider: stats["requests"] 
                for provider, stats in self.current_stats["providers"].items()
            },
            "most_used_models": sorted(
                [(model, stats["requests"]) for model, stats in self.current_stats["models"].items()],
                key=lambda x: x[1],
                reverse=True
            )[:5],
            "last_updated": self.current_stats["last_updated"]
        }


def validate_api_key(api_key, provider):
    """
    Validate that an API key is provided and properly formatted
    
    Args:
        api_key (str): The API key to validate
        provider (str): Provider name for error messages
        
    Returns:
        bool: True if API key seems valid, False otherwise
        
    Raises:
        ValueError: If API key is missing
    """
    if provider =="ollama":
        logger.info(f"{provider} API key is not required")
        return True
    
    if not api_key:
        raise ValueError(f"API key for {provider} is missing. Please add it to your .env file.")
    
    # Basic validation based on provider-specific patterns
    if provider == "openrouter" and not api_key.startswith(("sk-", "or-")):
        logger.warning(f"{provider} API key format seems incorrect (should start with 'sk-' or 'or-')")
        return False
    elif provider == "elevenlabs" and len(api_key) < 32:
        logger.warning(f"{provider} API key seems too short")
        return False
    elif provider == "gemini" and len(api_key) < 10:
        logger.warning(f"{provider} API key seems too short")
        return False
    
    return True


def handle_api_error(response, provider, operation):
    """
    Handle API error responses
    
    Args:
        response: The response object from the API
        provider (str): Provider name
        operation (str): Description of operation
        
    Returns:
        tuple: (error_message, error_type)
    """
    error_message = f"Error during {operation} with {provider}"
    error_type = "unknown"
    
    try:
        # Try to extract error details from response
        if hasattr(response, 'json') and callable(response.json):
            try:
                error_data = response.json()
                if isinstance(error_data, dict):
                    if 'error' in error_data:
                        if isinstance(error_data['error'], dict):
                            if 'message' in error_data['error']:
                                error_message = f"{error_message}: {error_data['error']['message']}"
                            if 'type' in error_data['error']:
                                error_type = error_data['error']['type']
                        else:
                            error_message = f"{error_message}: {error_data['error']}"
                    elif 'message' in error_data:
                        error_message = f"{error_message}: {error_data['message']}"
            except:
                pass
        
        # Extract HTTP status code if available
        if hasattr(response, 'status_code'):
            error_type = f"http_{response.status_code}"
            error_message = f"{error_message} (Status: {response.status_code})"
    except:
        # If all else fails, use the string representation
        error_message = f"{error_message}: {str(response)}"
    
    return error_message, error_type
