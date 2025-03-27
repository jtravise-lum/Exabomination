#!/bin/bash
# Script to start all EXASPERATION components

# Navigate to the project root (works regardless of where script is called from)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
cd "${PROJECT_ROOT}" || exit 1

# Set colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${YELLOW}Starting EXASPERATION services...${NC}"

# Check if Docker is running
if ! docker info >/dev/null 2>&1; then
    echo -e "${RED}Docker is not running. Please start Docker first.${NC}"
    exit 1
fi

# Create required directories
mkdir -p "${PROJECT_ROOT}/logs/caddy"

# Start the Docker services
echo -e "${YELLOW}Stopping any running containers...${NC}"
docker compose down

# Remove existing images to force rebuild
echo -e "${YELLOW}Removing frontend and API images...${NC}"
docker rmi exasperation-frontend:latest exasperation-api:latest 2>/dev/null || true

echo -e "${YELLOW}Starting Docker services with rebuild...${NC}"
docker compose up -d --build
if [ $? -ne 0 ]; then
    echo -e "${RED}Failed to start Docker services. See error above.${NC}"
    exit 1
fi

# Caddy is now running as a Docker container, no need to run it separately
echo -e "${YELLOW}Caddy is running in Docker. No need to start it separately.${NC}"

# Wait for services to be ready
echo -e "${YELLOW}Waiting for services to be ready...${NC}"
sleep 5

# Display service status
echo -e "${GREEN}EXASPERATION services started!${NC}"
echo -e "${YELLOW}ChromaDB is running at: http://localhost:8000${NC}"
echo -e "${YELLOW}API is running at: http://localhost:8888${NC}"
echo -e "${YELLOW}Frontend is running at: http://localhost:8501${NC}"
echo -e "${YELLOW}Application is accessible at: https://exp.travise.net${NC}"

echo -e "${YELLOW}To stop all services, run: ${GREEN}${PROJECT_ROOT}/scripts/run/stop_all.sh${NC}"
