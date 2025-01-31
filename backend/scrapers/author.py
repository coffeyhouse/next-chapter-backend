import os
from bs4 import BeautifulSoup
from pathlib import Path
import re
import json
from backend.utils.downloader import GoodreadsDownloader
from backend.utils.image_downloader import download_author_photo

def get_author_url(author_id):
    return f"https://www.goodreads.com/author/show/{author_id}"

def extract_author_id(soup):
    # Look for the edit data link which contains the author ID
    edit_link = soup.find('a', href=lambda x: x and '/author/edit/' in x)
    if edit_link:
        id_match = re.search(r'/author/edit/(\d+)', edit_link['href'])
        if id_match:
            return id_match.group(1)
    return None

def extract_author_name(soup):
    name_element = soup.find('h1', class_='authorName')
    if name_element:
        name_span = name_element.find('span', itemprop='name')
        if name_span:
            # Split the name into words and join them with a single space
            return ' '.join(name_span.text.split())
    return None

def extract_author_bio(soup):
    bio_div = soup.find('div', class_='aboutAuthorInfo')
    if bio_div:
        bio_span = bio_div.find('span', id=lambda x: x and x.startswith('freeTextContainer'))
        if bio_span:
            return bio_span.text.strip()
    return None

def extract_author_photo(soup):
    img = soup.find('img', class_='authorPhotoImg')
    if img and 'src' in img.attrs:
        return img['src']
    return None

def extract_series_info(series_div):
    series = {
        'name': None,
        'id': None
    }
    
    # Extract name and ID
    series_link = series_div.find('a', class_='bookTitle')
    if series_link:
        series['name'] = series_link.text.strip()
        url_match = re.search(r'/series/(\d+)', series_link['href'])
        if url_match:
            series['id'] = url_match.group(1)
    
    return series

def extract_author_photo_url(soup):
    """Extract the author photo URL from the page"""
    # Try authorPhotoImg class first
    img = soup.find('img', class_='authorPhotoImg')
    if img and 'src' in img.attrs:
        return img['src']
        
    # Try alt text containing author as fallback
    img = soup.find('img', alt=lambda x: x and 'author' in x.lower())
    if img and 'src' in img.attrs:
        return img['src']
        
    # Try leftContainer authorLeftContainer as another fallback
    container = soup.find('div', class_='leftContainer authorLeftContainer')
    if container:
        img = container.find('img')
        if img and 'src' in img.attrs:
            return img['src']
            
    return None

def scrape_author(author_id, scrape=False):
    """Scrape author information from Goodreads
    
    Args:
        author_id (str): Goodreads author ID
        scrape (bool): If True, use proxy to scrape. If False, only use cached files.
        
    Returns:
        dict: Author information or None if not found
    """
    # Initialize downloader with scrape flag
    downloader = GoodreadsDownloader(scrape=scrape)
    
    # Get author URL
    url = get_author_url(author_id)
    
    # Download/retrieve the HTML content
    success = downloader.download_url(url)
    if not success:
        print(f"Failed to get content for author ID: {author_id}")
        return None
        
    # Construct the path where the file was saved
    local_path = Path('data/exported_html') / 'author' / 'show' / f"{author_id}.html"
    
    try:
        # Read the downloaded HTML
        with open(local_path, 'r', encoding='utf-8') as f:
            html_content = f.read()
            
        # Parse and extract information
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Extract all info
        author_info = {
            'goodreads_id': extract_author_id(soup),
            'name': extract_author_name(soup),
            'bio': extract_author_bio(soup),
            'image_url': extract_author_photo(soup),
            'series': []
        }
        
        # Extract and download photo
        photo_url = extract_author_photo_url(soup)
        if photo_url:
            local_path = download_author_photo(author_id, photo_url)
            if local_path:
                author_info['image_url'] = local_path
        
        # Extract series
        series_divs = soup.find_all('div', class_='bookRow seriesBookRow')
        for series_div in series_divs:
            series_info = extract_series_info(series_div)
            if series_info['name'] and series_info['id']:
                author_info['series'].append(series_info)
        
        return author_info
        
    except Exception as e:
        print(f"Error processing author ID {author_id}: {str(e)}")
        return None

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python -m backend.scrapers.author <author_id> [--scrape]")
        sys.exit(1)
        
    author_id = sys.argv[1]
    scrape = "--scrape" in sys.argv
    scrape_author(author_id, scrape=scrape)