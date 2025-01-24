from pathlib import Path
from bs4 import BeautifulSoup
import json
import re
from backend.utils.downloader import GoodreadsDownloader

def get_similar_url(book_id):
    return f"https://www.goodreads.com/book/similar/{book_id}"

def extract_book_info(div):
    book = {'id': None, 'title': None}
    
    # Get book link which contains ID and title
    book_link = div.find('a', class_='gr-h3')
    if book_link:
        # Extract ID from URL
        url_match = re.search(r'/show/(\d+)', book_link['href'])
        if url_match:
            book['id'] = url_match.group(1)
        
        # Extract title
        title_span = book_link.find('span', itemprop='name')
        if title_span:
            book['title'] = title_span.text.strip()
    
    return book if book['id'] and book['title'] else None

def extract_similar_books(soup):
    book_divs = soup.find_all('div', class_='u-paddingBottomXSmall')
    
    if not book_divs:
        return None, []
        
    # First div is the main book
    main_book = extract_book_info(book_divs[0])
    
    # Rest are similar books
    similar_books = []
    for div in book_divs[1:]:
        book = extract_book_info(div)
        if book:
            similar_books.append(book)
            
    return main_book, similar_books

def scrape_similar(book_id):
    # Initialize downloader
    downloader = GoodreadsDownloader()
    
    # Get URL
    url = get_similar_url(book_id)
    
    # Download the HTML content
    success = downloader.download_url(url)
    if not success:
        print(f"Failed to download similar books for book ID: {book_id}")
        return None
        
    # Construct the path where the file was saved
    local_path = Path('data/exported_html') / 'book' / 'similar' / f"{book_id}.html"
    
    try:
        # Read the downloaded HTML
        with open(local_path, 'r', encoding='utf-8') as f:
            html_content = f.read()
            
        # Parse and extract information
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Extract similar books
        main_book, similar_books = extract_similar_books(soup)
        return main_book, similar_books
        
    except Exception as e:
        print(f"Error processing similar books for book ID {book_id}: {str(e)}")
        return None

def main():
    import sys
    
    if len(sys.argv) != 2:
        print("Usage: python -m backend.scrapers.similar <book_id>")
        sys.exit(1)
        
    book_id = sys.argv[1]
    result = scrape_similar(book_id)
    
    if result:
        main_book, similar_books = result
        print("\n" + "=" * 80)
        if main_book:
            print(f"Book:{'':<10} {main_book['title']} (ID: {main_book['id']})")
            print(f"Similar:{'':<7} {len(similar_books)} books found")
            for book in similar_books:
                print(f"{'':<15}{book['title']} (ID: {book['id']})")
        print("=" * 80)

if __name__ == "__main__":
    main() 