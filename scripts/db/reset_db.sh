#!/bin/bash
# Script to reset the ChromaDB database with proper permissions

echo "Stopping ChromaDB container..."
docker compose stop chromadb

echo "Removing ChromaDB data directories..."
sudo rm -rf data/chromadb
sudo rm -rf data/chromadb_logs

echo "Creating fresh data directories with proper permissions..."
mkdir -p data/chromadb
mkdir -p data/chromadb_logs
chmod -R 777 data/chromadb
chmod -R 777 data/chromadb_logs

echo "Starting ChromaDB container..."
docker compose up -d chromadb

echo "Waiting for ChromaDB to be ready..."
sleep 5

echo "Checking container status..."
docker compose ps chromadb

echo "Done! ChromaDB is reset with proper permissions."