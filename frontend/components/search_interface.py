"""Search interface component for the EXASPERATION frontend."""

import streamlit as st
from typing import Callable, Optional, List, Dict, Any

from frontend.config import EXAMPLE_QUERIES
from frontend.utils.api_client import api_client


def search_interface(
    on_search: Callable[[str, Dict[str, Any]], None],
    loading: bool = False
) -> str:
    """Render the search interface component.
    
    Args:
        on_search: Callback function when search is submitted
        loading: Whether a search is currently in progress
        
    Returns:
        Current query text
    """
    # Initialize session state for query history if it doesn't exist
    if "query_history" not in st.session_state:
        st.session_state.query_history = []
    
    # Get current query from session state or initialize it
    current_query = st.session_state.get("current_query", "")
    
    # Search header with Exabeam styling
    st.markdown(
        """<h1 style='text-align: center; color: #0066CC;'>
        EXASPERATION <span style='font-size: 0.7em; color: #666;'>(Exabeam Automated Search Assistant)</span>
        </h1>""", 
        unsafe_allow_html=True
    )
    
    # Search description
    st.markdown(
        """<p style='text-align: center;'>
        Ask questions about Exabeam documentation, use cases, parsers, and more.
        </p>""",
        unsafe_allow_html=True
    )
    
    # Main search input
    with st.form(key="search_form", clear_on_submit=False):
        col1, col2 = st.columns([6, 1])
        
        with col1:
            query = st.text_input(
                "Enter your question",
                value=current_query,
                placeholder="e.g., How does the password reset detection rule work?",
                disabled=loading,
                key="query_input"
            )
        
        with col2:
            submit_button = st.form_submit_button(
                "Search", 
                disabled=loading,
                use_container_width=True,
                type="primary"
            )
        
        # Advanced filters expander (to be implemented)
        with st.expander("Advanced filters", expanded=False):
            st.info("Advanced filters will be implemented in a future update.")
            # Placeholder for filters
            # This will be linked with the filters_panel component
    
    # Process form submission
    if submit_button and query and not loading:
        st.session_state.current_query = query
        
        # Add to query history if not already present
        if query not in st.session_state.query_history:
            st.session_state.query_history = [query] + st.session_state.query_history
            if len(st.session_state.query_history) > 10:  # Limit history size
                st.session_state.query_history = st.session_state.query_history[:10]
        
        # Call the search callback
        on_search(query, {})
    
    # Show example queries (moved outside the form)
    with st.expander("Example questions", expanded=False):
        example_cols = st.columns(2)
        for i, example in enumerate(EXAMPLE_QUERIES):
            with example_cols[i % 2]:
                if st.button(
                    example, 
                    key=f"example_{i}",
                    use_container_width=True,
                    disabled=loading
                ):
                    # Set the example as the current query and trigger search
                    st.session_state.current_query = example
                    on_search(example, {})
    
    # Show loading indicator if search is in progress
    if loading:
        st.info("Searching for your answer...")
    
    return query


def query_history_sidebar():
    """Display search query history in the sidebar."""
    if "query_history" in st.session_state and len(st.session_state.query_history) > 0:
        st.sidebar.header("Recent Searches")
        
        for i, past_query in enumerate(st.session_state.query_history):
            if st.sidebar.button(
                past_query, 
                key=f"history_{i}",
                use_container_width=True
            ):
                st.session_state.current_query = past_query
                st.rerun()  # Trigger rerun to update the main query field
    
        if st.sidebar.button("Clear History", type="secondary"):
            st.session_state.query_history = []
            st.rerun()