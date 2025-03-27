# EXASPERATION Run Scripts

This directory contains scripts used to run and control EXASPERATION services.

## Available Scripts

- `start_all.sh`: Starts all components (ChromaDB, API, Frontend, Caddy)
- `stop_all.sh`: Stops all components
- `start_api_server.sh`: Starts only the API server in the background
- `stop_api_server.sh`: Stops the API server
- `run_api.sh`: Runs the API server in the foreground
- `run_frontend.sh`: Runs the Streamlit frontend in the foreground
- `api_server_status.sh`: Checks the status of the API server

## Usage

These scripts should be run from the project root directory or via the symlinks in the root directory:

```bash
# Start all services
./scripts/run/start_all.sh
# or using symlink
./start_all.sh

# Run the frontend in foreground
./scripts/run/run_frontend.sh
```

## Design

All scripts are designed to:

1. Work with relative paths regardless of where they're called from
2. Provide clear output with color-coded messages
3. Include proper error handling
4. Check prerequisites before execution
