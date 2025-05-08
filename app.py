#!/usr/bin/env python3
"""
College Housing Platform - Main Entry Point

This file serves as the primary entry point for the College Housing Platform application.
It redirects to the actual server implementation in src/server.py.
"""

import os
import sys

# Add the src directory to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

if __name__ == "__main__":
    try:
        # Import and run the server from src directory
        from src.server import app
        
        # Get port from environment or use default
        port = int(os.environ.get("PORT", 5000))
        
        print(f"Starting College Housing Platform on port {port}...")
        print("Visit http://localhost:{} in your browser".format(port))
        
        # Run the Flask application
        app.run(host="0.0.0.0", port=port, debug=True)
    except ImportError as e:
        print(f"Error importing server module: {e}")
        print("Make sure you have installed all requirements:")
        print("pip install -r requirements.txt")
        sys.exit(1)
    except Exception as e:
        print(f"Error starting server: {e}")
        sys.exit(1) 