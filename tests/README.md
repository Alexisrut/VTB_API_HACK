# Backend Tests

This directory contains tests for the backend API.

## Setup

Install test dependencies:

```bash
pip install -r requirements.txt
```

## Running Tests

Run all tests:

```bash
pytest
```

Run with verbose output:

```bash
pytest -v
```

Run specific test file:

```bash
pytest tests/test_auth.py
```

Run specific test:

```bash
pytest tests/test_auth.py::TestRegistration::test_register_success
```

Run with coverage:

```bash
pytest --cov=app --cov-report=html
```

## Test Structure

- `conftest.py` - Pytest fixtures and configuration
- `test_auth.py` - Authentication endpoint tests (registration, login, token refresh)

## Test Database

Tests use an in-memory SQLite database, so no external database setup is required. Each test gets a fresh database session.

## Writing New Tests

1. Create a new test file: `test_<module>.py`
2. Import necessary fixtures from `conftest.py`
3. Use `@pytest.mark.asyncio` for async tests
4. Use the `client` fixture for API requests
5. Use the `db_session` fixture for database operations

Example:

```python
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_example(client: AsyncClient):
    response = await client.get("/health")
    assert response.status_code == 200
```

