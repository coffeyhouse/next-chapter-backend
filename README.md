# Calibre Companion CLI

A powerful command-line interface for managing your Calibre library and Goodreads integration.

## Installation

```bash
# TODO: Add installation instructions
```

## Command Overview

The CLI provides several command groups for managing different aspects of your library:

### Library Management

```bash
cli library [COMMAND]
```

Commands:
- `empty-db`: Empty the database of all records (use with caution)
  ```bash
  cli library empty-db [--force]
  ```
- `sync-reading`: Sync reading progress from Calibre database
  ```bash
  cli library sync-reading [--calibre-path PATH] [--dry-run]
  ```
- `reset-sync`: Reset the sync date for all records in a table
  ```bash
  cli library reset-sync [table] [--force] [--verbose]
  ```
  Valid tables: book, author, series, library, book-similar

### Book Management

```bash
cli book [COMMAND]
```

Commands:
- `create`: Create a book from Goodreads ID
  ```bash
  cli book create GOODREADS_ID [--scrape/--no-scrape]
  ```
- `check-exclusions`: Check existing books against exclusion rules
  ```bash
  cli book check-exclusions [--limit N] [--verbose] [--work-id ID]
  ```

### Author Management

```bash
cli author [COMMAND]
```

Manage author information and synchronization with Goodreads.

### Series Management

```bash
cli series [COMMAND]
```

Manage book series information and synchronization.

### Similar Books

```bash
cli similar [COMMAND]
```

Commands:
- `sync-sa`: Sync similar books relationships
  ```bash
  cli similar sync-sa [--limit N] [--source SOURCE] [--goodreads-id ID] [--scrape] [--verbose] [--retry]
  ```

### List Management

```bash
cli list [COMMAND]
```

Manage reading lists and book collections.

### System Monitoring

```bash
cli monitor [COMMAND]
```

Commands:
- `cpu`: Monitor CPU usage and temperature
  ```bash
  cli monitor cpu [--interval SECONDS] [--count N]
  ```

### Development Tools

```bash
cli dev [COMMAND]
```

Commands:
- `structure`: Output directory structure to file
  ```bash
  cli dev structure [--output FILE]
  ```
- `combine`: Combine non-empty files within each subfolder
  ```bash
  cli dev combine [--output-dir DIR]
  ```

## Examples

1. Create a new book from Goodreads:
   ```bash
   cli book create 54493401  # Create "Project Hail Mary"
   cli book create 7235533 --scrape  # Create "The Way of Kings" with fresh data
   ```

2. Sync reading progress with Calibre:
   ```bash
   cli library sync-reading  # Use default Calibre path
   cli library sync-reading --calibre-path "path/to/metadata.db" --dry-run
   ```

3. Monitor system performance:
   ```bash
   cli monitor cpu --interval 5 --count 10  # Take 10 measurements, 5 seconds apart
   ```

4. Reset sync status:
   ```bash
   cli library reset-sync series  # Reset series sync dates
   cli library reset-sync book --force  # Reset book sync dates without confirmation
   ```

## Notes

- Always use `--dry-run` when available to preview changes before applying them
- Use `--verbose` flag for detailed progress information
- Be cautious with destructive commands (like `empty-db`); they may require confirmation
- Most sync commands support `--scrape` flag to fetch fresh data instead of using cache

## Contributing

[Add contribution guidelines here]

## License

[Add license information here] 