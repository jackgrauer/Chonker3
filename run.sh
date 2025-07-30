#!/bin/bash

# Chonker3 run script - ensures the app stays open
# Uses the virtual environment and runs in background

cd "$(dirname "$0")"

# Ensure virtual environment exists
if [ ! -d ".venv" ]; then
    echo "Virtual environment not found. Creating with uv..."
    uv venv .venv
    uv pip install docling
    
    # Install optional OCR preprocessing dependencies
    echo "Installing OCR preprocessing dependencies..."
    uv pip install opencv-python-headless pdf2image pillow img2pdf numpy
else
    # Ensure docling is installed
    if ! .venv/bin/python -c "import docling" 2>/dev/null; then
        echo "Installing docling..."
        uv pip install docling
    fi
    
    # Check for OCR preprocessing dependencies
    if ! .venv/bin/python -c "import cv2" 2>/dev/null; then
        echo "Installing OCR preprocessing dependencies..."
        uv pip install opencv-python-headless pdf2image pillow img2pdf numpy
    fi
fi

# Build the Rust app
echo "Building Chonker3..."
cargo build --release

# Run in background and disown
echo "Starting Chonker3..."
nohup cargo run --release > chonker3.log 2>&1 &
PID=$!
disown $PID

echo "Chonker3 started with PID $PID"
echo "Logs available at: chonker3.log"
echo "To stop: kill $PID"