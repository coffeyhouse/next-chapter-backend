# core/utils/rate_limit.py

import time
import random
from datetime import datetime, timedelta
from typing import Optional
import click

class RateLimiter:
    def __init__(self, 
                 min_delay: float = 1.0,
                 max_delay: float = 1.5,
                 burst_size: int = 50,
                 min_burst_delay: float = 5.0,
                 max_burst_delay: float = 10.0):
        """
        Initialize rate limiter with configurable delays.
        
        Args:
            min_delay: Minimum delay between requests in seconds
            max_delay: Maximum delay between requests in seconds
            burst_size: Number of requests before triggering burst delay
            burst_delay: Delay after burst_size requests in seconds
        """
        self.min_delay = min_delay
        self.max_delay = max_delay
        self.burst_size = burst_size
        self.min_burst_delay = min_burst_delay
        self.max_burst_delay = max_burst_delay
        self.request_count = 0
        self.last_request_time: Optional[datetime] = None

    def delay(self) -> None:
        """Apply appropriate delay before next request"""
        current_time = datetime.now()
        
        # If this is not the first request
        if self.last_request_time:
            # Calculate time since last request
            time_since_last = (current_time - self.last_request_time).total_seconds()
            
            # Determine delay
            if self.request_count >= self.burst_size:
                # Reset counter and apply burst delay
                burst_delay = random.uniform(self.min_burst_delay, self.max_burst_delay)
                click.echo(f"\nTaking a longer break for {burst_delay:.1f} seconds...")
                time.sleep(burst_delay)
                self.request_count = 0
            else:
                # Calculate random delay
                delay = random.uniform(self.min_delay, self.max_delay)
                
                # If we need to wait more
                if time_since_last < delay:
                    wait_time = delay - time_since_last
                    # click.echo(f"\nWaiting {wait_time:.1f} seconds...")
                    time.sleep(wait_time)
        
        self.request_count += 1
        self.last_request_time = datetime.now()