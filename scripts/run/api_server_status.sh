#!/bin/bash
# Script to check the status of the EXASPERATION API server

PID_FILE="api_server.pid"
API_LOG_DIR="logs"
API_LOG_FILE="api_server.log"

# Check if API server is running
if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE")
    if ps -p "$PID" > /dev/null; then
        echo "API server status: RUNNING"
        echo "PID: $PID"
        echo "Process info:"
        ps -p "$PID" -o pid,ppid,cmd,%cpu,%mem,start,etime
        
        # Check if the server is responding
        API_HOST=$(hostname -I | awk '{print $1}')
        API_PORT=8080
        HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "http://$API_HOST:$API_PORT/health" 2>/dev/null)
        
        if [ "$HTTP_CODE" == "200" ]; then
            echo "API endpoint health check: OK (HTTP 200)"
        else
            echo "API endpoint health check: FAIL (HTTP $HTTP_CODE or no response)"
            echo "The process is running but the API may not be responding correctly."
            echo "Check the logs for more information."
        fi
        
        # Show recent logs
        if [ -f "$API_LOG_DIR/$API_LOG_FILE" ]; then
            echo ""
            echo "Recent logs (last 10 lines):"
            tail -n 10 "$API_LOG_DIR/$API_LOG_FILE"
            echo ""
            echo "For full logs, run: tail -f $API_LOG_DIR/$API_LOG_FILE"
        else
            echo "Log file not found at $API_LOG_DIR/$API_LOG_FILE"
        fi
    else
        echo "API server status: NOT RUNNING (stale PID file)"
        echo "PID file exists but process $PID is not running."
        echo "You can remove the stale PID file with: rm $PID_FILE"
    fi
else
    echo "API server status: NOT RUNNING (no PID file)"
    echo "To start the server, run: ./start_api_server.sh"
fi

# Show help
echo ""
echo "Available commands:"
echo "  - Start API server: ./start_api_server.sh"
echo "  - Stop API server:  ./stop_api_server.sh"
echo "  - Check status:     ./api_server_status.sh"