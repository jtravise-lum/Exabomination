# EXASPERATION Frontend-Backend API Contract

This document defines the API contract between the EXASPERATION frontend and backend systems, outlining endpoints, request/response formats, error handling, and authentication requirements.

## Base URL

```
https://api.exasperation.example.com/v1
```

## Authentication

All API endpoints require authentication using an API key provided in the request header:

```
Authorization: Bearer {api_key}
```

Rate limiting is enforced at 60 requests per minute per API key.

## Endpoints

### 1. Search Query

Submit a natural language query to retrieve relevant information from Exabeam documentation.

**Endpoint:** `POST /search`

**Request:**
```json
{
  "query": "How does the password reset detection rule work?",
  "filters": {
    "document_types": ["use_case", "parser", "rule"],
    "vendors": ["microsoft", "okta"],
    "products": ["active_directory", "azure_ad"],
    "created_after": "2024-01-01",
    "created_before": "2025-03-27"
  },
  "options": {
    "max_results": 10,
    "include_metadata": true,
    "rerank": true,
    "threshold": 0.7
  }
}
```

**Response:**
```json
{
  "request_id": "req_1234567890",
  "query": "How does the password reset detection rule work?",
  "answer": "The password reset detection rule works by monitoring authentication events...",
  "sources": [
    {
      "id": "doc_123",
      "title": "Password Reset Detection Use Case",
      "url": "https://docs.exabeam.com/use-cases/password-reset-detection",
      "chunk_id": "chunk_456",
      "content": "Password reset detection monitors authentication events for password changes...",
      "relevance_score": 0.92,
      "metadata": {
        "document_type": "use_case",
        "vendor": "microsoft",
        "product": "active_directory",
        "created_at": "2024-02-15",
        "updated_at": "2024-03-10"
      }
    },
    {
      "id": "doc_124",
      "title": "Active Directory Password Events",
      "url": "https://docs.exabeam.com/data-sources/active-directory/password-events",
      "chunk_id": "chunk_789",
      "content": "Active Directory password events are logged with event ID 4724...",
      "relevance_score": 0.87,
      "metadata": {
        "document_type": "parser",
        "vendor": "microsoft",
        "product": "active_directory",
        "created_at": "2023-11-05",
        "updated_at": "2024-01-22"
      }
    }
  ],
  "suggested_queries": [
    "How do I configure password reset alerting?",
    "What events are generated during a password reset?",
    "How does password reset differ from password change?"
  ],
  "metadata": {
    "processing_time_ms": 235,
    "filter_count": 5,
    "total_matches": 27,
    "threshold_applied": 0.7
  }
}
```

### 2. Query Suggestions

Get autocomplete suggestions for a partial query.

**Endpoint:** `GET /suggestions`

**Request Parameters:**
- `partial_query` (string, required): The partial query text
- `limit` (integer, optional): Maximum number of suggestions to return (default: 5)

**Response:**
```json
{
  "suggestions": [
    "How do I configure SAML authentication",
    "How do I set up the Okta integration",
    "How does lateral movement detection work",
    "How do I troubleshoot data lake connectivity issues",
    "How do I create a custom parser"
  ],
  "metadata": {
    "processing_time_ms": 45
  }
}
```

### 3. Feedback

Submit feedback about a search result.

**Endpoint:** `POST /feedback`

**Request:**
```json
{
  "request_id": "req_1234567890",
  "rating": "positive",  // "positive", "negative"
  "comments": "This answer was very helpful and accurate.",
  "selected_sources": ["doc_123", "doc_124"],
  "user_query_reformulation": "How does password reset detection work in Active Directory?"
}
```

**Response:**
```json
{
  "status": "success",
  "feedback_id": "fb_987654321",
  "message": "Thank you for your feedback!"
}
```

### 4. Metadata Options

Retrieve available metadata options for filtering.

**Endpoint:** `GET /metadata/options`

**Response:**
```json
{
  "document_types": [
    "use_case",
    "parser",
    "rule",
    "data_source",
    "overview",
    "tutorial"
  ],
  "vendors": [
    "microsoft",
    "cisco",
    "okta",
    "palo_alto",
    "aws"
  ],
  "products": {
    "microsoft": [
      "active_directory",
      "azure_ad",
      "exchange_online",
      "windows"
    ],
    "cisco": [
      "asa",
      "firepower",
      "ise",
      "meraki"
    ],
    "okta": [
      "identity_cloud"
    ]
  },
  "use_cases": [
    "account_takeover",
    "data_exfiltration",
    "lateral_movement",
    "privilege_escalation"
  ],
  "date_range": {
    "oldest": "2022-01-15",
    "newest": "2025-03-27"
  }
}
```

### 5. Session Status

Check the status of the current session.

**Endpoint:** `GET /session/status`

**Response:**
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

## Error Handling

All endpoints return standard HTTP status codes:

- `200 OK`: Request succeeded
- `400 Bad Request`: Invalid request parameters
- `401 Unauthorized`: Missing or invalid API key
- `403 Forbidden`: Insufficient permissions
- `404 Not Found`: Requested resource not found
- `429 Too Many Requests`: Rate limit exceeded
- `500 Internal Server Error`: Server error

Error responses follow this format:

```json
{
  "error": {
    "code": "invalid_query",
    "message": "Query parameter cannot be empty",
    "details": {
      "parameter": "query",
      "reason": "empty_value"
    }
  },
  "request_id": "req_1234567890"
}
```

## Pagination

For endpoints that return multiple items, pagination is supported using:

- `limit`: Number of items per page (default: 10, max: 100)
- `offset`: Starting position (default: 0)

Paginated responses include:

```json
{
  "items": [...],
  "pagination": {
    "limit": 10,
    "offset": 0,
    "total": 42,
    "next_offset": 10,
    "has_more": true
  }
}
```

## Versioning

The API is versioned in the URL path (e.g., `/v1/search`). 

Changes to the API will be communicated:
- Major version changes (e.g., v1 to v2) for breaking changes
- Minor updates within the same version for non-breaking additions

## Implementation Notes

1. All timestamps are in ISO 8601 format (UTC)
2. Request IDs should be included in client logs for troubleshooting
3. The frontend should implement exponential backoff for retries on 429 or 5xx errors
4. JSON responses may include additional fields not documented here for future compatibility