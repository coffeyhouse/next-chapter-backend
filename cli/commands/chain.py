import click
from core.database import GoodreadsDB

@click.command()
@click.option('--db-path', '--db', default="books.db", help='Path to the books database')
@click.option('--calibre-path', default="C:/path/to/calibre/metadata.db", help='Path to Calibre metadata.db')
@click.option('--limit', default=None, type=int, help='Limit number of books for each operation')
def chain(db_path: str, calibre_path: str, limit: int):
    """
    Chain several CLI operations:
      1. Import books from the Calibre library.
      2. Sync similar books (for books with source "library").
      3. Sync series.

    This command will run the three tasks sequentially.
    """
    db = GoodreadsDB(db_path)

    click.echo("\n=== Starting Library Import ===")
    lib_processed, lib_imported = db.import_calibre_books(calibre_path, limit)
    click.echo(f"Library Import: Processed {lib_processed} books, Imported {lib_imported} books.\n")

    click.echo("=== Starting Similar Sync ===")
    sim_processed, sim_imported = db.sync_similar(source="library", limit=limit)
    click.echo(f"Similar Sync: Processed {sim_processed} books, Imported {sim_imported} similar relationships.\n")

    click.echo("=== Starting Series Sync ===")
    ser_processed, ser_imported = db.sync_series(limit=limit)
    click.echo(f"Series Sync: Processed {ser_processed} series, Imported {ser_imported} books from series.\n")

if __name__ == '__main__':
    chain()
