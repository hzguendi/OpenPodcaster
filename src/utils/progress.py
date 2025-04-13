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
    
    def __init__(self, total, desc="Processing", unit="steps", color="green"):
        """
        Initialize a new progress bar
        
        Args:
            total (int): Total number of steps
            desc (str): Description for the progress bar
            unit (str): Unit name for the progress counter
            color (str): Color for the progress bar
        """
        self.pbar = tqdm(
            total=total,
            desc=desc,
            unit=unit,
            colour=color,
            bar_format="{l_bar}{bar:30}{r_bar}",
            file=sys.stdout
        )
    
    def update(self, n=1, desc=None):
        """
        Update the progress bar
        
        Args:
            n (int): Number of steps to increment
            desc (str, optional): New description for the progress bar
        """
        if desc:
            self.pbar.set_description(desc)
        self.pbar.update(n)
    
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
