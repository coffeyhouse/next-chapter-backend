# core/cli/main.py
import click
from .commands.scraper import scraper

@click.group()
def cli():
    """Goodreads Companion CLI"""
    pass

cli.add_command(scraper)

if __name__ == '__main__':
    cli()