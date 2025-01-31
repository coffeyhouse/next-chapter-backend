# backend/cli/base.py
import click
from typing import Callable, Any, Optional, List
import logging
from backend.db.operations import GoodreadsDB

logger = logging.getLogger(__name__)

class BaseCommand:
    """Base class for CLI commands"""
    
    def __init__(self, db_path: str, scrape: bool = False):
        self.db = GoodreadsDB(db_path)
        self.scrape = scrape
        
    def process_items(
        self,
        items: List[dict],
        processor: Callable[[dict], bool],
        description: str = "items"
    ) -> int:
        """Process a list of items with progress tracking
        
        Args:
            items: List of items to process
            processor: Function that processes each item
            description: Description of what's being processed
            
        Returns:
            Number of successfully processed items
        """
        total = len(items)
        success_count = 0
        
        click.echo(f"\nFound {total} {description}")
        
        for i, item in enumerate(items, 1):
            name = item.get('name', item.get('title', str(item)))
            click.echo(f"\nProcessing {i}/{total}: {name}")
            
            try:
                if processor(item):
                    success_count += 1
                    click.echo(f"Successfully processed: {name}")
            except Exception as e:
                click.echo(f"Error processing {name}: {str(e)}")
                logger.exception(f"Error processing {name}")
                continue
                
        click.echo(f"\nCompleted processing {total} {description}")
        click.echo(f"Successfully processed {success_count} {description}")
        
        return success_count