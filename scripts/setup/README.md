# EXASPERATION Setup Scripts

This directory contains scripts used to set up and install EXASPERATION components.

## Available Scripts

- `setup.sh`: Main setup script that orchestrates the entire setup process
- `setup_embedding.sh`: Sets up the embedding pipeline and environment
- `setup_frontend.sh`: Sets up the frontend environment and dependencies
- `setup_certbot.sh`: Configures SSL certificates using Certbot
- `setup_env.sh`: Sets up environment variables from templates

## Usage

These scripts should be run from the project root directory:

```bash
# Run the main setup
./scripts/setup/setup.sh

# Set up only the frontend environment
./scripts/setup/setup_frontend.sh
```

## Prerequisites

Before running these scripts, ensure you have:

1. Python 3.10+ installed
2. Docker and Docker Compose installed (for containerized components)
3. Sufficient permissions to create directories and virtual environments
4. Internet access for downloading dependencies

## Virtual Environments

The setup scripts create the following virtual environments:

- `chromadb_venv`: For embeddings and ChromaDB interactions
- `frontend_venv`: For the Streamlit frontend
- `api_venv`: For the FastAPI backend
