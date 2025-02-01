# core/scrapers/book_scraper.py
from bs4 import BeautifulSoup
from pathlib import Path
import re
import json
from datetime import datetime
from ..utils.http import GoodreadsDownloader
from ..utils.image import download_book_cover

class BookScraper:
    """Scrapes a book page from Goodreads"""
    
    def __init__(self, scrape: bool = False):
        self.downloader = GoodreadsDownloader(scrape)
        
    def scrape_book(self, book_id: str) -> dict:
        """
        Get book data from Goodreads book page
        Expected output:
        {
            'goodreads_id': str,
            'title': str,
            'description': str,
            'language': str,
            'pages': int,
            'published_date': str,
            'isbn': str,
            'image_url': str,
            'rating': float,
            'rating_count': int,
            'authors': [
                {
                    'goodreads_id': str,
                    'name': str,
                    'role': str
                }
            ],
            'series': [
                {
                    'goodreads_id': str,
                    'name': str,
                    'order': float
                }
            ],
            'genres': [
                {
                    'name': str
                }
            ]
        }
        """
        print(f"Scraping book: {book_id}")
        
        # Get book page content
        url = self._get_book_url(book_id)
        if not self.downloader.download_url(url):
            print(f"Failed to download book page for ID: {book_id}")
            return None
            
        # Parse HTML
        html = self._read_html(book_id)
        if not html:
            return None
            
        try:
            soup = BeautifulSoup(html, 'html.parser')
            book_data = {
                'goodreads_id': book_id,
                'title': self._extract_title(soup),
                'description': self._extract_description(soup),
                'language': None,
                'pages': None,
                'isbn': None,
                'rating': None,
                'rating_count': None,
                'published_date': None,
                'image_url': None
            }
            
            # Extract book details
            details = self._extract_book_details(soup)
            book_data.update({
                'language': details.get('language'),
                'pages': details.get('pages'),
                'isbn': details.get('isbn'),
                'rating': details.get('rating'),
                'rating_count': details.get('rating_count')
            })
            
            # Get publication date
            pub_info = self._extract_publication_info(soup)
            book_data['published_date'] = pub_info.get('date')
            
            # Get relationships
            book_data['authors'] = self._extract_authors(soup)
            book_data['series'] = self._extract_series(soup)
            book_data['genres'] = self._extract_genres(soup)
            
            # Get cover image
            cover_url = self._extract_cover_url(soup)
            if cover_url:
                local_path = download_book_cover(book_id, cover_url)
                if local_path:
                    book_data['image_url'] = local_path
            
            return book_data
            
        except Exception as e:
            print(f"Error parsing book data: {e}")
            return None
    
    def _get_book_url(self, book_id: str) -> str:
        """Get Goodreads URL for book"""
        return f"https://www.goodreads.com/book/show/{book_id}"
    
    def _read_html(self, book_id: str) -> str:
        """Read downloaded HTML file"""
        path = Path('data/cache/book/show') / f"{book_id}.html"
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            print(f"Error reading HTML file: {e}")
            return None
    
    def _extract_title(self, soup) -> str:
        """Extract book title"""
        title_element = soup.find('h1', attrs={'data-testid': 'bookTitle'})
        if title_element:
            return title_element['aria-label'].replace('Book title:', '').strip()
        return None
    
    def _extract_description(self, soup) -> str:
        """Extract book description"""
        next_data = soup.find('script', id='__NEXT_DATA__')
        if next_data:
            try:
                data = json.loads(next_data.string)
                for key, value in data['props']['pageProps']['apolloState'].items():
                    if key.startswith('Book:') and isinstance(value, dict):
                        return value.get('description')
            except (json.JSONDecodeError, KeyError):
                pass
        return None
    
    def _extract_book_details(self, soup) -> dict:
        """Extract book details from schema.org data"""
        schema = soup.find('script', {'type': 'application/ld+json'})
        if schema:
            try:
                data = json.loads(schema.string)
                return {
                    'language': data.get('inLanguage'),
                    'pages': data.get('numberOfPages'),
                    'isbn': data.get('isbn'),
                    'rating': data.get('aggregateRating', {}).get('ratingValue'),
                    'rating_count': data.get('aggregateRating', {}).get('ratingCount')
                }
            except json.JSONDecodeError:
                pass
        return {}
    
    def _extract_publication_info(self, soup) -> dict:
        """Extract publication date"""
        pub_element = soup.find('p', attrs={'data-testid': 'publicationInfo'})
        if pub_element:
            text = pub_element.text.strip()
            for prefix in ['Published ', 'First published ', 'Expected publication ']:
                if text.startswith(prefix):
                    return {'date': text.replace(prefix, '').strip()}
        return {}
    
    def _extract_authors(self, soup) -> list:
        """Extract author information"""
        authors = []
        author_links = soup.find_all('a', class_='ContributorLink')
        
        for link in author_links:
            name_span = link.find('span', class_='ContributorLink__name')
            if not name_span:
                continue
                
            author = {
                'name': name_span.text.strip(),
                'goodreads_id': None,
                'role': 'Author'
            }
            
            # Get author ID from URL
            if 'href' in link.attrs:
                id_match = re.search(r'/author/show/(\d+)', link['href'])
                if id_match:
                    author['goodreads_id'] = id_match.group(1)
            
            # Get role if specified
            role_span = link.find('span', class_='ContributorLink__role')
            if role_span:
                author['role'] = role_span.text.strip('()').strip()
            
            authors.append(author)
            
        return authors
    
    def _extract_series(self, soup) -> list:
        """Extract series information"""
        series = []
        series_element = soup.find('h3', class_='Text__title3', 
                                 attrs={'aria-label': lambda x: x and 'Book' in x and 'series' in x})
        
        if series_element:
            series_link = series_element.find('a')
            if series_link:
                # Get series ID
                id_match = re.search(r'/series/(\d+)', series_link['href'])
                if id_match:
                    series_id = id_match.group(1)
                    text = series_link.text.strip()
                    
                    # Handle series order if present
                    name = text
                    order = None
                    if '#' in text:
                        name, number = text.split('#')
                        try:
                            order = float(number.strip())
                        except ValueError:
                            pass
                    
                    series.append({
                        'goodreads_id': series_id,
                        'name': name.strip(),
                        'order': order
                    })
        
        return series
    
    def _extract_genres(self, soup) -> list:
        """Extract genre information"""
        genres = []
        next_data = soup.find('script', id='__NEXT_DATA__')
        if next_data:
            try:
                data = json.loads(next_data.string)
                book_data = data['props']['pageProps']['apolloState']
                
                for value in book_data.values():
                    if isinstance(value, dict) and 'bookGenres' in value:
                        for genre_data in value['bookGenres']:
                            if isinstance(genre_data, dict) and 'genre' in genre_data:
                                genre = genre_data['genre']
                                if isinstance(genre, dict):
                                    genres.append({
                                        'name': genre.get('name', '')
                                    })
                        break
            except (json.JSONDecodeError, KeyError):
                pass
        return genres
    
    def _extract_cover_url(self, soup) -> str:
        """Extract book cover URL"""
        img = soup.find('img', {'class': 'ResponsiveImage'})
        if img and 'src' in img.attrs:
            return img['src']
            
        # Fallback to schema.org data
        schema = soup.find('script', {'type': 'application/ld+json'})
        if schema:
            try:
                data = json.loads(schema.string)
                return data.get('image')
            except json.JSONDecodeError:
                pass
        return None