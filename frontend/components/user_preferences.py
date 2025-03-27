"""User preferences component for the EXASPERATION frontend."""

import streamlit as st
from typing import Dict, Any, Optional


def user_preferences():
    """Render user preferences panel in the sidebar."""
    if "preferences" not in st.session_state:
        # Initialize default preferences
        st.session_state.preferences = {
            "theme": "light",
            "result_display": {
                "expand_sources": True,
                "show_metadata": True,
                "max_sources": 5
            },
            "notifications": {
                "enable_sound": False,
                "enable_toast": True
            }
        }
    
    with st.sidebar.expander("Settings", expanded=False):
        # Theme selection
        theme = st.radio(
            "Theme", 
            options=["light", "dark"], 
            index=0 if st.session_state.preferences["theme"] == "light" else 1,
            horizontal=True,
            key="pref_theme"
        )
        st.session_state.preferences["theme"] = theme
        
        # Results display options
        st.markdown("##### Results Display")
        
        expand_sources = st.checkbox(
            "Auto-expand sources", 
            value=st.session_state.preferences["result_display"]["expand_sources"],
            key="pref_expand_sources"
        )
        st.session_state.preferences["result_display"]["expand_sources"] = expand_sources
        
        show_metadata = st.checkbox(
            "Show document metadata", 
            value=st.session_state.preferences["result_display"]["show_metadata"],
            key="pref_show_metadata"
        )
        st.session_state.preferences["result_display"]["show_metadata"] = show_metadata
        
        max_sources = st.slider(
            "Maximum sources to display",
            min_value=1,
            max_value=10,
            value=st.session_state.preferences["result_display"]["max_sources"],
            key="pref_max_sources"
        )
        st.session_state.preferences["result_display"]["max_sources"] = max_sources
        
        # Notification preferences
        st.markdown("##### Notifications")
        
        enable_toast = st.checkbox(
            "Enable toast notifications", 
            value=st.session_state.preferences["notifications"]["enable_toast"],
            key="pref_enable_toast"
        )
        st.session_state.preferences["notifications"]["enable_toast"] = enable_toast
        
        # Reset preferences button
        if st.button("Reset to Defaults", key="reset_preferences"):
            st.session_state.preferences = {
                "theme": "light",
                "result_display": {
                    "expand_sources": True,
                    "show_metadata": True,
                    "max_sources": 5
                },
                "notifications": {
                    "enable_sound": False,
                    "enable_toast": True
                }
            }
            st.rerun()
    
    return st.session_state.preferences


def get_preference(key_path: str, default: Any = None) -> Any:
    """Get a preference value by dot-notation path.
    
    Args:
        key_path: Dot-notation path to the preference (e.g. "result_display.expand_sources")
        default: Default value if preference doesn't exist
        
    Returns:
        Preference value
    """
    if "preferences" not in st.session_state:
        return default
    
    parts = key_path.split(".")
    value = st.session_state.preferences
    
    try:
        for part in parts:
            value = value[part]
        return value
    except (KeyError, TypeError):
        return default


def set_preference(key_path: str, value: Any) -> None:
    """Set a preference value by dot-notation path.
    
    Args:
        key_path: Dot-notation path to the preference (e.g. "result_display.expand_sources")
        value: New value for the preference
    """
    if "preferences" not in st.session_state:
        user_preferences()  # Initialize preferences
    
    parts = key_path.split(".")
    pref_dict = st.session_state.preferences
    
    # Navigate to the parent object
    for part in parts[:-1]:
        if part not in pref_dict:
            pref_dict[part] = {}
        pref_dict = pref_dict[part]
    
    # Set the value on the parent object
    pref_dict[parts[-1]] = value