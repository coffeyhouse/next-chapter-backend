# core/cli/main.py
import click
from .commands.scraper import scraper
from .commands.library import library
from .commands.dev import dev
from .commands.series import series
from .commands.author import author
from .commands.similar import similar
from .commands.book import book
from .commands.list import list
from .commands.monitor import monitor
from .commands.read import read

@click.group()
def cli():
    """Goodreads Companion CLI"""
    pass

cli.add_command(scraper)
cli.add_command(library)
cli.add_command(dev)
cli.add_command(series)
cli.add_command(author)
cli.add_command(similar)
cli.add_command(book)
cli.add_command(list)
cli.add_command(monitor)
cli.add_command(read)

def main():
    """Entry point for the CLI"""
    cli()

if __name__ == '__main__':
    main()