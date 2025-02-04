# core/cli/main.py
import click
from .commands.scraper import scraper
from .commands.library import library
from .commands.dev import dev
from .commands.series import series
from .commands.author import author
from .commands.similar import similar

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

if __name__ == '__main__':
    cli()