#!/bin/bash

set -e

# ANSI color codes
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}Setting up EXASPERATION environment...${NC}"

# Check if Python 3.8+ is installed
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}Python 3 is not installed. Please install Python 3.8 or higher.${NC}"
    exit 1
fi

PY_MAJOR=$(python3 -c 'import sys; print(sys.version_info.major)')
PY_MINOR=$(python3 -c 'import sys; print(sys.version_info.minor)')
PY_VERSION="$PY_MAJOR.$PY_MINOR"

# Simple integer comparison
if [ "$PY_MAJOR" -lt 3 ] || ([ "$PY_MAJOR" -eq 3 ] && [ "$PY_MINOR" -lt 8 ]); then
    echo -e "${RED}Python 3.8 or higher is required. You have Python $PY_VERSION.${NC}"
    exit 1
fi

# Warn about Python 3.12+
if [ "$PY_MAJOR" -gt 3 ] || ([ "$PY_MAJOR" -eq 3 ] && [ "$PY_MINOR" -ge 12 ]); then
    echo -e "${YELLOW}Python 3.12+ detected. Some packages may have compatibility issues.${NC}"
    echo -e "${YELLOW}Python 3.10-3.11 is recommended for best compatibility.${NC}"
fi

echo -e "${GREEN}Python $PY_VERSION detected.${NC}"

# Create virtual environment if it doesn't exist
if [ ! -d "chromadb_venv" ]; then
    echo -e "${YELLOW}Creating embedding environment...${NC}"
    python3 -m venv chromadb_venv
fi

# Activate virtual environment
echo -e "${YELLOW}Activating virtual environment...${NC}"
source chromadb_venv/bin/activate

# Install dependencies
echo -e "${YELLOW}Installing dependencies...${NC}"
pip install --upgrade pip
pip install -r chromadb.requirements.txt

# Create .env file if it doesn't exist
if [ ! -f ".env" ]; then
    echo -e "${YELLOW}Creating .env file from template...${NC}"
    cp .env.example .env
    echo -e "${GREEN}Please edit the .env file to add your API keys.${NC}"
fi

# Create data directory if it doesn't exist
if [ ! -d "data" ]; then
    echo -e "${YELLOW}Creating data directory...${NC}"
    mkdir -p data/chromadb
fi

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo -e "${YELLOW}Docker is not installed. You'll need Docker to run ChromaDB.${NC}"
    echo -e "${YELLOW}Please install Docker from https://docs.docker.com/get-docker/${NC}"
fi

# Check if docker-compose is installed
if ! command -v docker-compose &> /dev/null; then
    echo -e "${YELLOW}Docker Compose is not installed. You'll need it to run ChromaDB.${NC}"
    echo -e "${YELLOW}Please install Docker Compose from https://docs.docker.com/compose/install/${NC}"
fi

# Check if Exabeam Content-Library-CIM2 exists
if [ ! -d "data/content-library-cim2" ]; then
    echo -e "${YELLOW}Exabeam Content-Library-CIM2 not found.${NC}"
    echo -e "${YELLOW}Please clone the repository:${NC}"
    echo -e "git clone https://github.com/ExabeamLabs/Content-Library-CIM2.git data/content-library-cim2"
fi

echo -e "${GREEN}Setup complete!${NC}"
echo -e "${GREEN}To activate the virtual environment, run:${NC}"
echo -e "source chromadb_venv/bin/activate"
echo -e "${GREEN}To start ChromaDB, run:${NC}"
echo -e "docker-compose up -d"
echo -e "${GREEN}To initialize the database, run:${NC}"
echo -e "python -m src.initialize_db"