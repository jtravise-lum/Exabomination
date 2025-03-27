#!/bin/bash
# Script to stop the EXASPERATION API server

PID_FILE="api_server.pid"

# Check if PID file exists
if [ ! -f "$PID_FILE" ]; then
    echo "API server is not running (no PID file found)"
    exit 0
fi

# Get the PID
PID=$(cat "$PID_FILE")

# Check if process exists
if ! ps -p "$PID" > /dev/null; then
    echo "API server is not running (PID $PID not found)"
    rm "$PID_FILE"
    exit 0
fi

# Stop the process gracefully
echo "Stopping API server (PID $PID)..."
kill "$PID"

# Wait for process to terminate
MAX_WAIT=30
COUNT=0
while ps -p "$PID" > /dev/null && [ $COUNT -lt $MAX_WAIT ]; do
    echo "Waiting for API server to shut down..."
    sleep 1
    COUNT=$((COUNT + 1))
done

# If it's still running after waiting, force kill
if ps -p "$PID" > /dev/null; then
    echo "Force killing API server (PID $PID)..."
    kill -9 "$PID"
    sleep 1
fi

# Remove PID file
rm "$PID_FILE"
echo "API server stopped successfully"