# EXASPERATION API

This directory contains the FastAPI implementation for the EXASPERATION backend API. The API provides endpoints for querying the Exabeam documentation, retrieving metadata options, and collecting user feedback in compliance with the API contract defined in `documentation/FRONTEND_API_CONTRACT.md`.

## API Structure

- **`app.py`**: Main FastAPI application with middleware and exception handlers
- **`auth.py`**: Authentication middleware and utilities
- **`models.py`**: Pydantic models for request and response validation
- **`routes.py`**: API route handlers
- **`service.py`**: Service layer that interacts with the RAG backend
- **`main.py`**: Entry point for running the API server
- **`test_client.py`**: Sample client for testing the API

## Architecture

The API follows a layered architecture:

1. **Presentation Layer**: Request handling, response formatting, error management
   - Implemented in `routes.py` as FastAPI route handlers
   - Uses Pydantic models in `models.py` for validation

2. **Service Layer**: Business logic coordination, query processing
   - Implemented in `service.py` as the `ExasperationService` class
   - Handles interaction with RAG components and formatting responses

3. **Data Access Layer**: Integration with existing backend systems
   - Connects to ChromaDB via the Vector Store module
   - Uses the Query Engine for retrieval and response generation

4. **Security Layer**: Authentication, permissions, rate limiting
   - Implemented in `auth.py` as middleware and utility functions
   - Handles API key validation, request throttling, and permission checking

## Running the API

```bash
# Create and activate a dedicated API virtual environment
python3 -m venv api_venv
source api_venv/bin/activate

# Install dependencies
pip install -r frontend.requirements.txt

# Run the API server
python -m frontend.api.main

# Or with specific host and port
python -m frontend.api.main --host 127.0.0.1 --port 8080
```

The API server will run on port 8080 by default (configurable via environment variables).

## Configuration

The API uses the following environment variables:

- `APP_PORT`: Port for the API server (default: 8080)
- `DEBUG_MODE`: Enable debug mode (default: False)
- `LOG_LEVEL`: Logging level (default: INFO)
- `API_RATE_LIMIT`: Requests per minute limit (default: 60)
- `API_CONCURRENT_LIMIT`: Concurrent requests limit (default: 5)
- `EXASPERATION_API_KEY`: Test API key for development

These can be set in the `.env` file or passed through the environment.

## API Endpoints

The API implements the following endpoints:

### 1. Search Query

```
POST /v1/search
```

Submit a natural language query to retrieve relevant information from Exabeam documentation.

**Example Request:**
```json
{
  "query": "How does the password reset detection rule work?",
  "filters": {
    "document_types": ["use_case", "parser", "rule"],
    "vendors": ["microsoft", "okta"]
  },
  "options": {
    "max_results": 10,
    "rerank": true,
    "threshold": 0.7
  }
}
```

**Example Response:**
```json
{
  "request_id": "req_1234567890",
  "query": "How does the password reset detection rule work?",
  "answer": "Password reset detection in Exabeam works by monitoring...",
  "sources": [
    {
      "id": "doc_123",
      "title": "Password Reset Detection",
      "url": "https://docs.exabeam.com/...",
      "chunk_id": "chunk_456",
      "content": "Password reset events are logged with EventID 4724...",
      "relevance_score": 0.92,
      "metadata": {
        "document_type": "use_case",
        "vendor": "microsoft",
        "product": "active_directory"
      }
    }
  ],
  "suggested_queries": [
    "How do I configure password reset alerting?",
    "What events are generated during a password reset?"
  ],
  "metadata": {
    "processing_time_ms": 235,
    "filter_count": 2,
    "total_matches": 15,
    "threshold_applied": 0.7
  }
}
```

### 2. Query Suggestions

```
GET /v1/suggestions?partial_query={query}&limit={limit}
```

Get autocomplete suggestions for a partial query.

**Example Response:**
```json
{
  "suggestions": [
    "How do I configure SAML authentication",
    "How do I set up the Okta integration",
    "How does lateral movement detection work"
  ],
  "metadata": {
    "processing_time_ms": 45
  }
}
```

### 3. Feedback

```
POST /v1/feedback
```

Submit feedback about a search result.

**Example Request:**
```json
{
  "request_id": "req_1234567890",
  "rating": "positive",
  "comments": "This answer was very helpful and accurate."
}
```

**Example Response:**
```json
{
  "status": "success",
  "feedback_id": "fb_987654321",
  "message": "Thank you for your feedback!"
}
```

### 4. Metadata Options

```
GET /v1/metadata/options
```

Retrieve available metadata options for filtering.

**Example Response:**
```json
{
  "document_types": ["use_case", "parser", "rule"],
  "vendors": ["microsoft", "cisco", "okta"],
  "products": {
    "microsoft": ["active_directory", "azure_ad"]
  },
  "use_cases": ["account_takeover", "lateral_movement"],
  "date_range": {
    "oldest": "2022-01-15",
    "newest": "2025-03-27"
  }
}
```

### 5. Session Status

```
GET /v1/session/status
```

Check the status of the current session.

**Example Response:**
```json
{
  "authenticated": true,
  "user_id": "usr_12345",
  "session_expires_at": "2025-03-28T08:30:00Z",
  "rate_limit": {
    "limit": 60,
    "remaining": 58,
    "reset_at": "2025-03-27T08:06:00Z"
  },
  "account_tier": "standard",
  "features_enabled": [
    "advanced_filtering",
    "query_history",
    "feedback",
    "suggestions"
  ]
}
```

### 6. Test Endpoint

```
GET /v1/test
```

Simple test endpoint for verifying API connectivity.

## Authentication

All endpoints require authentication using an API key provided in the Authorization header:

```
Authorization: Bearer {api_key}
```

The API implements:
- Rate limiting (60 requests per minute)
- Concurrent request limiting (5 concurrent requests)
- Permission-based access control
- Session tracking

## Error Handling

Error responses follow this format:

```json
{
  "error": {
    "code": "error_code",
    "message": "Human-readable error message",
    "details": {
      "parameter": "query",
      "reason": "empty_value"
    }
  },
  "request_id": "req_1234567890"
}
```

## Testing

The API includes a test client for validating endpoint functionality:

```bash
# Run the test client
python frontend/api/test_client.py --endpoint search

# Test all endpoints
python frontend/api/test_client.py --endpoint all
```

Or use the test shell script:

```bash
./test_api.sh
```

## Documentation

API documentation is available at:

- Swagger UI: `/v1/docs`
- ReDoc: `/v1/redoc`
- OpenAPI JSON: `/v1/openapi.json`

## Implementation Notes

1. The API handles connection to ChromaDB for vector storage
2. It falls back to mock services when components are unavailable
3. It uses a MockLLM when Claude is not available
4. It handles input validation and error formatting
5. Request tracking allows for better analytics and debugging