"""Analytics for the EXASPERATION frontend."""

import streamlit as st
from typing import Dict, Any, Optional, List
import json
import time
from datetime import datetime

from frontend.config import ENABLE_ANALYTICS


class AnalyticsTracker:
    """Component to track user interactions for analytics purposes."""
    
    def __init__(self):
        """Initialize the analytics tracker."""
        # Skip initialization if analytics are disabled
        if not ENABLE_ANALYTICS:
            return
            
        # Create analytics storage in session state if it doesn't exist
        if "analytics" not in st.session_state:
            st.session_state.analytics = {
                "queries": [],
                "interactions": [],
                "errors": [],
                "session_start": datetime.now().isoformat(),
            }
    
    def track_query(self, query_text: str, filters: Optional[Dict[str, Any]] = None) -> str:
        """Track a user query.
        
        Args:
            query_text: The query text
            filters: Optional search filters
            
        Returns:
            Query ID
        """
        if not ENABLE_ANALYTICS:
            return f"query_{int(time.time())}"
            
        query_id = f"query_{int(time.time())}"
        
        # Add query to tracking data
        st.session_state.analytics["queries"].append({
            "id": query_id,
            "text": query_text,
            "filters": filters,
            "timestamp": datetime.now().isoformat()
        })
        
        return query_id
    
    def track_result_interaction(self, result_id: str, interaction_type: str) -> None:
        """Track user interaction with search results.
        
        Args:
            result_id: ID of the search result
            interaction_type: Type of interaction (e.g., feedback, source_click)
        """
        if not ENABLE_ANALYTICS:
            return
            
        # Add interaction to tracking data
        st.session_state.analytics["interactions"].append({
            "result_id": result_id,
            "type": interaction_type,
            "timestamp": datetime.now().isoformat()
        })
    
    def track_session(self, session_id: str, duration_seconds: float) -> None:
        """Track session information.
        
        Args:
            session_id: Session ID
            duration_seconds: Duration of the session in seconds
        """
        if not ENABLE_ANALYTICS:
            return
        
        # Update session information
        st.session_state.analytics["session_duration"] = duration_seconds
        st.session_state.analytics["session_end"] = datetime.now().isoformat()
    
    def report_error(self, error_type: str, details: Dict[str, Any]) -> None:
        """Report an error for analytics.
        
        Args:
            error_type: Type of error
            details: Error details
        """
        if not ENABLE_ANALYTICS:
            return
            
        # Add error to tracking data
        st.session_state.analytics["errors"].append({
            "type": error_type,
            "details": details,
            "timestamp": datetime.now().isoformat()
        })
    
    def export_analytics(self) -> Dict[str, Any]:
        """Export analytics data.
        
        Returns:
            Dictionary of analytics data
        """
        if not ENABLE_ANALYTICS or "analytics" not in st.session_state:
            return {}
            
        return st.session_state.analytics


# Create a singleton instance
analytics_tracker = AnalyticsTracker()