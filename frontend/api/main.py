"""Main entry point for EXASPERATION API."""

import os
import logging
import argparse
import uvicorn
from dotenv import load_dotenv

from src.config import APP_PORT, LOG_LEVEL

# Configure logging
logging_level = getattr(logging, LOG_LEVEL, logging.INFO)
logging.basicConfig(
    level=logging_level,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)


def start_api_server(host="0.0.0.0", port=APP_PORT):
    """Start the FastAPI server.
    
    Args:
        host: Host to bind to
        port: Port to bind to (defaults to APP_PORT from config)
    """
    # Import the FastAPI app
    from frontend.api.app import app
    
    logger.info(f"Starting EXASPERATION API server on {host}:{port}")
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="EXASPERATION API server")
    parser.add_argument(
        "--host", 
        type=str, 
        default="0.0.0.0", 
        help="API server host"
    )
    parser.add_argument(
        "--port", 
        type=int, 
        default=APP_PORT, 
        help=f"API server port (default: {APP_PORT})"
    )
    args = parser.parse_args()
    
    # Start API server
    start_api_server(host=args.host, port=args.port)