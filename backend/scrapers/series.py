from pathlib import Path
from bs4 import BeautifulSoup
import sys
import re
from backend.utils.data_transformer import transform_series_data, print_transformed_data
from backend.utils.downloader import GoodreadsDownloader

example_html_dir = Path('exported_html/series')

def extract_series_name(soup):
    title_element = soup.find('h1', class_='gr-h1--serif')
    if title_element:
        name = title_element.text.strip()
        # Remove " Series" from the end if present
        if name.endswith(' Series'):
            name = name[:-7]
        return name
    return None

def extract_series_id(soup):
    canonical_link = soup.find('link', rel='canonical')
    if canonical_link and 'href' in canonical_link.attrs:
        id_match = re.search(r'/series/(\d+)', canonical_link['href'])
        if id_match:
            return id_match.group(1)
    return None

def extract_book_info(book_div):
    book = {
        'number': None,
        'title': None,
        'id': None
    }
    
    # Extract series number
    number_heading = book_div.find('h3', class_='gr-h3--noBottomMargin')
    if number_heading:
        number_text = number_heading.text.strip()
        try:
            if number_text.startswith('Book '):
                number_text = number_text[5:]
            if '-' in number_text:
                book['number'] = number_text
            else:
                book['number'] = float(number_text)
        except ValueError:
            pass
    
    # Extract title and ID
    title_link = book_div.find('a', class_='gr-h3--serif')
    if title_link:
        book['title'] = title_link.find('span', itemprop='name').text.strip()
        url_match = re.search(r'/show/(\d+)', title_link['href'])
        if url_match:
            book['id'] = url_match.group(1)
    
    return book

def extract_books(soup):
    books = []
    book_divs = soup.find_all('div', class_='listWithDividers__item')
    
    for book_div in book_divs:
        book_info = extract_book_info(book_div)
        if book_info['title'] and book_info['id']:
            books.append(book_info)
    
    return books

def extract_series_info(file_path, html_content):
    soup = BeautifulSoup(html_content, 'html.parser')
    
    books = []
    book_divs = soup.find_all('div', class_='listWithDividers__item')
    
    for book_div in book_divs:
        book_info = extract_book_info(book_div)
        if book_info['title'] and book_info['id']:
            books.append(book_info)
    
    # Extract series name and ID from URL
    series_name = extract_series_name(soup)
    series_id = extract_series_id(soup)
    
    # Print table
    print("\n" + "=" * 80)
    print(f"{'Name:':<15} {series_name}")
    print(f"{'ID:':<15} {series_id}")
    if books:
        first_book = True
        for book in books:
            book_str = f"{book['title']} (ID: {book['id']})"
            if book['number'] is not None:
                book_str += f" - Book {book['number']}"
            
            if first_book:
                print(f"{'Books:':<15} {book_str}")
                first_book = False
            else:
                print(f"{'':<15} {book_str}")
    print("=" * 80)

def get_series_url(series_id):
    return f"https://www.goodreads.com/series/show/{series_id}"

def scrape_series(series_id):
    # Initialize downloader
    downloader = GoodreadsDownloader()
    
    # Get series URL
    url = get_series_url(series_id)
    
    # Download the HTML content
    success = downloader.download_url(url)
    if not success:
        print(f"Failed to download series ID: {series_id}")
        return None
        
    # Construct the path where the file was saved
    local_path = Path('data/exported_html') / 'series' / 'show' / f"{series_id}.html"
    
    try:
        # Read the downloaded HTML
        with open(local_path, 'r', encoding='utf-8') as f:
            html_content = f.read()
            
        # Parse and extract information
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Extract all info
        series_info = {
            'id': series_id,
            'name': extract_series_name(soup),
            'books': extract_books(soup)
        }
        
        return series_info
        
    except Exception as e:
        print(f"Error processing series ID {series_id}: {str(e)}")
        return None

def main():
    if len(sys.argv) != 2:
        print("Usage: python -m backend.scrapers.series <series_id>")
        sys.exit(1)
        
    series_id = sys.argv[1]
    scrape_series(series_id)

if __name__ == "__main__":
    main()