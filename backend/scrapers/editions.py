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
    """Scrape editions until an English one is found
    
    Args:
        work_id (str): Goodreads work ID
        scrape (bool): If True, use proxy to scrape. If False, only use cached files.
        
    Returns:
        tuple: (first_edition, english_edition) or (first_edition, None) if no English edition found
    """
    downloader = GoodreadsDownloader(scrape=scrape)
    current_page = 1
    first_edition = None
    english_edition = None
    
    while True:
        # Get URL for current page
        url = get_editions_url(work_id, current_page)
        
        # Download/retrieve the HTML content
        success = downloader.download_url(url)
        if not success:
            print(f"Failed to get content for page {current_page} of work ID: {work_id}")
            break
        
        # Construct the path where the file was saved
        query_params = f"page={current_page}&per_page=100&utf8=%E2%9C%93"
        local_path = Path('data/exported_html/work/editions') / f"{work_id}{query_params}.html"
        
        try:
            # Read the HTML file
            with open(local_path, 'r', encoding='utf-8') as f:
                html_content = f.read()
            
            # Parse and extract information
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Get the main book info if we're on the first page
            if current_page == 1:
                first_edition = extract_book_info(soup)
            
            # Extract editions from this page
            editions = extract_books(soup)
            
            # Check each edition for English language
            for edition in editions:
                if edition['id'] and edition.get('language', '').lower() == 'english':
                    book_info = scrape_book(edition['id'], scrape=scrape)
                    if book_info:
                        book_info['language'] = 'English'  # Ensure language is set
                        english_edition = book_info
                        print(f"Found English edition: {edition['id']}")
                        return first_edition, english_edition
            
            # Get pagination info
            pagination = extract_pagination_info(soup)
            print(f"Processing page {pagination['current_page']} of {pagination['total_pages']}")
            
            # Break if we've reached the last page
            if current_page >= pagination['total_pages']:
                break
                
            current_page += 1
            
        except Exception as e:
            print(f"Error processing page {current_page} for work ID {work_id}: {str(e)}")
            break
            
    # Return None if no English edition found
    return first_edition, None

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python -m backend.scrapers.editions <work_id> [--scrape]")
        sys.exit(1)
        
    work_id = sys.argv[1]
    scrape = "--scrape" in sys.argv
    scrape_editions(work_id, scrape=scrape)