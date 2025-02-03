from bs4 import BeautifulSoup
from pathlib import Path
import re
import json
from datetime import datetime
from ..utils.http import GoodreadsDownloader
from ..utils.image import download_book_cover
from .editions_scraper import EditionsScraper  # Import the editions scraper

class BookScraper:
    """Scrapes a book page from Goodreads, then selects the best edition based on criteria."""
    
    def __init__(self, scrape: bool = False):
        self.scrape = scrape
        self.downloader = GoodreadsDownloader(scrape)
        
    def scrape_book(self, book_id: str) -> dict:
        """
        Scrape the initial book page to get the work id, then use the editions page
        to choose a preferred edition based on criteria, and finally scrape that edition.
        """
        # Step 1: Scrape the initial book page using the given goodreads id.
        print(f"Scraping initial book page for: {book_id}")
        initial_url = self._get_book_url(book_id)
        if not self.downloader.download_url(initial_url):
            print(f"Failed to download book page for ID: {book_id}")
            return None
            
        initial_html = self._read_html(book_id)
        if not initial_html:
            return None
            
        initial_soup = BeautifulSoup(initial_html, 'html.parser')
        # Extract work_id from the initial page
        work_id = self._extract_work_id(initial_soup)
        if not work_id:
            print("Could not determine work id from the initial page.")
            return None
        
        # (Optional) You might want to extract some other minimal data from the initial page.
        
        # Step 2: Scrape the editions page using the work id.
        editions_scraper = EditionsScraper(scrape=self.scrape)
        editions = editions_scraper.scrape_editions(work_id)
        if not editions:
            print(f"Failed to scrape editions for work: {work_id}")
            return None
        
        # Step 3: Filter the editions based on your criteria.
        # For example, here we require:
        # - The edition must have a 'pages' value (non-null)
        # - The language is English
        # - The format is one of a set of accepted formats.
        accepted_formats = {'Paperback', 'Hardcover', 'Mass Market Paperback', 'Kindle Edition', 'ebook'}
        filtered_editions = [
            ed for ed in editions
            if ed.get('pages') and ed.get('published_date') and ed.get('language') == 'English'
            and ed.get('format') in accepted_formats
        ]
        
        if not filtered_editions:
            print("No editions found matching the criteria; using the initial edition.")
            chosen_edition_id = book_id
        else:
            # Choose the first edition from the filtered list.
            chosen = filtered_editions[0]
            chosen_edition_id = chosen['goodreads_id']
            print(f"Selected edition {chosen_edition_id} based on criteria.")
        
        # Step 4: Re-scrape the chosen edition's book page for detailed data.
        print(f"Scraping chosen edition page for: {chosen_edition_id}")
        chosen_url = self._get_book_url(chosen_edition_id)
        if not self.downloader.download_url(chosen_url):
            print(f"Failed to download chosen edition page for ID: {chosen_edition_id}")
            return None
        chosen_html = self._read_html(chosen_edition_id)
        if not chosen_html:
            return None
        
        chosen_soup = BeautifulSoup(chosen_html, 'html.parser')
        # Now extract detailed data from the chosen edition page.
        book_data = {
            'goodreads_id': chosen_edition_id,
            'title': self._extract_title(chosen_soup),
            'work_id': self._extract_work_id(chosen_soup),
            'description': self._extract_description(chosen_soup),
            'language': None,
            'pages': None,
            'isbn': None,
            'goodreads_rating': None,
            'goodreads_votes': None,
            'published_date': None,
            'published_state': None,
            'image_url': None,
            'source': 'scrape',
            'hidden': False
        }
        
        # Extract additional details from schema.org data or other elements.
        details = self._extract_book_details(chosen_soup)
        book_data.update({
            'language': details.get('language'),
            'pages': details.get('numberOfPages') or details.get('pages'),
            'isbn': details.get('isbn'),
            'goodreads_rating': details.get('rating'),
            'goodreads_votes': details.get('rating_count')
        })
        
        pub_info = self._extract_publication_info(chosen_soup)
        book_data['published_date'] = pub_info.get('date')
        book_data['published_state'] = pub_info.get('state')
        
        # Get authors, series, genres etc. if needed:
        book_data['authors'] = self._extract_authors(chosen_soup)
        book_data['series'] = self._extract_series(chosen_soup)
        book_data['genres'] = self._extract_genres(chosen_soup)
        
        # Get cover image
        cover_url = self._extract_cover_url(chosen_soup)
        if cover_url:
            local_path = download_book_cover(chosen_edition_id, cover_url)
            if local_path:
                book_data['image_url'] = local_path
                
        return book_data

    # Example helper methods:
    def _get_book_url(self, book_id: str) -> str:
        """Return the Goodreads URL for a book by its ID."""
        return f"https://www.goodreads.com/book/show/{book_id}"
    
    def _read_html(self, book_id: str) -> str:
        """Read the locally cached HTML file for a given book id."""
        path = Path('data/cache/book/show') / f"{book_id}.html"
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            print(f"Error reading HTML file for book {book_id}: {e}")
            return None

    def _extract_title(self, soup) -> str:
        """Extract the book title from the soup."""
        title_element = soup.find('h1', attrs={'data-testid': 'bookTitle'})
        if title_element:
            return title_element.get('aria-label', '').replace('Book title:', '').strip()
        return None
    
    def _extract_work_id(self, soup) -> str:
        """Extract the work id from the page. Implementation may vary."""
        # Example using the __NEXT_DATA__ script (adjust as needed)
        next_data = soup.find('script', id='__NEXT_DATA__')
        if next_data:
            try:
                data = json.loads(next_data.string)
                for key, value in data.get('props', {}).get('pageProps', {}).get('apolloState', {}).items():
                    if isinstance(value, dict) and 'editions' in value:
                        if value['editions'].get('webUrl'):
                            # Assuming the work id is in the URL.
                            return value['editions']['webUrl'].split('/')[-1].split('-')[0]
            except Exception as e:
                print(f"Error extracting work id: {e}")
        return None

    def _extract_description(self, soup) -> str:
        """Extract the book description."""
        next_data = soup.find('script', id='__NEXT_DATA__')
        if next_data:
            try:
                data = json.loads(next_data.string)
                apollo_state = data.get('props', {}).get('pageProps', {}).get('apolloState', {})
                # Use your logic to extract the description from apollo_state.
                for key, value in apollo_state.items():
                    if isinstance(value, dict) and 'description' in value:
                        return value.get('description')
            except Exception as e:
                print(f"Error extracting description: {e}")
        return None

    def _extract_book_details(self, soup) -> dict:
        """Extract details from the schema.org JSON-LD if available."""
        schema = soup.find('script', {'type': 'application/ld+json'})
        if schema:
            try:
                data = json.loads(schema.string)
                return {
                    'language': data.get('inLanguage'),
                    'numberOfPages': data.get('numberOfPages'),
                    'isbn': data.get('isbn'),
                    'rating': data.get('aggregateRating', {}).get('ratingValue'),
                    'rating_count': data.get('aggregateRating', {}).get('ratingCount')
                }
            except Exception as e:
                print(f"Error extracting book details: {e}")
        return {}
    
    def _extract_publication_info(self, soup) -> dict:
        """Extract publication info and convert the date to ISO 8601 format."""
        pub_element = soup.find('p', attrs={'data-testid': 'publicationInfo'})
        if pub_element:
            text = pub_element.get_text(strip=True)
            result = {'date': None, 'state': None}
            if text.startswith('Expected publication'):
                result['state'] = 'upcoming'
                raw_date = text.replace('Expected publication', '').strip()
            elif text.startswith('First published'):
                result['state'] = 'published'
                raw_date = text.replace('First published', '').strip()
            elif text.startswith('Published'):
                result['state'] = 'published'
                raw_date = text.replace('Published', '').strip()
            else:
                raw_date = text
            try:
                dt = datetime.strptime(raw_date, "%B %d, %Y")
                result['date'] = dt.isoformat(timespec='microseconds')
            except Exception as e:
                print(f"Error parsing publication date '{raw_date}': {e}")
                result['date'] = raw_date
            return result
        return {}

    def _extract_cover_url(self, soup) -> str:
        """Extract the cover image URL from the page."""
        img = soup.find('img', {'class': 'ResponsiveImage'})
        if img and 'src' in img.attrs:
            return img['src']
        schema = soup.find('script', {'type': 'application/ld+json'})
        if schema:
            try:
                data = json.loads(schema.string)
                return data.get('image')
            except Exception as e:
                print(f"Error extracting cover URL from schema: {e}")
        return None

    def _extract_authors(self, soup) -> list:
        authors = []
        author_links = soup.find_all('a', class_='ContributorLink')
        for link in author_links:
            name_span = link.find('span', class_='ContributorLink__name')
            if not name_span:
                continue

            goodreads_id = None
            if 'href' in link.attrs:
                match = re.search(r'/author/show/(\d+)', link['href'])
                if match:
                    goodreads_id = match.group(1)

            # Safely get the role text if available.
            role_el = link.find('span', class_='ContributorLink__role')
            if role_el is not None:
                role = role_el.text.strip('()').strip()
            else:
                role = 'Author'
            
            authors.append({
                'goodreads_id': goodreads_id,
                'name': name_span.text.strip(),
                'role': role
            })
        return authors


    def _extract_series(self, soup) -> list:
        """Extract series information from the page. Implement as needed."""
        series = []
        series_element = soup.find('h3', class_='Text__title3', 
                                     attrs={'aria-label': lambda x: x and 'series' in x.lower()})
        if series_element:
            series_link = series_element.find('a')
            if series_link:
                match = re.search(r'/series/(\d+)', series_link['href'])
                if match:
                    series_id = match.group(1)
                    # Optional: extract order if present
                    order = None
                    text = series_link.get_text(strip=True)
                    if '#' in text:
                        parts = text.split('#')
                        try:
                            order = float(parts[1].strip())
                        except:
                            pass
                    series.append({
                        'goodreads_id': series_id,
                        'name': series_link.get_text(strip=True),
                        'order': order
                    })
        return series

    def _extract_genres(self, soup) -> list:
        """Extract genres from the page. Implement as needed."""
        genres = []
        next_data = soup.find('script', id='__NEXT_DATA__')
        if next_data:
            try:
                data = json.loads(next_data.string)
                apollo_state = data.get('props', {}).get('pageProps', {}).get('apolloState', {})
                for value in apollo_state.values():
                    if isinstance(value, dict) and 'bookGenres' in value:
                        for genre_item in value['bookGenres']:
                            if isinstance(genre_item, dict) and 'genre' in genre_item:
                                genre = genre_item['genre']
                                if isinstance(genre, dict):
                                    genres.append({'name': genre.get('name', '')})
                        break
            except Exception as e:
                print(f"Error extracting genres: {e}")
        return genres
