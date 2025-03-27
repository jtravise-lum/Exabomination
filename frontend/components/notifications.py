"""Notifications component for the EXASPERATION frontend."""

import streamlit as st
from typing import Optional, Dict, Any
import uuid


class NotificationSystem:
    """Component for displaying system notifications and alerts."""
    
    def __init__(self):
        """Initialize the notification system."""
        # Create notifications in session state if they don't exist
        if "notifications" not in st.session_state:
            st.session_state.notifications = []
    
    def _add_notification(self, message: str, notification_type: str, 
                          duration: Optional[int] = None) -> str:
        """Add a notification to session state.
        
        Args:
            message: Notification message
            notification_type: Type of notification (success, error, info, warning)
            duration: Display duration in seconds (None for permanent)
            
        Returns:
            Notification ID
        """
        notification_id = str(uuid.uuid4())
        
        st.session_state.notifications.append({
            "id": notification_id,
            "message": message,
            "type": notification_type,
            "duration": duration,
            "created_at": st.session_state.get("_current_time", 0)
        })
        
        return notification_id
    
    def show_success(self, message: str, duration: Optional[int] = 5) -> str:
        """Show a success notification.
        
        Args:
            message: Notification message
            duration: Display duration in seconds (None for permanent)
            
        Returns:
            Notification ID
        """
        return self._add_notification(message, "success", duration)
    
    def show_error(self, message: str, duration: Optional[int] = None) -> str:
        """Show an error notification.
        
        Args:
            message: Notification message
            duration: Display duration in seconds (None for permanent)
            
        Returns:
            Notification ID
        """
        return self._add_notification(message, "error", duration)
    
    def show_info(self, message: str, duration: Optional[int] = 5) -> str:
        """Show an information notification.
        
        Args:
            message: Notification message
            duration: Display duration in seconds (None for permanent)
            
        Returns:
            Notification ID
        """
        return self._add_notification(message, "info", duration)
    
    def show_warning(self, message: str, duration: Optional[int] = 10) -> str:
        """Show a warning notification.
        
        Args:
            message: Notification message
            duration: Display duration in seconds (None for permanent)
            
        Returns:
            Notification ID
        """
        return self._add_notification(message, "warning", duration)
    
    def show_loading(self, message: str = "Loading...") -> str:
        """Show a loading notification.
        
        Args:
            message: Loading message
            
        Returns:
            Notification ID
        """
        return self._add_notification(message, "loading", None)
    
    def clear(self, notification_id: Optional[str] = None) -> None:
        """Clear notifications.
        
        Args:
            notification_id: Specific notification ID to clear (None for all)
        """
        if notification_id is None:
            st.session_state.notifications = []
        else:
            st.session_state.notifications = [
                n for n in st.session_state.notifications 
                if n["id"] != notification_id
            ]
    
    def render(self) -> None:
        """Render all active notifications."""
        if "notifications" not in st.session_state:
            return
            
        # Update current time
        if "_current_time" not in st.session_state:
            st.session_state._current_time = 0
        else:
            st.session_state._current_time += 1
            
        # Remove expired notifications
        st.session_state.notifications = [
            n for n in st.session_state.notifications
            if n["duration"] is None or 
               (st.session_state._current_time - n["created_at"]) // 10 < n["duration"]
        ]
        
        # Render each notification
        for notification in st.session_state.notifications:
            self._render_notification(notification)
    
    def _render_notification(self, notification: Dict[str, Any]) -> None:
        """Render a single notification.
        
        Args:
            notification: Notification data
        """
        notification_type = notification["type"]
        message = notification["message"]
        
        if notification_type == "success":
            st.success(message)
        elif notification_type == "error":
            st.error(message)
        elif notification_type == "info":
            st.info(message)
        elif notification_type == "warning":
            st.warning(message)
        elif notification_type == "loading":
            with st.spinner(message):
                pass


# Create a singleton instance
notifications = NotificationSystem()