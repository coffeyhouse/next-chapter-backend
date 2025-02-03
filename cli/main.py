# core/cli/main.py
import click
from .commands.scraper import scraper
from .commands.library import library
from .commands.dev import dev
from .commands.series import series

@click.group()
def cli():
    """Goodreads Companion CLI"""
    pass

cli.add_command(scraper)
cli.add_command(library)
cli.add_command(dev)
cli.add_command(series)

if __name__ == '__main__':
    cli()