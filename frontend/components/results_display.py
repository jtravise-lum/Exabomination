"""Results display component for the EXASPERATION frontend."""

import streamlit as st
from typing import Dict, List, Any, Optional
from datetime import datetime

from frontend.api.models import SearchResponse, SourceDocument, ErrorResponse, FeedbackResponse


def results_display(result: Optional[SearchResponse] = None, error: Optional[ErrorResponse] = None):
    """Render the search results component.
    
    Args:
        result: Search result to display
        error: Error response to display
    """
    # Handle error state
    if error is not None:
        st.error(
            f"Error: {error.error.get('message', 'Unknown error')}. "
            f"Please try again or rephrase your query."
        )
        return
    
    # Handle empty result state
    if result is None:
        # First-time visit, show welcome message
        if "current_query" not in st.session_state:
            st.markdown(
                """
                ## Welcome to EXASPERATION
                
                Use the search box above to ask questions about Exabeam documentation.
                
                ### Examples:
                - How does the password reset detection rule work?
                - What events are monitored for lateral movement detection?
                - How do I set up the AWS CloudTrail data source?
                """
            )
        return
    
    # Display the answer with proper styling
    st.markdown("### Answer")
    st.markdown(result.answer)
    
    # Add feedback buttons
    col1, col2, col3 = st.columns([1, 1, 5])
    with col1:
        if st.button("👍 Helpful", key="feedback_positive"):
            _submit_feedback(result.request_id, "positive")
            st.success("Thank you for your feedback!")
    with col2:
        if st.button("👎 Not Helpful", key="feedback_negative"):
            _submit_feedback(result.request_id, "negative")
            st.info("Thank you for your feedback! We'll try to improve.")
    
    # Add copy button
    with col3:
        if st.button("📋 Copy Answer", key="copy_answer"):
            st.code(f"""
{result.answer}

Source: EXASPERATION - Exabeam Documentation Search Assistant
""", language="")
    
    # Display sources header
    if result.sources and len(result.sources) > 0:
        st.markdown("### Sources")
        _display_sources(result.sources)
    
    # Display suggested follow-up queries
    if result.suggested_queries and len(result.suggested_queries) > 0:
        st.markdown("### Follow-up Questions")
        cols = st.columns(2)  # 2 columns for follow-up suggestions
        
        for i, suggested_query in enumerate(result.suggested_queries):
            with cols[i % 2]:
                if st.button(
                    suggested_query, 
                    key=f"suggested_{i}",
                    use_container_width=True
                ):
                    # Set as current query and trigger search
                    st.session_state.current_query = suggested_query
                    st.rerun()
    
    # Display metadata at the bottom
    if st.button("Show Request Details", key="show_details"):
        st.markdown("#### Request Details")
        st.markdown(f"**Request ID:** {result.request_id}")
        st.markdown(f"**Processing Time:** {result.metadata.processing_time_ms} ms")
        st.markdown(f"**Total Matches:** {result.metadata.total_matches}")
        st.markdown(f"**Relevance Threshold:** {result.metadata.threshold_applied}")


def _display_sources(sources: List[SourceDocument]):
    """Display source documents with formatting.
    
    Args:
        sources: List of source documents to display
    """
    for i, source in enumerate(sources):
        # Use a default title if none is provided
        title = source.title if source.title else f"Document {source.id}"
        st.markdown(f"#### Source {i+1}: {title}")
        st.markdown(f"**Relevance Score:** {source.relevance_score:.2f}")
        
        # Format metadata
        metadata_str = []
        if source.metadata.document_type:
            metadata_str.append(f"**Type:** {source.metadata.document_type}")
        if source.metadata.vendor:
            metadata_str.append(f"**Vendor:** {source.metadata.vendor}")
        if source.metadata.product:
            metadata_str.append(f"**Product:** {source.metadata.product}")
        
        st.markdown(" | ".join(metadata_str))
        
        # Display source URL as a clickable link
        st.markdown(f"[View Source Document]({source.url})")
        
        # Display a collapsible section for content
        # Instead of using a nested expander, use a button to toggle content
        content_key = f"show_content_{i}"
        
        if st.button(f"Show Content for Source {i+1}" if content_key not in st.session_state or not st.session_state[content_key] else f"Hide Content for Source {i+1}", key=f"toggle_content_{i}"):
            st.session_state[content_key] = not st.session_state.get(content_key, False)
            
        if content_key in st.session_state and st.session_state[content_key]:
            # Format the content nicely
            if source.content:
                # Use markdown for better formatting
                st.markdown("##### Content:")
                st.markdown(source.content)
            else:
                st.info("No content available for this source.")
        
        if i < len(sources) - 1:  # Add separator except after last source
            st.markdown("---")


def _submit_feedback(request_id: str, rating: str):
    """Submit feedback to the API.
    
    Args:
        request_id: Request ID
        rating: Feedback rating (positive/negative)
    """
    # Import at the top level of the file 
    from frontend.utils.api_client import api_client
    
    try:
        # Submit feedback to API
        response = api_client.submit_feedback(request_id, rating)
        if isinstance(response, ErrorResponse):
            st.warning(f"Feedback submission error: {response.error.get('message', 'Unknown error')}")
        elif isinstance(response, FeedbackResponse):
            st.success(f"Feedback submitted: {response.message}")
    except Exception as e:
        st.warning(f"Could not submit feedback: {str(e)}")