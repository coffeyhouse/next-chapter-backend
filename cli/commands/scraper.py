# core/cli/commands/scraper.py
import click
import json
from pathlib import Path
from core.scrapers.book_scraper import BookScraper
from core.scrapers.author_scraper import AuthorScraper
from core.scrapers.author_books_scraper import AuthorBooksScraper
from core.scrapers.series_scraper import SeriesScraper
from core.scrapers.editions_scraper import EditionsScraper

@click.group()
def scraper():
    """Commands for testing scrapers"""
    # Ensure data directories exist
    Path('data/cache/book/show').mkdir(parents=True, exist_ok=True)
    Path('data/cache/author/show').mkdir(parents=True, exist_ok=True)
    Path('data/cache/series/show').mkdir(parents=True, exist_ok=True)

@scraper.command()
@click.argument('book_id')
@click.option('--scrape/--no-scrape', default=False)
def book(book_id: str, scrape: bool):
    """Test book scraper output"""
    click.echo(f"\nTesting book scraper with ID: {book_id} (scrape={scrape})")
    
    scraper = BookScraper(scrape=scrape)  # Pass the scrape flag
    result = scraper.scrape_book(book_id)
    
    if result:
        click.echo(click.style("\nBook Data:", fg='green'))
        # Pretty print the result
        click.echo(json.dumps(result, indent=2))
    else:
        click.echo(click.style("\nFailed to get book data", fg='red'))

@scraper.command()
@click.argument('author_id')
@click.option('--scrape/--no-scrape', default=False)
def author(author_id: str, scrape: bool):
    """Test author scraper output"""
    scraper = AuthorScraper()
    result = scraper.scrape_author(author_id)
    click.echo(click.style("Author Data:", fg='green'))
    click.echo(result)

@scraper.command()
@click.argument('author_id')
@click.option('--scrape/--no-scrape', default=False)
def author_books(author_id: str, scrape: bool):
    """Test author books scraper output"""
    scraper = AuthorBooksScraper()
    result = scraper.scrape_author_books(author_id)
    click.echo(click.style("Author Books Data:", fg='green'))
    click.echo(result)

@scraper.command()
@click.argument('series_id')
@click.option('--scrape/--no-scrape', default=False)
def series(series_id: str, scrape: bool):
    """Test series scraper output"""
    scraper = SeriesScraper()
    result = scraper.scrape_series(series_id)
    click.echo(click.style("Series Data:", fg='green'))
    click.echo(result)

@scraper.command()
@click.argument('work_id')
@click.option('--scrape/--no-scrape', default=False)
def editions(work_id: str, scrape: bool):
    """Test editions scraper output"""
    scraper = EditionsScraper()
    result = scraper.scrape_editions(work_id)
    click.echo(click.style("Editions Data:", fg='green'))
    click.echo(result)