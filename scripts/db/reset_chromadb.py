#!/usr/bin/env python3
"""
Reset the ChromaDB database completely by stopping the container,
cleaning up the data directory, and restarting the container.
"""

import os
import shutil
import subprocess
import logging
import time
from pathlib import Path

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def reset_chromadb():
    """Reset the ChromaDB database completely."""
    # Stop the Docker container
    logger.info("Stopping ChromaDB Docker container...")
    subprocess.run(["docker", "compose", "stop", "chromadb"], check=True)
    
    # Remove data directory using sudo to handle permission issues
    data_dir = Path("data/chromadb")
    if data_dir.exists():
        logger.info(f"Removing data directory: {data_dir}")
        
        try:
            # Use sudo rm to handle permission issues with Docker-created files
            logger.info("Using sudo to remove data directory (you may be prompted for password)")
            subprocess.run(["sudo", "rm", "-rf", str(data_dir)], check=True)
            logger.info("Successfully removed data directory")
        except subprocess.CalledProcessError as e:
            logger.error(f"Error removing data directory with sudo: {e}")
            logger.info("Falling back to manual removal...")
            
            try:
                # Alternative: use chmod to fix permissions first
                subprocess.run(["sudo", "chmod", "-R", "777", str(data_dir)], check=False)
                
                # Then try manual removal
                for file_path in data_dir.glob("**/*"):
                    if file_path.is_file():
                        try:
                            file_path.unlink()
                        except Exception as e:
                            logger.warning(f"Could not remove file {file_path}: {e}")
                
                # Try to rmdir all directories
                for dir_path in sorted(data_dir.glob("**/*"), reverse=True):
                    if dir_path.is_dir():
                        try:
                            dir_path.rmdir()
                        except OSError as e:
                            logger.warning(f"Could not remove directory {dir_path}: {e}")
                
                # Try to remove main directory
                try:
                    data_dir.rmdir()
                except OSError as e:
                    logger.warning(f"Could not remove main directory {data_dir}: {e}")
            except Exception as e:
                logger.error(f"Error during manual removal: {e}")
    
    # Create fresh data directory
    logger.info("Creating fresh data directory...")
    data_dir.mkdir(parents=True, exist_ok=True)
    
    # Start the container
    logger.info("Starting ChromaDB Docker container...")
    subprocess.run(["docker", "compose", "up", "-d", "chromadb"], check=True)
    
    # Wait for it to be ready
    logger.info("Waiting for ChromaDB to be ready...")
    time.sleep(5)
    
    # Verify it's running
    try:
        output = subprocess.check_output(["docker", "compose", "ps", "chromadb"])
        logger.info(f"ChromaDB container status: {output.decode().strip()}")
    except subprocess.CalledProcessError as e:
        logger.error(f"Error checking container status: {e}")
    
    logger.info("ChromaDB reset complete!")

if __name__ == "__main__":
    reset_chromadb()