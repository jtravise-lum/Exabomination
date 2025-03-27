#!/bin/bash

# Run the EXASPERATION API test client

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

# Set test API key
export EXASPERATION_API_KEY="test_key_1234567890"

# Run the API test client
echo "Running EXASPERATION API test client..."
python frontend/api/test_client.py "$@"