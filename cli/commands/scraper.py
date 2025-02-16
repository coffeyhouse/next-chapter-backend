# core/cli/commands/scraper.py
import click
import json
from pathlib import Path
from core.scrapers.book_scraper import BookScraper
from core.scrapers.author_scraper import AuthorScraper
from core.scrapers.author_books_scraper import AuthorBooksScraper
from core.scrapers.series_scraper import SeriesScraper
from core.scrapers.editions_scraper import EditionsScraper
from core.scrapers.similar_scraper import SimilarScraper

@click.group()
def scraper():
    """Commands for testing scrapers"""
    # Ensure data directories exist
    Path('data/cache/book/show').mkdir(parents=True, exist_ok=True)
    Path('data/cache/author/show').mkdir(parents=True, exist_ok=True)
    Path('data/cache/author/list').mkdir(parents=True, exist_ok=True)
    Path('data/cache/series/show').mkdir(parents=True, exist_ok=True)
    Path('data/cache/work/editions').mkdir(parents=True, exist_ok=True)
    Path('data/cache/book/similar').mkdir(parents=True, exist_ok=True)

@scraper.command()
@click.argument('book_id')
@click.option('--scrape/--no-scrape', default=False)
def book(book_id: str, scrape: bool):
    """Test book scraper output"""
    click.echo(f"\nTesting book scraper with ID: {book_id} (scrape={scrape})")
    
    scraper = BookScraper(scrape=scrape)  # Pass the scrape flag
    result = scraper.scrape(book_id)
    
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
    click.echo(f"\nTesting author scraper with ID: {author_id} (scrape={scrape})")
    
    scraper = AuthorScraper(scrape=scrape)  # Pass the scrape flag
    result = scraper.scrape_author(author_id)
    
    if result:
        click.echo(click.style("\nAuthor Data:", fg='green'))
        # Pretty print the result
        click.echo(json.dumps(result, indent=2))
    else:
        click.echo(click.style("\nFailed to get author data", fg='red'))

@scraper.command()
@click.argument('author_id')
@click.option('--scrape/--no-scrape', default=False)
def author_books(author_id: str, scrape: bool):
    """Test author books scraper output"""
    click.echo(f"\nTesting author books scraper with ID: {author_id} (scrape={scrape})")
    
    scraper = AuthorBooksScraper(scrape=scrape)  # Pass the scrape flag
    result = scraper.scrape_author_books(author_id)
    
    if result:
        click.echo(click.style("\nAuthor Books Data:", fg='green'))
        # Pretty print the result
        click.echo(json.dumps(result, indent=2))
    else:
        click.echo(click.style("\nFailed to get author books data", fg='red'))

@scraper.command()
@click.argument('series_id')
@click.option('--scrape/--no-scrape', default=False)
def series(series_id: str, scrape: bool):
    """Test series scraper output"""
    click.echo(f"\nTesting series scraper with ID: {series_id} (scrape={scrape})")
    
    scraper = SeriesScraper(scrape=scrape)  # Pass the scrape flag
    result = scraper.scrape_series(series_id)
    
    if result:
        click.echo(click.style("\nSeries Data:", fg='green'))
        # Pretty print the result
        click.echo(json.dumps(result, indent=2))
    else:
        click.echo(click.style("\nFailed to get series data", fg='red'))

@scraper.command()
@click.argument('work_id')
@click.option('--scrape/--no-scrape', default=False)
def editions(work_id: str, scrape: bool):
    """Test editions scraper output"""
    click.echo(f"\nTesting editions scraper with ID: {work_id} (scrape={scrape})")
    
    scraper = EditionsScraper(scrape=scrape)  # Pass the scrape flag
    result = scraper.scrape_editions(work_id)
    
    if result:
        click.echo(click.style("\nEditions Data:", fg='green'))
        # Pretty print the result
        click.echo(json.dumps(result, indent=2))
    else:
        click.echo(click.style("\nFailed to get editions data", fg='red'))
        
@scraper.command()
@click.argument('book_id')
@click.option('--scrape/--no-scrape', default=False)
def similar(book_id: str, scrape: bool):
    """Test similar books scraper output"""
    click.echo(f"\nTesting similar books scraper with ID: {book_id} (scrape={scrape})")
    
    scraper = SimilarScraper(scrape=scrape)  # Pass the scrape flag
    result = scraper.scrape_similar_books(book_id)
    
    if result:
        click.echo(click.style("\nSimilar Books Data:", fg='green'))
        # Pretty print the result
        click.echo(json.dumps(result, indent=2))
    else:
        click.echo(click.style("\nFailed to get similar books data", fg='red'))