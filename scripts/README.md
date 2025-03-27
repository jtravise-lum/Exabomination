# EXASPERATION Scripts

This directory contains scripts used to install, configure, run, and maintain the EXASPERATION system. Scripts are organized into the following subdirectories:

## Directory Structure

- `setup/`: Scripts for setting up and installing EXASPERATION components
  - `setup.sh`: Main setup script
  - `setup_embedding.sh`: Sets up the embedding pipeline
  - `setup_frontend.sh`: Sets up the frontend environment
  - `setup_certbot.sh`: Configures SSL certificates
  - `setup_env.sh`: Sets up environment variables

- `run/`: Scripts for running and controlling EXASPERATION services
  - `start_all.sh`: Starts all components (ChromaDB, API, Frontend, Caddy)
  - `stop_all.sh`: Stops all components
  - `start_api_server.sh`: Starts only the API server
  - `stop_api_server.sh`: Stops the API server
  - `run_api.sh`: Runs the API server in the foreground
  - `run_frontend.sh`: Runs the Streamlit frontend in the foreground
  - `api_server_status.sh`: Checks the status of the API server

- `db/`: Scripts for database management and maintenance
  - `check_chromadb.py`: Checks ChromaDB connection and status
  - `check_collection.py`: Examines a specific collection
  - `check_count.py`: Counts documents in collections
  - `check_db.py`: General database checks
  - `check_db_size.py`: Checks database size
  - `reset_chromadb.py`: Resets the ChromaDB database
  - `reset_db.sh`: Shell script for database reset
  - `fix_ingestion.py`: Fixes ingestion issues
  - `local_ingest.py`: Runs local ingestion process

- `tests/`: Scripts for testing EXASPERATION components
  - `test_api.sh`: Tests the API
  - `test_api_directly.py`: Tests the API directly (bypassing HTTP)
  - `test_query.py`: Tests the query engine
  - Various testing scripts for database functionality

- `utilities/`: Utility scripts for maintenance and operations

## Usage

Most scripts should be run from the project root directory, as they use relative paths from there. For example:

```bash
# Start all services
./scripts/run/start_all.sh

# Run the frontend
./scripts/run/run_frontend.sh

# Check database status
python ./scripts/db/check_chromadb.py
```

Many scripts have also been symlinked to the root directory for convenience.

## Script Design

All scripts are designed to:

1. Work with relative paths regardless of where they're called from
2. Provide clear output with color-coded messages
3. Include proper error handling
4. Check prerequisites before execution
5. Provide helpful guidance when errors occur

## Adding New Scripts

When adding new scripts, please follow these guidelines:

1. Place scripts in the appropriate subdirectory
2. Use the standard header and PROJECT_ROOT detection pattern
3. Include proper documentation in the script itself
4. Update this README if adding a new category of scripts