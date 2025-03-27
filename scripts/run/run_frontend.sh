#!/bin/bash
# Run script for EXASPERATION frontend

# Navigate to the project root (works regardless of where script is called from)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
cd "${PROJECT_ROOT}" || exit 1

# Set colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${YELLOW}Starting EXASPERATION frontend...${NC}"

# Check if virtual environment exists
if [ ! -d "${PROJECT_ROOT}/frontend_venv" ]; then
    echo -e "${RED}Error: Virtual environment not found. Please run scripts/setup/setup_frontend.sh first.${NC}"
    exit 1
fi

# Activate virtual environment
echo -e "${YELLOW}Activating virtual environment...${NC}"
source "${PROJECT_ROOT}/frontend_venv/bin/activate"

# Check if .env.frontend file exists
if [ ! -f "${PROJECT_ROOT}/.env.frontend" ]; then
    echo -e "${YELLOW}Warning: .env.frontend file not found. Creating from example...${NC}"
    if [ -f "${PROJECT_ROOT}/.env.frontend.example" ]; then
        cp "${PROJECT_ROOT}/.env.frontend.example" "${PROJECT_ROOT}/.env.frontend"
        echo -e "${GREEN}.env.frontend file created. Using default settings.${NC}"
    else
        echo -e "${RED}Error: .env.frontend.example not found. Please create .env.frontend manually.${NC}"
        exit 1
    fi
fi

# Check if the API is running on the expected port
echo -e "${YELLOW}Checking API availability...${NC}"
API_URL=$(grep EXASPERATION_API_URL "${PROJECT_ROOT}/.env.frontend" | cut -d '=' -f2)
API_HOST=$(echo $API_URL | sed -e 's|^[^/]*//||' -e 's|/.*$||' -e 's|:.*$||')
API_PORT=$(echo $API_URL | grep -o ':[0-9]*' | cut -d ':' -f2)

if [ -z "$API_PORT" ]; then
    # Default port based on protocol
    if [[ $API_URL == https://* ]]; then
        API_PORT=443
    else
        API_PORT=80
    fi
fi

# Try to connect to the API
if command -v nc &> /dev/null; then
    if nc -z $API_HOST $API_PORT &> /dev/null; then
        echo -e "${GREEN}API is available at $API_HOST:$API_PORT${NC}"
    else
        echo -e "${YELLOW}Warning: API does not appear to be running at $API_HOST:$API_PORT${NC}"
        echo -e "${YELLOW}The frontend will run in limited functionality mode.${NC}"
    fi
else
    echo -e "${YELLOW}Note: 'nc' command not found. Cannot check API availability.${NC}"
fi

# Start the frontend application
echo -e "${GREEN}Starting Streamlit application...${NC}"
streamlit run "${PROJECT_ROOT}/frontend/app.py"

# Deactivate virtual environment
deactivate