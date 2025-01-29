from pathlib import Path
from bs4 import BeautifulSoup
import json
import re
from backend.utils.downloader import GoodreadsDownloader
from urllib.parse import urlencode
from backend.utils.data_transformer import transform_author_books_data, print_transformed_data

def get_author_books_url(author_id, page=1):
    base_url = f"https://www.goodreads.com/author/list/{author_id}"
    params = {
        'page': page,
        'per_page': 100,
        'utf8': '✓',
        'sort': 'original_publication_year'
    }
    return f"{base_url}?{urlencode(params)}"

def extract_author_name(soup):
    name_link = soup.find('a', class_='authorName')
    if name_link:
        return name_link.text.strip()
    return None

def extract_books(soup):
    books = []
    book_rows = soup.find_all('tr', itemtype='http://schema.org/Book')
    
    for row in book_rows:
        book = {'id': None, 'title': None, 'publication': None}
        
        # Get book ID and title from the book link
        book_link = row.find('a', class_='bookTitle')
        if book_link:
            book['title'] = book_link.find('span', itemprop='name').text.strip()
            url_match = re.search(r'/show/(\d+)', book_link['href'])
            if url_match:
                book['id'] = url_match.group(1)
                
        # Get publication info
        grey_text = row.find('span', class_='greyText smallText uitext')
        if grey_text:
            text_content = grey_text.get_text(strip=True)
            
            # Check for publication info
            if 'expected publication' in text_content:
                year_match = re.search(r'expected publication\s*(\d{4})', text_content)
                if year_match:
                    book['publication'] = year_match.group(1)
            elif 'published' in text_content:
                year_match = re.search(r'published\s*(\d{4})', text_content)
                if year_match:
                    book['publication'] = year_match.group(1)
        
        if book['id'] and book['title']:
            books.append(book)
            
    return books

def extract_pagination_info(soup):
    pagination = {'current_page': 1, 'total_pages': 1}
    
    pagination_div = soup.find('div', style='float: right')
    if pagination_div:
        current = pagination_div.find('em', class_='current')
        if current:
            try:
                pagination['current_page'] = int(current.text.strip())
            except ValueError:
                pass
        
        page_links = pagination_div.find_all('a')
        max_page = 1
        
        for link in page_links:
            try:
                page_num = int(link.text.strip())
                max_page = max(max_page, page_num)
            except ValueError:
                continue
                
        pagination['total_pages'] = max_page
    
    return pagination

def scrape_author_books(author_id, scrape=False):
    """Scrape all books by an author from Goodreads
    
    Args:
        author_id (str): Goodreads author ID
        scrape (bool): If True, use proxy to scrape. If False, only use cached files.
        
    Returns:
        dict: Author books information or None if not found
    """
    downloader = GoodreadsDownloader(scrape=scrape)
    all_books = []
    author_name = None
    current_page = 1
    
    while True:
        # Get URL for current page
        url = get_author_books_url(author_id, current_page)
        
        # Download/retrieve the HTML content
        success = downloader.download_url(url)
        if not success:
            print(f"Failed to get content for page {current_page} of author ID: {author_id}")
            # If we have books from previous pages, return them
            if all_books:
                break
            return None
        
        # Construct the path where the file was saved
        query_params = f"page={current_page}&per_page=100&utf8=%E2%9C%93&sort=original_publication_year"
        local_path = Path('data/exported_html/author/list') / f"{author_id}{query_params}.html"
        
        try:
            # Read the HTML file
            with open(local_path, 'r', encoding='utf-8') as f:
                html_content = f.read()
            
            # Parse and extract information
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Get author name if we don't have it yet
            if not author_name:
                author_name = extract_author_name(soup)
            
            # Extract books from this page
            books = extract_books(soup)
            all_books.extend(books)
            
            # Get pagination info
            pagination = extract_pagination_info(soup)
            print(f"Processing page {pagination['current_page']} of {pagination['total_pages']}")
            
            # Break if we've reached the last page
            if current_page >= pagination['total_pages']:
                break
                
            current_page += 1
            
        except Exception as e:
            print(f"Error processing page {current_page} for author ID {author_id}: {str(e)}")
            # If we have books from previous pages, return them
            if all_books:
                break
            return None
        
    # Filter to only include books with publication data
    published_books = [book for book in all_books if book['publication'] is not None]
    
    return {
        'author_name': author_name,
        'author_id': author_id,
        'books': published_books
    }

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python -m backend.scrapers.author_books <author_id> [--scrape]")
        sys.exit(1)
        
    author_id = sys.argv[1]
    scrape = "--scrape" in sys.argv
    scrape_author_books(author_id, scrape=scrape)