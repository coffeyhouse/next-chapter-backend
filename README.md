# Calibre Companion

A command-line tool to enhance your Calibre library with Goodreads data. This tool helps you manage your books by:
- Importing books from your Calibre library
- Syncing with Goodreads to get additional metadata
- Managing book series and authors
- Tracking reading progress and library statistics

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd calibre-companion
```

2. Install the package in development mode:
```bash
pip install -e .
```

## Usage

The tool provides several commands for managing your book collection:

### Library Management

Import books from Calibre:
```bash
calibre-companion library import-calibre-sa --calibre-path "path/to/metadata.db"
# Options:
#   --limit INTEGER    Limit number of books to import
#   --scrape          Scrape fresh data from Goodreads
#   --verbose         Show detailed progress
```

View library statistics:
```bash
calibre-companion library stats
```

### Series Management

Sync series data:
```bash
# Sync all unsynced series
calibre-companion series sync-sa --days 30

# Sync specific series by ID
calibre-companion series sync-sa --goodreads-id 45175

# Sync series with books from library
calibre-companion series sync-sa --source library
```

### Author Management

Sync author data:
```bash
# Sync all unsynced authors
calibre-companion author sync-sa --days 30

# Sync specific author by ID
calibre-companion author sync-sa --goodreads-id 18541

# Sync authors with books from library
calibre-companion author sync-sa --source library
```

### Book Management

Create individual books:
```bash
calibre-companion book create <goodreads-id>
```

### Common Options

Most commands support these options:
- `--verbose`: Show detailed progress
- `--scrape`: Use fresh data instead of cache
- `--limit`: Limit number of items to process
- `--source`: Filter by source (library, series, author)

## Data Sources

The tool manages data from multiple sources:
- **library**: Books imported from Calibre
- **series**: Books added via series sync
- **author**: Books added via author sync
- **goodreads**: Books added directly from Goodreads

## Database Structure

The tool uses SQLAlchemy to manage relationships between:
- Books
- Authors
- Series
- Genres
- Library entries

## Development

### Project Structure
```
calibre_companion/
├── cli/               # Command-line interface
│   ├── commands/     # Individual command modules
│   └── utils.py      # Shared CLI utilities
├── core/             # Core functionality
│   ├── resolvers/    # Data resolution logic
│   ├── scrapers/     # Web scraping modules
│   ├── sa/           # SQLAlchemy models and repositories
│   └── utils/        # Utility functions
└── tests/            # Test suite
```

### Running Tests
```bash
pytest
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## License

[Your chosen license] 