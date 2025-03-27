#!/usr/bin/env python3
"""
Entry point for running the EXASPERATION frontend.
This script sets up the proper Python path and runs the Streamlit app.
"""

import os
import sys
from streamlit.web.cli import main as stcli_main

if __name__ == "__main__":
    # Add the project root to the Python path
    sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
    
    # Set environment variable for Streamlit module search path
    os.environ["PYTHONPATH"] = os.path.abspath(os.path.dirname(__file__))
    
    # Get the absolute path to the app.py file
    app_path = os.path.join(os.path.dirname(__file__), "frontend", "app.py")
    
    # Run the Streamlit app
    sys.argv = ["streamlit", "run", app_path]
    sys.exit(stcli_main())