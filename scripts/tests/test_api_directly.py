#!/usr/bin/env python3
"""Test the API service layer directly."""

import asyncio
from frontend.api.service import ExasperationService

async def test_search():
    """Test the search functionality."""
    service = ExasperationService()
    print("Service initialized")
    
    # Test search query
    result = await service.process_search_query(
        query="How does password reset detection work?",
        user_id="test_user"
    )
    
    print("\nSearch result:")
    print(f"Answer: {result.get('answer', 'No answer')}")
    print(f"Sources: {len(result.get('sources', []))}")
    
    # Print sources if available
    if result.get('sources'):
        print("\nTop sources:")
        for i, source in enumerate(result.get('sources', [])[:2]):
            print(f"Source {i+1}: {source.get('title')} - {source.get('relevance_score')}")
    
    # Print metadata
    print("\nMetadata:")
    print(f"Processing time: {result.get('metadata', {}).get('processing_time_ms')}ms")
    print(f"Total matches: {result.get('metadata', {}).get('total_matches')}")

if __name__ == "__main__":
    asyncio.run(test_search())