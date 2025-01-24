#!/usr/bin/env python
import click
from backend.scrapers.book import scrape_book
from backend.scrapers.author import scrape_author
from backend.scrapers.author_books import scrape_author_books
from backend.scrapers.series import scrape_series
from backend.scrapers.similar import scrape_similar
from backend.scrapers.editions import scrape_editions

# Ensure backend module can be imported
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent))

@click.group()
def cli():
    """Goodreads Scraper CLI"""
    pass

@cli.command()
@click.argument('book_id')
def book(book_id):
    """Scrape a book by its ID"""
    book_info = scrape_book(book_id)
    if book_info:
        # Print book information
        print("\n" + "=" * 80)
        print(f"{'Title:':<15} {book_info['title']['title']}")
        print(f"{'ID:':<15} {book_info['id'] if book_info['id'] else 'Not found'}")
        
        if book_info['title']['series'] and book_info['title']['series']['name']:
            series_text = f"{book_info['title']['series']['name']}"
            if book_info['title']['series']['id']:
                series_text += f" (ID: {book_info['title']['series']['id']})"
            if book_info['title']['series']['number']:
                series_text += f" #{book_info['title']['series']['number']}"
            print(f"{'Series:':<15} {series_text}")
            
        if book_info['additional_series']:
            print(f"{'Alt Series:':<15} {', '.join(f'{series['name']} (ID: {series['id']})' for series in book_info['additional_series'])}")
            
        if book_info['authors']:
            first_author = True
            for author in book_info['authors']:
                author_str = f"{author['name']} (ID: {author['id']}) ({author['role']})"
                if first_author:
                    print(f"{'Authors:':<15} {author_str}")
                    first_author = False
                else:
                    print(f"{'':<15} {author_str}")

        if book_info['genres']:
            print(f"{'Genres:':<15} {', '.join(genre['name'] for genre in book_info['genres'])}")
        print("=" * 80)

@cli.command()
@click.argument('author_id')
def author(author_id):
    """Scrape an author by their ID"""
    author_info = scrape_author(author_id)
    if author_info:
        print("\n" + "=" * 80)
        print(f"{'Name:':<15}{author_info['name'].strip()}")
        print(f"{'ID:':<15}{author_info['id'].strip()}")
        if author_info['photo_url']:
            print(f"{'Photo URL:':<15}{author_info['photo_url'].strip()}")
        if author_info['bio']:
            truncated_bio = author_info['bio'][:100].strip() + "..." if len(author_info['bio']) > 100 else author_info['bio'].strip()
            print(f"{'Bio:':<15}{truncated_bio}")
        print("=" * 80)

@cli.command()
@click.argument('author_id')
def author_books(author_id):
    """Scrape all books by an author"""
    result = scrape_author_books(author_id)
    if result:
        print("\n" + "=" * 80)
        print(f"{'Author:':<15}{result['author_name']}")
        print(f"{'ID:':<15}{result['author_id']}")
        for book in result['books']:
            print(f"{'':<15}{book['title']} (ID: {book['id']})")
        print("=" * 80)

@cli.command()
@click.argument('series_id')
def series(series_id):
    """Scrape a series by its ID"""
    series_info = scrape_series(series_id)
    if series_info:
        print("\n" + "=" * 80)
        print(f"{'Name:':<15}{series_info['name']}")
        print(f"{'ID:':<15}{series_info['id']}")
        if series_info['books']:
            first_book = True
            for book in series_info['books']:
                book_str = f"{book['title']} (ID: {book['id']})"
                if book['number'] is not None:
                    book_str += f" - Book {book['number']}"
                if first_book:
                    print(f"{'Books:':<15}{book_str}")
                    first_book = False
                else:
                    print(f"{'':<15}{book_str}")
        print("=" * 80)

@cli.command()
@click.argument('book_id')
def similar(book_id):
    """Find similar books"""
    result = scrape_similar(book_id)
    if result:
        main_book, similar_books = result
        print("\n" + "=" * 80)
        if main_book:
            print(f"{'Book:':<15}{main_book['title']} (ID: {main_book['id']})")
            print(f"{'Similar:':<15}{len(similar_books)} books found")
            for book in similar_books:
                print(f"{'':<15}{book['title']} (ID: {book['id']})")
        print("=" * 80)

@cli.command()
@click.argument('work_id')
def editions(work_id):
    """Scrape all editions of a book"""
    first_edition, all_editions = scrape_editions(work_id)
    if all_editions:
        print("\n" + "=" * 80)
        if first_edition and first_edition.get('title') and first_edition.get('id'):
            print(f"{'Book:':<15}{first_edition['title']} (ID: {first_edition['id']})")
        print(f"{'Editions:':<15}{len(all_editions)} found")
        for edition in all_editions:
            if first_edition and edition['id'] == first_edition.get('id'):
                continue
            print(f"{'':<15}{edition['title']} (ID: {edition['id']})")
        print("=" * 80)

if __name__ == '__main__':
    cli()