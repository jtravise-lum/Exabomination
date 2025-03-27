# EXASPERATION Frontend Components

This document describes the key components of the EXASPERATION frontend application, their functionality, and relationships.

## 1. Main Application

**File:** `app.py`

The main Streamlit application entry point that initializes the user interface and orchestrates the various components.

**Key Responsibilities:**
- Application initialization and configuration
- Page routing and navigation
- Session state management
- Authentication handling
- Main layout structure

## 2. Search Interface

**File:** `components/search_interface.py`

The primary search input component where users enter natural language queries.

**Features:**
- Query input field with auto-suggestions
- Example queries display
- Search history tracking
- Advanced search options toggle
- Search submit functionality

**States:**
- Current query text
- Search in progress indicator
- Previous queries list

## 3. Results Display

**File:** `components/results_display.py`

Component that renders search results and answers from the backend.

**Features:**
- Answer rendering with markdown support
- Source citation display
- Code snippet formatting
- Expandable context sections
- Feedback collection (thumbs up/down)
- Copy to clipboard functionality

**States:**
- Current result data
- Expanded/collapsed sections
- Feedback state

## 4. Filters Panel

**File:** `components/filters_panel.py`

Component for filtering search results by metadata.

**Features:**
- Document type selection (parsers, use cases, etc.)
- Vendor filtering
- Product filtering
- Date range selection
- Clear filters option

**States:**
- Active filters
- Available filter options
- Filter visibility toggle

## 5. User Preferences

**File:** `components/user_preferences.py`

Component for managing user preferences and settings.

**Features:**
- Theme selection
- Result display options
- Query history management
- API key management (if applicable)
- Notification settings

**States:**
- Current preferences
- Settings visibility toggle

## 6. API Client

**File:** `utils/api_client.py`

Utility for communicating with the backend API.

**Functionality:**
- Query submission
- Result fetching
- Error handling
- Rate limiting
- Connection status management

**Methods:**
- `search(query, filters)`
- `get_suggestions(partial_query)`
- `submit_feedback(query_id, feedback)`
- `get_metadata_options()`

## 7. Analytics Tracker

**File:** `utils/analytics.py`

Component that tracks user interactions for analytics purposes.

**Functionality:**
- Query tracking
- Result interaction logging
- Session timing
- Feature usage metrics
- Error reporting

**Methods:**
- `track_query(query_text, filters)`
- `track_result_interaction(result_id, interaction_type)`
- `track_session(session_id, duration)`
- `report_error(error_type, details)`

## 8. Help System

**File:** `components/help_system.py`

Component providing contextual help and guidance.

**Features:**
- Tooltips for UI elements
- Guided tours for new users
- Search syntax documentation
- Keyboard shortcuts reference
- Frequently asked questions

**States:**
- Current help context
- Tour progress
- Help visibility toggle

## 9. Notifications

**File:** `components/notifications.py`

Component for displaying system notifications and alerts.

**Features:**
- Success messages
- Error alerts
- Information notices
- Loading indicators
- Toast notifications

**Methods:**
- `show_success(message)`
- `show_error(message)`
- `show_info(message)`
- `show_loading(message)`

## 10. Authentication

**File:** `utils/auth.py`

Component handling user authentication and session management.

**Features:**
- Login interface
- Session tracking
- Permission management
- Secure credential handling
- Session timeout handling

**Methods:**
- `login(username, password)`
- `logout()`
- `check_session()`
- `get_current_user()`

## Component Relationships

```
                     +----------------+
                     |                |
                     |    app.py      |
                     |                |
                     +-------+--------+
                             |
                             |
        +-------------------+-------------------+
        |                   |                   |
+-------v-------+   +-------v-------+   +-------v-------+
|               |   |               |   |               |
| search_       |   | results_      |   | filters_      |
| interface.py  |   | display.py    |   | panel.py      |
|               |   |               |   |               |
+-------+-------+   +-------+-------+   +---------------+
        |                   |
        |                   |
        |            +------v-------+
        |            |              |
        +----------->| api_client.py|
                     |              |
                     +--------------+
```

## Styling Guidelines

- Use Exabeam brand colors:
  - Primary: `#0066CC`
  - Secondary: `#00A3E0`
  - Accent: `#FF6B00`
  - Background: `#F5F7FA`
  - Text: `#333333`

- Typography:
  - Headings: 'Inter', sans-serif
  - Body: 'Inter', sans-serif
  - Code: 'Source Code Pro', monospace

- Component styling:
  - Consistent padding (16px)
  - Rounded corners (4px)
  - Subtle shadows for elevated components
  - Clear visual hierarchy with whitespace

## State Management

All components should follow these state management practices:

1. Use Streamlit's session state for persistent data across reruns
2. Initialize state variables at component startup
3. Implement clear state update methods
4. Document state dependencies between components
5. Handle state initialization for new sessions