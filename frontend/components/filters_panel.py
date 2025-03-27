"""Filters panel component for the EXASPERATION frontend."""

import streamlit as st
from typing import Dict, List, Any, Optional, Callable

from frontend.api.models import SearchFilters, MetadataOptionsResponse


def filters_panel(
    on_filter_change: Callable[[SearchFilters], None],
    metadata_options: Optional[MetadataOptionsResponse] = None
) -> SearchFilters:
    """Render the search filters panel component.
    
    Args:
        on_filter_change: Callback function when filters change
        metadata_options: Available metadata options for filtering
        
    Returns:
        Current filter settings
    """
    # Initialize session state for filters if it doesn't exist
    if "filters" not in st.session_state:
        st.session_state.filters = SearchFilters()
    
    filters = st.session_state.filters
    
    # Placeholder when metadata options aren't available
    if metadata_options is None:
        st.warning("Metadata options not available. Filter functionality limited.")
        
        # Provide minimal filter UI even without metadata
        with st.expander("Basic Filters", expanded=False):
            date_cols = st.columns(2)
            with date_cols[0]:
                created_after = st.date_input(
                    "Created After",
                    value=None,
                    key="created_after"
                )
                if created_after:
                    filters.created_after = created_after.isoformat()
                
            with date_cols[1]:
                created_before = st.date_input(
                    "Created Before",
                    value=None,
                    key="created_before"
                )
                if created_before:
                    filters.created_before = created_before.isoformat()
        
        return filters
    
    # Full filter UI with metadata options
    st.sidebar.header("Search Filters")
    
    # Document Types filter
    if metadata_options.document_types:
        selected_doc_types = st.sidebar.multiselect(
            "Document Types",
            options=metadata_options.document_types,
            default=filters.document_types or [],
            key="filter_doc_types"
        )
        filters.document_types = selected_doc_types if selected_doc_types else None
    
    # Vendors filter
    if metadata_options.vendors:
        selected_vendors = st.sidebar.multiselect(
            "Vendors",
            options=metadata_options.vendors,
            default=filters.vendors or [],
            key="filter_vendors"
        )
        filters.vendors = selected_vendors if selected_vendors else None
        
        # Products filter - dependent on selected vendors
        if selected_vendors and metadata_options.products:
            # Get products for selected vendors
            available_products = []
            for vendor in selected_vendors:
                if vendor in metadata_options.products:
                    available_products.extend(metadata_options.products[vendor])
            
            if available_products:
                selected_products = st.sidebar.multiselect(
                    "Products",
                    options=available_products,
                    default=filters.products or [],
                    key="filter_products"
                )
                filters.products = selected_products if selected_products else None
    
    # Date range filters
    if metadata_options.date_range:
        with st.sidebar.expander("Date Range", expanded=False):
            date_cols = st.columns(2)
            
            # Parse date strings from metadata options
            try:
                oldest_date = metadata_options.date_range.get("oldest")
                newest_date = metadata_options.date_range.get("newest")
            except:
                oldest_date = None
                newest_date = None
            
            with date_cols[0]:
                created_after = st.date_input(
                    "After",
                    value=None,
                    key="filter_after"
                )
                if created_after:
                    filters.created_after = created_after.isoformat()
                
            with date_cols[1]:
                created_before = st.date_input(
                    "Before",
                    value=None,
                    key="filter_before"
                )
                if created_before:
                    filters.created_before = created_before.isoformat()
    
    # Clear filters button
    if st.sidebar.button("Clear All Filters", key="clear_filters"):
        st.session_state.filters = SearchFilters()
        filters = st.session_state.filters
        # Call the callback to notify about filter changes
        on_filter_change(filters)
    
    # Update filters in session state
    st.session_state.filters = filters
    
    return filters