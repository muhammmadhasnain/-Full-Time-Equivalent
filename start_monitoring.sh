#!/bin/bash
# Start Local Monitoring System
# This script activates the virtual environment and starts the monitoring system

echo "Starting Local Monitoring System..."
echo "=================================="

# Check if virtual environment exists
if [ ! -f "venv/bin/activate" ]; then
    echo "ERROR: Virtual environment not found!"
    echo "Please create a virtual environment first:"
    echo "python -m venv venv"
    exit 1
fi

# Activate virtual environment
source venv/bin/activate

# Check if required packages are installed
python -c "import watchdog" >/dev/null 2>&1
if [ $? -ne 0 ]; then
    echo "ERROR: Required packages not installed!"
    echo "Please install dependencies:"
    echo "pip install -r requirements.txt"
    exit 1
fi

# Start the monitoring system
echo "Starting monitoring system..."
echo "Press Ctrl+C to stop monitoring"
echo ""
python src/monitor.py

echo ""
echo "Monitoring system stopped."