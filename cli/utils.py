import click
from typing import List, Any, Callable, Optional, Dict
from datetime import datetime, UTC
from sqlalchemy.orm import Session

class ProgressTracker:
    """Tracks progress and manages skipped items during sync operations"""
    
    def __init__(self, verbose: bool = False):
        self.processed = 0
        self.imported = 0
        self.skipped: List[Dict[str, str]] = []
        self.verbose = verbose
        
    def add_skipped(self, name: str, id: str, reason: str, color: str = 'yellow'):
        """Add a skipped item to the tracking"""
        if self.verbose or color == 'red':  # Always track errors
            self.skipped.append({
                'name': name,
                'id': id,
                'reason': reason,
                'color': color
            })
    
    def increment_processed(self):
        """Increment the processed counter"""
        self.processed += 1
    
    def increment_imported(self):
        """Increment the imported counter"""
        self.imported += 1
    
    def print_results(self, item_type: str = 'items'):
        """Print the results of the operation"""
        click.echo("\n" + click.style("Results:", fg='blue'))
        click.echo(click.style("Processed: ", fg='blue') + 
                  click.style(str(self.processed), fg='cyan') + 
                  click.style(f" {item_type}", fg='blue'))
        click.echo(click.style("Imported: ", fg='blue') + 
                  click.style(str(self.imported), fg='green') + 
                  click.style(" books", fg='blue'))
        
        if self.skipped and self.verbose:
            click.echo("\n" + click.style("Skipped items:", fg='yellow'))
            for skip_info in self.skipped:
                click.echo("\n" + click.style(f"Name: {skip_info['name']}", fg=skip_info['color']))
                click.echo(click.style(f"ID: {skip_info['id']}", fg=skip_info['color']))
                click.echo(click.style(f"Reason: {skip_info['reason']}", fg=skip_info['color']))
        elif self.skipped:
            click.echo(click.style(f"\nSkipped {len(self.skipped)} items. ", fg='yellow') + 
                      click.style("Use --verbose to see details.", fg='blue'))

def print_sync_start(days: Optional[int] = None, limit: Optional[int] = None, 
                    source: Optional[str] = None, specific_id: Optional[str] = None,
                    item_type: str = 'items', verbose: bool = False) -> None:
    """Print sync operation start information"""
    if not verbose:
        return
        
    if specific_id:
        click.echo(click.style(f"\nSyncing specific {item_type[:-1]} with ID: ", fg='blue') + 
                  click.style(specific_id, fg='cyan'))
    else:
        if days:
            click.echo(click.style(f"\nSyncing {item_type} not updated in ", fg='blue') + 
                      click.style(str(days), fg='cyan') + 
                      click.style(" days", fg='blue'))
        if limit:
            click.echo(click.style("Limited to ", fg='blue') + 
                      click.style(str(limit), fg='cyan') + 
                      click.style(f" {item_type}", fg='blue'))
        if source:
            click.echo(click.style("Only processing items with ", fg='blue') + 
                      click.style(source, fg='cyan') + 
                      click.style(" books", fg='blue'))

def create_progress_bar(items: List[Any], verbose: bool = False, 
                       label: str = 'Processing', 
                       item_name_func: Optional[Callable[[Any], str]] = None) -> click.progressbar:
    """Create a standardized progress bar for sync operations"""
    return click.progressbar(
        items,
        label=click.style(label, fg='blue'),
        item_show_func=lambda x: click.style(item_name_func(x), fg='cyan') if x and verbose and item_name_func else None,
        show_eta=True,
        show_percent=True,
        width=50
    )

def update_last_synced(item: Any, session: Session) -> None:
    """Update the last_synced_at timestamp for an item"""
    item.last_synced_at = datetime.now(UTC)
    session.commit() 