import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any
import sys
from pathlib import Path

# Add backend to path
sys.path.append(str(Path(__file__).parent.parent.parent))

from backend.utils.data_transformer import transform_book_data, format_tables

def fetch_calibre_books(calibre_db_path: str, limit: int = None) -> List[Dict[str, Any]]:
    """Fetch minimal book data from Calibre database"""
    try:
        with sqlite3.connect(calibre_db_path) as conn:
            query = """
                SELECT 
                    books.id AS calibre_id,
                    books.title,
                    gr.val AS goodreads_id,
                    isbn.val AS isbn,
                    warren_read.value AS warren_last_read,
                    ruth_read.value AS ruth_last_read
                FROM books
                LEFT JOIN identifiers gr 
                    ON gr.book = books.id 
                    AND gr.type = 'goodreads'
                LEFT JOIN identifiers isbn
                    ON isbn.book = books.id 
                    AND isbn.type = 'isbn'
                LEFT JOIN custom_column_6 warren_read
                    ON warren_read.book = books.id
                LEFT JOIN custom_column_14 ruth_read
                    ON ruth_read.book = books.id
                WHERE gr.val IS NOT NULL
            """
            
            if limit:
                query += f" LIMIT {limit}"
                
            cursor = conn.execute(query)
            results = [{
                'calibre_id': row[0],
                'title': row[1],
                'goodreads_id': row[2],
                'isbn': row[3],
                'warren_last_read': row[4],
                'ruth_last_read': row[5]
            } for row in cursor.fetchall()]
            
            return results
            
    except sqlite3.Error as e:
        print(f"Error fetching books from Calibre: {e}")
        return []

def prepare_book_data(calibre_book: Dict[str, Any]) -> Dict[str, Any]:
    """Prepare minimal Calibre book data to match the expected transformer structure"""
    return {
        'id': calibre_book['goodreads_id'],
        'title': calibre_book['title'],
        'calibre_id': calibre_book['calibre_id'],
        'warren_last_read': calibre_book['warren_last_read'],
        'ruth_last_read': calibre_book['ruth_last_read'],
        'source': 'library',
        'authors': [],
        'publication': {
            'date': None,
            'status': 'unknown'
        },
        'details': {
            'language': None,
            'pages': None,
            'isbn': None,
            'awards': [],
            'rating': None,
            'rating_count': None
        },
        'description': None,
        'genres': [],
        'additional_series': []
    }
    
def format_timestamp(dt: datetime) -> str:
    """Format datetime to ISO format with microsecond precision"""
    if isinstance(dt, str):
        dt = datetime.strptime(dt, '%Y-%m-%d %H:%M:%S%z')
    return dt.astimezone().isoformat(timespec='microseconds')

def process_calibre_books(calibre_db_path: str = "C:/Users/warre/Calibre Library/metadata.db", limit: int = None) -> Dict[str, List[Dict]]:
    """Process books from Calibre database and return transformed data"""
    # Fetch books from Calibre
    calibre_books = fetch_calibre_books(calibre_db_path, limit)
    now = format_timestamp(datetime.now())
    
    if not calibre_books:
        return {'book': [], 'library': [], 'user': [], 'book_user': []}
    
    # Initialize all tables
    all_tables = {
        'book': [],
        'library': [],
        'user': [
            {
                'id': 1,
                'name': 'Warren',
                'created_at': now,
                'updated_at': now
            },
            {
                'id': 2,
                'name': 'Ruth',
                'created_at': now,
                'updated_at': now
            }
        ],
        'book_user': []
    }
    
    for book in calibre_books:
        if book['goodreads_id']:
            # Prepare and transform book data
            book_data = prepare_book_data(book)
            transformed = transform_book_data(book_data)
            
            # Add transformed book data
            all_tables['book'].extend(transformed['book'])
            
            # Create library entry
            library_entry = {
                'title': book['title'],
                'calibre_id': book['calibre_id'],
                'goodreads_id': book['goodreads_id'],
                'isbn': book['isbn'],
                'created_at': now,
                'updated_at': now,
                'last_synced_at': now
            }
            all_tables['library'].append(library_entry)
            
            # Add reading records if dates exist
            if book['warren_last_read']:
                finished_at = format_timestamp(book['warren_last_read'])
                all_tables['book_user'].append({
                    'book_id': book['goodreads_id'],
                    'user_id': 1,  # Warren's ID
                    'status': 'read',
                    'source': 'calibre',
                    'finished_at': finished_at,
                    'created_at': now,
                    'updated_at': now
                })
            
            if book['ruth_last_read']:
                finished_at = format_timestamp(book['ruth_last_read'])
                all_tables['book_user'].append({
                    'book_id': book['goodreads_id'],
                    'user_id': 2,  # Ruth's ID
                    'status': 'read',
                    'source': 'calibre',
                    'finished_at': finished_at,
                    'created_at': now,
                    'updated_at': now
                })
    
    return all_tables

if __name__ == "__main__":
    CALIBRE_DB_PATH = "C:/Users/warre/Calibre Library/metadata.db"
    tables = process_calibre_books(CALIBRE_DB_PATH)