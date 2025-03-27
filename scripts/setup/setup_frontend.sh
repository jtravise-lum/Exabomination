#!/bin/bash
# Setup script for EXASPERATION frontend environment

# Set colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${YELLOW}Setting up EXASPERATION frontend environment...${NC}"

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}Error: Python 3 is required but not installed.${NC}"
    exit 1
fi

# Create virtual environment if it doesn't exist
if [ ! -d "frontend_venv" ]; then
    echo -e "${YELLOW}Creating virtual environment...${NC}"
    python3 -m venv frontend_venv
    if [ $? -ne 0 ]; then
        echo -e "${RED}Failed to create virtual environment.${NC}"
        exit 1
    fi
    echo -e "${GREEN}Virtual environment created successfully.${NC}"
fi

# Activate virtual environment
echo -e "${YELLOW}Activating virtual environment...${NC}"
source frontend_venv/bin/activate

# Install dependencies
echo -e "${YELLOW}Installing frontend dependencies...${NC}"
pip install -r frontend.requirements.txt
if [ $? -ne 0 ]; then
    echo -e "${RED}Failed to install dependencies.${NC}"
    exit 1
fi

# Create .env.frontend file if it doesn't exist
if [ ! -f ".env.frontend" ]; then
    echo -e "${YELLOW}Creating .env.frontend file from example...${NC}"
    cp .env.frontend.example .env.frontend
    echo -e "${GREEN}.env.frontend file created. Please update with your settings.${NC}"
else
    echo -e "${YELLOW}.env.frontend file already exists.${NC}"
fi

# Create any necessary directories
echo -e "${YELLOW}Ensuring frontend directories exist...${NC}"
mkdir -p frontend/assets/css
mkdir -p frontend/assets/images
mkdir -p frontend/assets/js

echo -e "${GREEN}Frontend environment setup complete!${NC}"
echo -e "${YELLOW}To run the frontend application:${NC}"
echo -e "  1. Activate the virtual environment: ${GREEN}source frontend_venv/bin/activate${NC}"
echo -e "  2. Start the application: ${GREEN}streamlit run frontend/app.py${NC}"
echo -e ""
echo -e "${YELLOW}To deploy with Docker Compose:${NC}"
echo -e "  Run: ${GREEN}docker-compose up -d${NC}"