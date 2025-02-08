# tests/test_sa/README.md
# SQLAlchemy Integration Tests

These tests verify that SQLAlchemy can correctly:
1. Connect to the existing database
2. Map the existing schema to SQLAlchemy models
3. Perform queries using the repository pattern

## Running Tests

From the project root:
```bash
pytest tests/test_sa
```

To see SQL queries:
```bash
pytest tests/test_sa -s --log-cli-level=DEBUG
```

## Test Structure

- `conftest.py`: Test configuration and fixtures
- `test_models.py`: Tests for SQLAlchemy model mappings
- `test_repositories/`: Tests for repository implementations