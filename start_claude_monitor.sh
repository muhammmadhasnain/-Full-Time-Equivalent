#!/bin/bash
# Start Claude Code Monitoring System
# This script activates the virtual environment and starts Claude Code monitoring

echo "Starting Claude Code Monitoring System..."
echo "======================================"

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

# Start the Claude Code monitoring system
echo "Starting Claude Code monitoring..."
echo "Press Ctrl+C to stop monitoring"
echo ""
python src/claude_code_monitor.py

echo ""
echo "Claude Code monitoring stopped."