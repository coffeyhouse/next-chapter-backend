import os
from pathlib import Path
from bs4 import BeautifulSoup
import json
import re
from collections import defaultdict
from backend.utils.downloader import GoodreadsDownloader
from urllib.parse import urlencode

example_html_dir = Path('exported_html/work/editions')

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

def extract_work_id_from_url(url):
    # Extract work ID from the filename directly
    id_match = re.search(r'(\d+)', url)
    if id_match:
        return id_match.group(1)
    return None

def extract_page_number(url):
    page_match = re.search(r'page=(\d+)', url)
    if page_match:
        return page_match.group(1)
    return '1'

def extract_next_page(soup):
    next_page_link = soup.find('a', class_='next_page')
    if next_page_link and 'href' in next_page_link.attrs:
        return next_page_link['href']
    return None

def extract_books(soup):
    books = []
    edition_elements = soup.find_all('div', class_='elementList clearFix')
    
    for edition in edition_elements:
        book_info = {
            'id': None,
            'title': None,
            'format': None,
            'published': None,
            'isbn': None
        }
        
        # Get book ID and title
        book_link = edition.find('a', class_='bookTitle')
        if book_link:
            book_info['title'] = book_link.text.strip()
            url_match = re.search(r'/show/(\d+)', book_link['href'])
            if url_match:
                book_info['id'] = url_match.group(1)
        
        # Get format and publication info
        details = edition.find('div', class_='editionData')
        if details:
            text = details.get_text(' ', strip=True)
            
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

def extract_editions_info(file_path, html_content):
    soup = BeautifulSoup(html_content, 'html.parser')
    work_id = extract_work_id_from_url(file_path.name)
    page_num = extract_page_number(file_path.name)
    
    print(f"Processing Work ID: {work_id} (Page {page_num})")
    print("=" * 80)

    # Extract book info
    books = extract_books(soup)
    for book in books:
        print(f"Book Title: {book['title']}, Book ID: {book['id']}")

    # Extract and process the next page if it exists
    next_page = extract_next_page(soup)
    if next_page:
        next_page_url = f"https://www.goodreads.com{next_page}"
        print(f"Next page URL: {next_page_url}")

def process_editions_file(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            html_content = file.read()
            extract_editions_info(file_path, html_content)
    except Exception as e:
        print(f"Error processing {file_path}: {str(e)}")

def process_editions_files():
    if not example_html_dir.exists():
        raise Exception(f"Directory not found: {example_html_dir}")
        
    # Group files by work ID
    work_files = defaultdict(list)
    for file_path in example_html_dir.glob('*.html'):
        print(f"Found file: {file_path.name}")  # Debugging line
        work_id = extract_work_id_from_url(file_path.name)
        if work_id:
            work_files[work_id].append(file_path)
    
    # Check if any work files were found
    if not work_files:
        print("No work files found.")
        return
    
    # Process each work's files
    for work_id, files in work_files.items():
        all_books = []
        
        # Process all pages for this work
        for file_path in files:
            with open(file_path, 'r', encoding='utf-8') as f:
                html_content = f.read()
            soup = BeautifulSoup(html_content, 'html.parser')
            
            book_info = extract_book_info(soup)
            books = extract_books(soup)
            all_books.extend(books)
        
        # Print combined results for this work
        print("\n" + "=" * 80)
        print(f"Book: {book_info['name']} (ID: {book_info['id']})")
        print(f"Books: {len(all_books)} found")
        for book in all_books:
            print(f"{'':<15}{book['title']} (ID: {book['id']})")
        print("=" * 80)

def get_editions_url(work_id, page=1):
    base_url = f"https://www.goodreads.com/work/editions/{work_id}"
    params = {
        'page': page,
        'per_page': 100,
        'utf8': '✓'
    }
    return f"{base_url}?{urlencode(params)}"

def extract_pagination_info(soup):
    pagination = {'current_page': 1, 'total_pages': 1}
    
    # Updated to find pagination div with style containing "text-align: right"
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

def scrape_editions(work_id):
    downloader = GoodreadsDownloader()
    all_editions = []
    current_page = 1
    first_edition = None
    
    while True:
        # Get URL for current page
        url = get_editions_url(work_id, current_page)
        
        # Download the HTML content
        success = downloader.download_url(url)
        if not success:
            print(f"Failed to download page {current_page} for work ID: {work_id}")
            break
        
        # Construct the path where the file was saved
        query_params = f"page={current_page}&per_page=100&utf8=%E2%9C%93"
        local_path = Path('data/exported_html/work/editions') / f"{work_id}{query_params}.html"
        
        try:
            # Read the downloaded HTML
            with open(local_path, 'r', encoding='utf-8') as f:
                html_content = f.read()
            
            # Parse and extract information
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Get the main book info if we're on the first page
            if current_page == 1:
                first_edition = extract_book_info(soup)
            
            # Extract editions from this page
            editions = extract_books(soup)
            all_editions.extend(editions)
            
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
    
    return first_edition, all_editions

def main():
    import sys
    
    if len(sys.argv) != 2:
        print("Usage: python -m backend.scrapers.editions <work_id>")
        sys.exit(1)
        
    work_id = sys.argv[1]
    first_edition, editions = scrape_editions(work_id)
    
    if editions:
        print("\n" + "=" * 80)
        if first_edition and first_edition.get('title') and first_edition.get('id'):
            print(f"Book: {first_edition['title']} (ID: {first_edition['id']})")
        print(f"Books: {len(editions) - 1} found")
        for edition in editions:
            # Skip if this edition is the first edition
            if first_edition and edition['id'] == first_edition.get('id'):
                continue
            print(f"{'':<15}{edition['title']} (ID: {edition['id']})")
        print("=" * 80)

if __name__ == "__main__":
    main()