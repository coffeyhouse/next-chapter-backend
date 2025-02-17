import click
import json
from datetime import datetime
from sqlalchemy.orm import Session
from core.resolvers.book_resolver import BookResolver
from core.resolvers.book_creator import BookCreator
from core.sa.models import User, Book, BookUser
from core.sa.repositories.book import BookRepository
from core.sa.repositories.user import UserRepository
from core.sa.database import Database

@click.command()
@click.argument('json_file', type=click.Path(exists=True))
@click.option('--user-id', type=int, required=True, help='User ID to associate the read books with')
@click.option('--dry-run', is_flag=True, help='Show what would be imported without making changes')
def read(json_file, user_id, dry_run):
    """Import read books from a JSON file containing Goodreads IDs and read dates."""
    try:
        # Initialize database and session
        db = Database()
        session = Session(db.engine)
        
        user_repo = UserRepository(session)
        book_repo = BookRepository(session)
        book_creator = BookCreator(session, scrape=True)
        
        # Check if user exists
        user = user_repo.get_by_id(user_id)
        if not user:
            if dry_run:
                click.echo(f"Would create new user with ID: {user_id}")
            else:
                # Prompt for user name
                name = click.prompt("User not found. Please enter a name for the new user")
                user = User(id=user_id, name=name)
                session.add(user)
                session.commit()
                click.echo(f"Created new user: {name} (ID: {user_id})")
        else:
            click.echo(f"Using existing user: {user.name} (ID: {user_id})")
        
        # Load the JSON file
        with open(json_file, 'r') as f:
            books = json.load(f)
        
        click.echo(f"Found {len(books)} books to process")
        
        processed = 0
        imported = 0
        
        for book_data in books:
            goodreads_id = book_data.get('goodreads_id')
            title = book_data.get('title', 'Unknown Title')
            date_read = book_data.get('date_read')
            
            if not goodreads_id:
                click.echo(f"Skipping book '{title}' - no Goodreads ID")
                continue
                
            click.echo(f"\nProcessing: {title} (ID: {goodreads_id})")
            
            # Convert date_read to proper format or None
            parsed_date = None
            if date_read:
                try:
                    parsed_date = datetime.strptime(date_read, '%Y-%m-%d')
                except ValueError:
                    click.echo(f"Warning: Invalid date format for '{title}': {date_read}")
            
            if dry_run:
                click.echo(f"Would import: {title} (Read on: {parsed_date or 'Unknown'})")
                processed += 1
                continue
            
            # Get or create the book
            book = book_repo.get_by_goodreads_id(goodreads_id)
            if not book:
                book = book_creator.create_book_from_goodreads(goodreads_id)
            
            if book:
                # Update reading status
                book_user = session.query(BookUser).filter_by(
                    work_id=book.work_id,
                    user_id=user_id
                ).first()
                
                if not book_user:
                    book_user = BookUser(
                        work_id=book.work_id,
                        user_id=user_id,
                        status='completed',
                        finished_at=parsed_date
                    )
                    session.add(book_user)
                else:
                    book_user.status = 'completed'
                    book_user.finished_at = parsed_date
                    book_user.updated_at = datetime.now()
                
                session.commit()
                imported += 1
                click.echo(f"Successfully imported and marked as read: {title}")
            else:
                click.echo(f"Failed to import book: {title}")
            
            processed += 1
            
        click.echo(f"\nProcessed {processed} books, imported {imported}")
        
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        raise click.Abort()
    finally:
        session.close() 
        
#         Code for the console:
#             // Select all book rows in the table
# const rows = document.querySelectorAll('#books tr.bookalike');

# const books = Array.from(rows).map(row => {
#   // Get the title anchor from the title field
#   const titleAnchor = row.querySelector('td.field.title a');
#   let title = titleAnchor ? titleAnchor.textContent.trim() : '';
#   // Remove any text after a newline
#   if (title.includes('\n')) {
#     title = title.split('\n')[0].trim();
#   }

#   // Attempt to extract goodreads_id from the cover cell's data attribute
#   let goodreads_id = '';
#   const coverDiv = row.querySelector('td.field.cover .js-tooltipTrigger');
#   if (coverDiv && coverDiv.getAttribute('data-resource-id')) {
#     goodreads_id = coverDiv.getAttribute('data-resource-id').trim();
#   } else {
#     // Fallback: parse it from the title link href, e.g. "/book/show/11125.Digital_Fortress"
#     const href = titleAnchor ? titleAnchor.getAttribute('href') : '';
#     const match = href.match(/\/book\/show\/(\d+)/);
#     if (match) {
#       goodreads_id = match[1];
#     }
#   }

#   // Extract and reformat the date read from the date_read cell
#   const dateReadEl = row.querySelector('td.field.date_read .date_read_value');
#   let date_read = dateReadEl ? dateReadEl.textContent.trim() : '';
#   if (date_read) {
#     const d = new Date(date_read);
#     if (!isNaN(d)) {
#       const year = d.getFullYear();
#       const month = (d.getMonth() + 1).toString().padStart(2, '0');
#       const day = d.getDate().toString().padStart(2, '0');
#       date_read = `${year}-${month}-${day}`;
#       // If date_read equals "2016-01-10", set it to empty string.
#       if (date_read === "2016-01-10") {
#         date_read = "";
#       }
#     }
#   }

#   return { title, goodreads_id, date_read };
# });

# console.log(books);