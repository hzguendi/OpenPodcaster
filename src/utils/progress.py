"""
Progress Bar Utilities
-------------------
Provides colorful progress bars for tracking operations
"""

import sys
import time
from tqdm import tqdm


class ProgressBar:
    """
    A wrapper around tqdm to provide consistent progress bars
    with optional logging.
    """
    
    def __init__(self, total, desc="Processing", unit="steps", color="green", stream_tokens=False, max_tokens=None):
        """
        Initialize a new progress bar
        
        Args:
            total (int): Total number of steps
            desc (str): Description for the progress bar
            unit (str): Unit name for the progress counter
            color (str): Color for the progress bar
            stream_tokens (bool): Whether to stream tokens in the progress bar
            max_tokens (int, optional): Maximum expected tokens for streaming mode
        """
        self.stream_tokens = stream_tokens
        self.max_tokens = max_tokens
        self.last_token = ""
        
        # Bar format differs based on streaming mode
        if stream_tokens:
            unit = "tokens"
            bar_format = "{l_bar}{bar:30}{r_bar} {postfix}"  # Remove newline character
            total = max_tokens  # Use max_tokens as the total in streaming mode
        else:
            bar_format = "{l_bar}{bar:30}{r_bar}"
        
        self.pbar = tqdm(
            total=total,
            desc=desc,
            unit=unit,
            colour=color,
            bar_format=bar_format,
            file=sys.stdout,
            postfix={"token": ""} if stream_tokens else None
        )
    
    def update(self, n=1, desc=None, token=None):
        """
        Update the progress bar
        
        Args:
            n (int): Number of steps to increment
            desc (str, optional): New description for the progress bar
            token (str, optional): Latest token received in streaming mode
        """
        if desc:
            self.pbar.set_description(desc)
        
        if self.stream_tokens and token is not None:
            # Update the latest token display
            self.last_token = token
            # Only show the last few characters in the display to avoid cluttering
            # Trim and clean up the token for display
            display_token = token.strip()[-10:] if len(token.strip()) > 10 else token.strip()
            self.pbar.set_postfix({"token": display_token})
        
        self.pbar.update(n)
    
    def update_token(self, token):
        """
        Update just the token display without incrementing the progress bar
        
        Args:
            token (str): Latest token received in streaming mode
        """
        if self.stream_tokens and token:
            self.last_token = token
            # Only show the last few characters in the display to avoid cluttering
            # Trim and clean up the token for display
            display_token = token.strip()[-10:] if len(token.strip()) > 10 else token.strip()
            self.pbar.set_postfix({"token": display_token})
    
    def close(self):
        """Close the progress bar"""
        self.pbar.close()


def with_progress(iterable, desc="Processing", unit="items", color="green"):
    """
    Wrap an iterable with a progress bar
    
    Args:
        iterable: The iterable to wrap
        desc (str): Description for the progress bar
        unit (str): Unit name for the progress counter
        color (str): Color for the progress bar
        
    Returns:
        A wrapped iterable with progress tracking
    """
    return tqdm(
        iterable,
        desc=desc,
        unit=unit,
        colour=color,
        bar_format="{l_bar}{bar:30}{r_bar}",
        file=sys.stdout
    )
