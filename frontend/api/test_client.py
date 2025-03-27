#!/usr/bin/env python3
"""Test client for EXASPERATION API.

This script demonstrates how to use the EXASPERATION API endpoints.
"""

import os
import sys
import time
import json
import argparse
import requests
from typing import Dict, Any, Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Default API URL from environment or use localhost:8080
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8080/v1")
API_KEY = os.getenv("EXASPERATION_API_KEY", "test_key_1234567890")


def print_response(response: requests.Response, title: str):
    """Print formatted API response.
    
    Args:
        response: HTTP response
        title: Title for the response
    """
    print(f"\n===== {title} =====")
    print(f"Status: {response.status_code}")
    print("Headers:")
    for header in ["Content-Type", "X-Request-ID", "X-Process-Time", 
                  "X-Rate-Limit-Limit", "X-Rate-Limit-Remaining", "X-Rate-Limit-Reset"]:
        if header in response.headers:
            print(f"  {header}: {response.headers[header]}")
    
    print("\nResponse:")
    if response.status_code == 200:
        # Format JSON response
        formatted_json = json.dumps(response.json(), indent=2)
        print(formatted_json)
    else:
        # Print error response
        print(response.text)
    
    print(f"\nElapsed: {response.elapsed.total_seconds():.3f} seconds")
    print("=" * (len(title) + 12))


def search_query(query: str, filters: Optional[Dict[str, Any]] = None):
    """Execute a search query.
    
    Args:
        query: Search query
        filters: Optional filters
    """
    url = f"{API_BASE_URL}/search"
    
    # Default options
    options = {
        "max_results": 5,
        "include_metadata": True,
        "rerank": True,
        "threshold": 0.7
    }
    
    # Request payload
    payload = {
        "query": query,
        "options": options
    }
    
    # Add filters if provided
    if filters:
        payload["filters"] = filters
    
    # Make request
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    
    response = requests.post(url, headers=headers, json=payload)
    print_response(response, "Search Query")


def get_suggestions(partial_query: str, limit: int = 5):
    """Get query suggestions.
    
    Args:
        partial_query: Partial query
        limit: Maximum number of suggestions
    """
    url = f"{API_BASE_URL}/suggestions?partial_query={partial_query}&limit={limit}"
    
    # Make request
    headers = {
        "Authorization": f"Bearer {API_KEY}"
    }
    
    response = requests.get(url, headers=headers)
    print_response(response, "Query Suggestions")


def submit_feedback(request_id: str, rating: str, comments: Optional[str] = None):
    """Submit feedback for a search result.
    
    Args:
        request_id: Request ID
        rating: Feedback rating ("positive" or "negative")
        comments: Optional feedback comments
    """
    url = f"{API_BASE_URL}/feedback"
    
    # Request payload
    payload = {
        "request_id": request_id,
        "rating": rating
    }
    
    # Add comments if provided
    if comments:
        payload["comments"] = comments
    
    # Make request
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    
    response = requests.post(url, headers=headers, json=payload)
    print_response(response, "Submit Feedback")


def get_metadata_options():
    """Get metadata options."""
    url = f"{API_BASE_URL}/metadata/options"
    
    # Make request
    headers = {
        "Authorization": f"Bearer {API_KEY}"
    }
    
    response = requests.get(url, headers=headers)
    print_response(response, "Metadata Options")


def get_session_status():
    """Get session status."""
    url = f"{API_BASE_URL}/session/status"
    
    # Make request
    headers = {
        "Authorization": f"Bearer {API_KEY}"
    }
    
    response = requests.get(url, headers=headers)
    print_response(response, "Session Status")


def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="EXASPERATION API Test Client")
    parser.add_argument(
        "--api-url", 
        type=str, 
        default=API_BASE_URL, 
        help="API base URL"
    )
    parser.add_argument(
        "--api-key", 
        type=str, 
        default=API_KEY, 
        help="API key"
    )
    parser.add_argument(
        "--endpoint", 
        type=str, 
        choices=["search", "suggestions", "feedback", "metadata", "session", "all"],
        default="all",
        help="Endpoint to test"
    )
    args = parser.parse_args()
    
    # Update global variables
    global API_BASE_URL, API_KEY
    API_BASE_URL = args.api_url
    API_KEY = args.api_key
    
    # Print API information
    print(f"Using API URL: {API_BASE_URL}")
    print(f"Using API Key: {API_KEY[:4]}...{API_KEY[-4:]}")
    
    # Test selected endpoint
    if args.endpoint == "search" or args.endpoint == "all":
        search_query("How does the password reset detection rule work?")
        
    if args.endpoint == "suggestions" or args.endpoint == "all":
        get_suggestions("How does")
        
    if args.endpoint == "feedback" or args.endpoint == "all":
        submit_feedback("req_1234567890", "positive", "This was very helpful!")
        
    if args.endpoint == "metadata" or args.endpoint == "all":
        get_metadata_options()
        
    if args.endpoint == "session" or args.endpoint == "all":
        get_session_status()
    
    print("\nTests completed.")


if __name__ == "__main__":
    main()