# EXASPERATION Frontend

This directory contains the frontend application for EXASPERATION (Exabeam Automated Search Assistant Preventing Exasperating Research And Time-wasting In Official Notes).

## Overview

The EXASPERATION frontend is a Streamlit-based web application that allows users to search through Exabeam documentation using natural language queries. It communicates with the backend API to retrieve relevant information and generates user-friendly responses.

## Setup

### Prerequisites

- Python 3.8+ (3.10 recommended for best compatibility)
- Git
- Internet access for package installation

### Installation

1. Set up the dedicated virtual environment:

```bash
cd /path/to/EXASPERATION
./setup_frontend.sh
```

This script will:
- Create a dedicated virtual environment (`frontend_venv`)
- Install the required dependencies
- Create the necessary configuration files
- Set up the required directory structure

2. Activate the virtual environment:

```bash
source frontend_venv/bin/activate
```

3. Configure the application by editing `.env.frontend` with your specific settings.

### Running the Application

Start the Streamlit server:

```bash
streamlit run frontend/app.py
```

This will launch the application and open it in your default web browser at http://localhost:8501.

## Project Structure

```
frontend/
├── app.py                  # Main Streamlit application entry point
├── config.py               # Configuration management
├── assets/                 # Static assets
│   ├── css/                # Custom CSS
│   ├── images/             # Images and icons
│   └── js/                 # JavaScript files
├── components/             # UI components
│   ├── search_interface.py # Search input component
│   ├── results_display.py  # Results rendering component
│   ├── filters_panel.py    # Search filters component
│   ├── help_system.py      # Help and documentation component
│   ├── user_preferences.py # User settings component
│   └── notifications.py    # Notification system component
├── utils/                  # Utility functions
│   ├── api_client.py       # Backend API client
│   ├── analytics.py        # Usage analytics
│   └── formatting.py       # Text and result formatting
└── api/                    # API models and definitions
    └── models.py           # Pydantic models for API
```

## Configuration

The application is configured using environment variables defined in the `.env.frontend` file. Key configuration parameters include:

- `EXASPERATION_API_URL`: URL of the backend API
- `EXASPERATION_API_KEY`: API key for authentication
- `STREAMLIT_SERVER_PORT`: Port for the Streamlit server
- `ENABLE_ANALYTICS`: Flag to enable/disable analytics tracking
- `ENABLE_ADVANCED_FILTERS`: Flag to enable/disable advanced filtering options

## Development

### Adding New Components

To add a new component:

1. Create a new file in the `components/` directory
2. Import the component in `app.py`
3. Add the component to the appropriate section of the UI

### Modifying the API Client

When the backend API changes, update the API client in `utils/api_client.py` to match the new endpoints or parameters.

### Styling

Custom styling can be added in the `assets/css/` directory and imported in `app.py`.

## Troubleshooting

### Common Issues

- **API Connection Errors**: Verify the API URL in `.env.frontend` and check if the API server is running.
- **Missing Dependencies**: Ensure you have activated the virtual environment and run `pip install -r frontend.requirements.txt`.
- **Port Already in Use**: Change the port in `.env.frontend` if port 8501 is already in use.

### Debugging

Set `STREAMLIT_LOG_LEVEL=debug` in `.env.frontend` for more detailed logging.

## License

See the repository root for license information.