import click
from core.database import GoodreadsDB
from core.database.queries import BookQueries

@click.group()
def genre():
    """Genre management commands"""
    pass

@genre.command(name="list")
@click.option('--db-path', '--db', default="books.db", help="Path to the books database")
@click.argument('genre_name')
def list_books(db_path: str, genre_name: str):
    """
    List all books in a specific genre, including Goodreads votes,
    ordered by votes (highest first).

    GENRE_NAME is the name of the genre to filter books by.
    """
    db = GoodreadsDB(db_path)
    # Instantiate the BookQueries with our DB instance (which provides execute_query)
    queries = BookQueries(db)
    books = queries.get_books_by_genre(genre_name)
    
    if books:
        click.echo(f"\nBooks in genre '{genre_name}':")
        for book in books:
            votes = book.get('goodreads_votes')
            votes_str = f"{votes}" if votes is not None else "N/A"
            click.echo(f" - {book['title']} (Goodreads ID: {book['goodreads_id']}, Votes: {votes_str})")
    else:
        click.echo(f"\nNo books found in genre '{genre_name}'.")

if __name__ == '__main__':
    genre()
