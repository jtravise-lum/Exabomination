#!/bin/bash

# Run the EXASPERATION API server

# Check if API virtual environment exists, create if not
if [ ! -d "api_venv" ]; then
    echo "Creating API virtual environment..."
    python3 -m venv api_venv
    source api_venv/bin/activate
    pip install -r frontend.requirements.txt
else
    # Activate the API virtual environment
    source api_venv/bin/activate
fi

# Set DEBUG_MODE to True for development
export DEBUG_MODE=True

# Run the API server
echo "Starting EXASPERATION API server..."
python -m frontend.api.main "$@"