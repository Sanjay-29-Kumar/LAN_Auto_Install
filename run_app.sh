#!/bin/bash

echo "========================================"
echo "  LAN Software Automation System"
echo "========================================"
echo
echo "Starting application..."
echo

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "ERROR: Python 3 is not installed"
    echo "Please install Python 3.8 or higher"
    exit 1
fi

# Check if required files exist
if [ ! -f "app.py" ]; then
    echo "ERROR: app.py not found"
    echo "Please make sure you're running this from the correct directory"
    exit 1
fi

# Install dependencies if needed
echo "Checking dependencies..."
pip3 install -r requirements.txt > /dev/null 2>&1

# Start the application
echo "Starting LAN Automation System..."
python3 app.py

if [ $? -ne 0 ]; then
    echo
    echo "ERROR: Application failed to start"
    echo "Please check the error messages above"
    read -p "Press Enter to continue..."
fi

echo
echo "Application closed." 