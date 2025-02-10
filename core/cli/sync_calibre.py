# core/cli/sync_calibre.py

import click
from datetime import datetime, UTC
from sqlalchemy.orm import Session
from typing import Dict, Any, List

from core.sa.database import Database
from core.sa.repositories.user import UserRepository
from core.database.queries import get_reading_progress

# Default Calibre database path
DEFAULT_CALIBRE_PATH = "C:/Users/warre/Calibre Library/metadata.db"

def print_reading_data(data: List[Dict[str, Any]]):
    """Print reading data in a readable format."""
    print("\nReading Progress Data:")
    print("-" * 80)
    for entry in data:
        print(f"\nBook: {entry['title']} (Calibre ID: {entry['calibre_id']}, Goodreads ID: {entry['goodreads_id']})")
        print("Warren:")
        print(f"  Last Read: {entry['warren_last_read'] or 'Never'}")
        print(f"  Progress: {entry['warren_read_percent']}%")
        print("Ruth:")
        print(f"  Last Read: {entry['ruth_last_read'] or 'Never'}")
        print(f"  Progress: {entry['ruth_read_percent']}%")
    print("-" * 80)

def determine_status(read_percent: float) -> str:
    """Determine reading status based on percentage."""
    if read_percent is None or read_percent == 0:
        return "want_to_read"
    elif read_percent == 100:
        return "completed"
    else:
        return "reading"

@click.command()
@click.option('--calibre-path', type=click.Path(exists=True), default=DEFAULT_CALIBRE_PATH, help="Path to Calibre metadata.db (optional)")
@click.option('--dry-run', is_flag=True, help="Print data without making changes")
def sync_calibre(calibre_path: str, dry_run: bool):
    """Sync reading progress from Calibre database."""
    # Get reading progress data
    data = get_reading_progress(calibre_path)
    
    # Print the data
    print_reading_data(data)
    
    if dry_run:
        print("\nDry run - no changes made")
        return
        
    # Initialize database
    db = Database()
    session: Session = db.get_session()
    user_repo = UserRepository(session)
    
    try:
        # Get or create users
        warren = user_repo.get_or_create_user("Warren")
        ruth = user_repo.get_or_create_user("Ruth")
        
        print(f"\nUsers:")
        print(f"Warren (ID: {warren.id})")
        print(f"Ruth (ID: {ruth.id})")
        
        # Process each book
        total_processed = 0
        warren_updates = 0
        ruth_updates = 0
        
        for entry in data:
            print(f"\nProcessing book: {entry['title']}")
            
            # Update Warren's status if there's progress
            if entry['warren_read_percent'] > 0:
                status = determine_status(entry['warren_read_percent'])
                print(f"Warren's status: {status} ({entry['warren_read_percent']}%)")
                result = user_repo.update_book_status(
                    user_id=warren.id,
                    goodreads_id=entry['goodreads_id'],
                    status=status,
                    source="calibre",
                    started_at=None,  # We don't have this information
                    finished_at=entry['warren_last_read'] if status == "completed" else None
                )
                if result:
                    warren_updates += 1
                    print("Warren's status updated")
                else:
                    print("Failed to update Warren's status")
            
            # Update Ruth's status if there's progress
            if entry['ruth_read_percent'] > 0:
                status = determine_status(entry['ruth_read_percent'])
                print(f"Ruth's status: {status} ({entry['ruth_read_percent']}%)")
                result = user_repo.update_book_status(
                    user_id=ruth.id,
                    goodreads_id=entry['goodreads_id'],
                    status=status,
                    source="calibre",
                    started_at=None,  # We don't have this information
                    finished_at=entry['ruth_last_read'] if status == "completed" else None
                )
                if result:
                    ruth_updates += 1
                    print("Ruth's status updated")
                else:
                    print("Failed to update Ruth's status")
                    
            total_processed += 1
        
        print(f"\nSync Results:")
        print(f"Total books processed: {total_processed}")
        print(f"Warren's updates: {warren_updates}")
        print(f"Ruth's updates: {ruth_updates}")
        
    finally:
        session.close()

if __name__ == '__main__':
    sync_calibre() 