#!/bin/bash

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
BACKEND_DIR="$SCRIPT_DIR/../backend"

# Change to backend directory
cd "$BACKEND_DIR"

# Start the backend using uvicorn directly
export PYTHONPATH="$BACKEND_DIR:$PYTHONPATH"
uvicorn app.main:app --host 0.0.0.0 --port 8000