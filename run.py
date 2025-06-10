#!/usr/bin/env python
"""
Entry point for running the API service.
This script adds the current directory to the Python path,
allowing imports to work when running from the aibot directory.
"""

import os
import sys
import uvicorn

# Add the current directory to the Python path
sys.path.insert(0, os.path.abspath("."))

# Import settings
from config.settings import API_HOST, API_PORT

if __name__ == "__main__":
    print(f"Starting AI Database Query Bot at http://{API_HOST}:{API_PORT}")
    uvicorn.run(
        "app:app",
        host=API_HOST,
        port=API_PORT,
        reload=True
    ) 