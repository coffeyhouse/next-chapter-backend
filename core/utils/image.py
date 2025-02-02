import os
from pathlib import Path
import requests
import re
import json
from urllib.parse import urlparse
import logging
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

class ImageDownloader:
    def __init__(self, base_dir: str = 'data/images'):
        """Initialize the image downloader with a base directory"""
        self.base_dir = Path(base_dir)
        
    def _create_directory(self, image_type: str) -> Path:
        """Create and return the appropriate directory for the image type"""
        directory = self.base_dir / image_type
        directory.mkdir(parents=True, exist_ok=True)
        return directory
        
    def _get_extension(self, url: str, content_type: str) -> str:
        """Determine the file extension from URL or content type"""
        # Try to get extension from URL first
        url_path = urlparse(url).path
        ext = Path(url_path).suffix.lower()
        
        if ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp']:
            return ext
            
        # Fall back to content type
        content_type_map = {
            'image/jpeg': '.jpg',
            'image/png': '.png',
            'image/gif': '.gif',
            'image/webp': '.webp'
        }
        
        return content_type_map.get(content_type, '.jpg')  # Default to jpg
        
    def _clean_image_url(self, url: str) -> str:
        """Clean up the image URL"""
        # Convert HTTP to HTTPS
        if url.startswith('http://'):
            url = 'https://' + url[7:]
            
        # Remove compression parameters from Goodreads URLs
        if 'goodreads.com' in url:
            url = re.sub(r'_\w+\d+_', '_', url)  # Remove size indicators like _SX318_
            url = re.sub(r'compressed\.', '', url)  # Remove "compressed." prefix
            
        return url
        
    def _validate_image(self, content: bytes, content_type: str) -> bool:
        """Validate that the content is actually an image"""
        # Check minimum size (1KB)
        if len(content) < 1024:
            return False
            
        # Check content type
        if not content_type.startswith('image/'):
            return False
            
        # Check for common image headers
        image_headers = {
            b'\xff\xd8\xff',  # JPEG
            b'\x89PNG\r\n',   # PNG
            b'GIF87a',        # GIF
            b'GIF89a',        # GIF
            b'RIFF'           # WEBP
        }
        
        return any(content.startswith(header) for header in image_headers)
        
    def download_image(
        self, 
        url: str, 
        image_type: str, 
        identifier: str,
        force_update: bool = False
    ) -> Tuple[bool, Optional[str]]:
        """
        Download an image and save it to the appropriate directory
        
        Args:
            url: The URL of the image to download
            image_type: Type of image (e.g., 'book', 'author')
            identifier: Unique identifier for the image (e.g., book_id or author_id)
            force_update: If True, download even if file exists
            
        Returns:
            Tuple of (success: bool, local_path: Optional[str])
        """
        if not url:
            return False, None
            
        try:
            url = self._clean_image_url(url)
            save_dir = self._create_directory(image_type)
            
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            
            content_type = response.headers.get('content-type', 'image/jpeg')
            if not self._validate_image(response.content, content_type):
                return False, None
                
            extension = self._get_extension(url, content_type)
            file_path = save_dir / f"{identifier}{extension}"
            
            if file_path.exists() and not force_update:
                return True, str(file_path)
            
            with open(file_path, 'wb') as f:
                f.write(response.content)
                
            return True, str(file_path)
            
        except requests.RequestException:
            return False, None
        except Exception:
            return False, None

def download_book_cover(book_id: str, cover_url: str) -> Optional[str]:
    """Download a book cover image"""
    downloader = ImageDownloader()
    success, path = downloader.download_image(
        url=cover_url,
        image_type='book',
        identifier=book_id
    )
    return path if success else None

def download_author_photo(author_id: str, photo_url: str) -> Optional[str]:
    """Download an author photo"""
    downloader = ImageDownloader()
    success, path = downloader.download_image(
        url=photo_url,
        image_type='author',
        identifier=author_id
    )
    return path if success else None

# Integration with book.py
def extract_book_cover_url(soup):
    """Extract the book cover image URL from a book page"""
    # Try class ResponsiveImage first
    img = soup.find('img', {'class': 'ResponsiveImage'})
    if img and 'src' in img.attrs:
        return img['src']
        
    # Try schema.org metadata as fallback
    schema_script = soup.find('script', {'type': 'application/ld+json'})
    if schema_script:
        try:
            data = json.loads(schema_script.string)
            if 'image' in data:
                return data['image']
        except json.JSONDecodeError:
            pass
            
    return None

# Example usage:
def download_book_cover(book_id: str, cover_url: str) -> Optional[str]:
    """Download a book cover image"""
    downloader = ImageDownloader()
    success, path = downloader.download_image(
        url=cover_url,
        image_type='book',
        identifier=book_id
    )
    return path if success else None

def extract_author_photo_url(soup):
    """Extract the author photo URL from an author page"""
    # Look for author photo in img tag
    img = soup.find('img', {'alt': lambda x: x and 'author' in x.lower()})
    if img and 'src' in img.attrs:
        return img['src']
    
    return None

def download_author_photo(author_id: str, photo_url: str) -> Optional[str]:
    """Download an author photo"""
    downloader = ImageDownloader()
    success, path = downloader.download_image(
        url=photo_url,
        image_type='author',
        identifier=author_id
    )
    return path if success else None