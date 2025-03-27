# EXASPERATION Test Scripts

This directory contains scripts for testing EXASPERATION components.

## Available Scripts

- `test_api.sh`: Tests the API endpoints
- `test_api_directly.py`: Tests the API directly (bypassing HTTP)
- `test_query.py`: Tests the query engine with sample questions
- `test_batch_ingestion.py`: Tests batch document ingestion
- `test_chroma_persistence.py`: Tests ChromaDB persistence
- `test_create_collection.py`: Tests collection creation
- `test_direct_ingestion.py`: Tests direct document ingestion
- `test_initialize_db.py`: Tests database initialization
- `test_metadata.py`: Tests metadata extraction and filtering

## Usage

Python scripts should be run with Python from the project root directory:

```bash
# Test the query engine
python scripts/tests/test_query.py "How does the password reset detection rule work?"

# Test the API
./scripts/tests/test_api.sh
```

## Prerequisites

Before running these tests, ensure that:

1. The appropriate virtual environment is activated
2. Required services are running (e.g., ChromaDB for database tests)
3. Environment variables are properly set

## Environment Selection

Depending on the test, you should use the appropriate virtual environment:

- For database tests: `chromadb_venv`
- For API tests: `api_venv`
- For frontend tests: `frontend_venv`
