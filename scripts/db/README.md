# EXASPERATION Database Scripts

This directory contains scripts for database management, maintenance, and troubleshooting.

## Available Scripts

- `check_chromadb.py`: Checks ChromaDB connection and status
- `check_collection.py`: Examines a specific collection
- `check_count.py`: Counts documents in collections
- `check_db.py`: General database checks
- `check_db_size.py`: Checks database size
- `check_all_collections.py`: Checks all collections
- `reset_chromadb.py`: Resets the ChromaDB database
- `reset_db.sh`: Shell script for database reset
- `fix_ingestion.py`: Fixes ingestion issues
- `local_ingest.py`: Runs local ingestion process

## Usage

Python scripts should be run with Python from the project root directory:

```bash
# Check ChromaDB connection and status
python scripts/db/check_chromadb.py

# Reset the database
./scripts/db/reset_db.sh
```

## ChromaDB

Most of these scripts interact with the ChromaDB vector database. Make sure ChromaDB is running before using these scripts. The database can be started using:

```bash
# Start all services including ChromaDB
./scripts/run/start_all.sh

# Or start just Docker services if using Docker
docker compose up -d
```

## Data Location

The ChromaDB data is stored in the `/data/chromadb/` directory by default. Backups are stored in `/data/chromadb.backup/`.
