from pathlib import Path
from bs4 import BeautifulSoup
import sys
import json
import re
from collections import defaultdict
from backend.scrapers.book import scrape_book
from backend.utils.downloader import GoodreadsDownloader
from urllib.parse import urlencode
from backend.utils.data_transformer import transform_editions_data, print_transformed_data

example_html_dir = Path('exported_html/work/editions')

def get_editions_url(work_id, page=1):
    base_url = f"https://www.goodreads.com/work/editions/{work_id}"
    params = {
        'page': page,
        'per_page': 100,
        'utf8': '✓'
    }
    return f"{base_url}?{urlencode(params)}"

def extract_book_info(soup):
    book_info = {
        'title': None,
        'id': None
    }
    
    # Look for the h1 with the main book link
    title_element = soup.find('h1')
    if title_element:
        book_link = title_element.find('a')
        if book_link:
            book_info['title'] = book_link.text.strip()
            url_match = re.search(r'/show/(\d+)', book_link['href'])
            if url_match:
                book_info['id'] = url_match.group(1)
    
    return book_info

def extract_books(soup):
    books = []
    edition_elements = soup.find_all('div', class_='elementList clearFix')
    
    for edition in edition_elements:
        book_info = {
            'id': None,
            'title': None,
            'format': None,
            'published': None,
            'isbn': None,
            'language': None
        }
        
        # Get book ID and title
        book_link = edition.find('a', class_='bookTitle')
        if book_link:
            book_info['title'] = book_link.text.strip()
            url_match = re.search(r'/show/(\d+)', book_link['href'])
            if url_match:
                book_info['id'] = url_match.group(1)
        
        # Get format, publication info, and language
        details = edition.find('div', class_='editionData')
        if details:
            text = details.get_text(' ', strip=True)
            
            # Extract language
            language_div = details.find('div', text=lambda x: x and 'Edition language:' in x)
            if language_div and language_div.find_next('div', class_='dataValue'):
                book_info['language'] = language_div.find_next('div', class_='dataValue').text.strip()
            
            # Extract format
            format_match = re.search(r'(Paperback|Hardcover|Kindle Edition|ebook|Audio CD|Mass Market Paperback|Unknown Binding)', text, re.IGNORECASE)
            if format_match:
                book_info['format'] = format_match.group(1)
            
            # Extract publication year
            year_match = re.search(r'published\s*(\d{4})', text)
            if year_match:
                book_info['published'] = year_match.group(1)
                
            # Extract ISBN
            isbn_match = re.search(r'ISBN\s*(\d{10}|\d{13})', text)
            if isbn_match:
                book_info['isbn'] = isbn_match.group(1)
        
        if book_info['id'] and book_info['title']:
            books.append(book_info)
            
    return books

def extract_pagination_info(soup):
    pagination = {'current_page': 1, 'total_pages': 1}
    
    pagination_div = soup.find('div', style=lambda x: x and 'text-align: right' in x)
    if pagination_div:
        # Get current page from the em element with class="current"
        current = pagination_div.find('em', class_='current')
        if current:
            try:
                pagination['current_page'] = int(current.text.strip())
            except ValueError:
                pass
        
        # Get all page links
        page_links = pagination_div.find_all('a')
        max_page = 1
        
        for link in page_links:
            try:
                page_num = int(link.text.strip())
                max_page = max(max_page, page_num)
            except ValueError:
                continue
                
        pagination['total_pages'] = max(max_page, pagination['current_page'])
        
        print(f"Debug - Found pagination: current={pagination['current_page']}, total={pagination['total_pages']}")
    else:
        print("Debug - No pagination div found")
    
    return pagination

def scrape_editions(work_id, scrape=False):
    """Scrape editions and find best format in preferred order, then check language
    
    Args:
        work_id (str): Goodreads work ID
        scrape (bool): If True, use proxy to scrape. If False, only use cached files.
        
    Returns:
        tuple: (first_edition, best_edition) or (first_edition, None) if no suitable edition found
    """
    # Preferred format order
    preferred_formats = [
        'Kindle Edition',
        'Paperback',
        'Hardcover', 
        'Mass Market Paperback',
        'ebook'
    ]
    
    downloader = GoodreadsDownloader(scrape=scrape)
    current_page = 1
    first_edition = None
    editions_by_format = {fmt: [] for fmt in preferred_formats}
    other_editions = []
    
    while True:
        url = get_editions_url(work_id, current_page)
        success = downloader.download_url(url)
        if not success:
            print(f"Failed to get content for page {current_page} of work ID: {work_id}")
            break
            
        query_params = f"page={current_page}&per_page=100&utf8=%E2%9C%93"
        local_path = Path('data/exported_html/work/editions') / f"{work_id}{query_params}.html"
        
        try:
            with open(local_path, 'r', encoding='utf-8') as f:
                html_content = f.read()
            
            soup = BeautifulSoup(html_content, 'html.parser')
            
            if current_page == 1:
                first_edition = extract_book_info(soup)
            
            editions = extract_books(soup)
            
            # Sort editions by format
            for edition in editions:
                if not edition['id']:
                    continue
                    
                edition_format = edition.get('format')
                if edition_format in preferred_formats:
                    editions_by_format[edition_format].append(edition)
                else:
                    other_editions.append(edition)
            
            # Get pagination info
            pagination = extract_pagination_info(soup)
            print(f"Processing page {pagination['current_page']} of {pagination['total_pages']}")
            
            if current_page >= pagination['total_pages']:
                break
                
            current_page += 1
            
        except Exception as e:
            print(f"Error processing page {current_page} for work ID {work_id}: {str(e)}")
            break
    
    # Try editions in preferred format order
    for format_type in preferred_formats:
        format_editions = editions_by_format[format_type]
        print(f"Checking {len(format_editions)} editions of format: {format_type}")
        
        for edition in format_editions:
            try:
                book_info = scrape_book(edition['id'], scrape=scrape)
                if not book_info:
                    continue
                
                # Safely get language value with default to empty string
                language = book_info.get('details', {}).get('language') or ''
                
                if language.lower() == 'english':
                    print(f"Found English edition in {format_type} format: {edition['id']}")
                    return first_edition, book_info
                else:
                    print(f"Skipping non-English edition (language: {language})")
            except Exception as e:
                print(f"Error processing edition {edition['id']}: {str(e)}")
                continue
    
    # If no preferred format found, try other editions
    print(f"Checking {len(other_editions)} editions of other formats")
    for edition in other_editions:
        try:
            book_info = scrape_book(edition['id'], scrape=scrape)
            if not book_info:
                continue
            
            # Safely get language value with default to empty string
            language = book_info.get('details', {}).get('language') or ''
            
            if language.lower() == 'english':
                print(f"Found English edition in format: {edition.get('format', 'Unknown')}")
                return first_edition, book_info
            else:
                print(f"Skipping non-English edition (language: {language})")
        except Exception as e:
            print(f"Error processing edition {edition['id']}: {str(e)}")
            continue
            
    print("No English editions found")
    return first_edition, None

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python -m backend.scrapers.editions <work_id> [--scrape]")
        sys.exit(1)
        
    work_id = sys.argv[1]
    scrape = "--scrape" in sys.argv
    scrape_editions(work_id, scrape=scrape)