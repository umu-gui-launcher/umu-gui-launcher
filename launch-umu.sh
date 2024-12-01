#!/bin/bash

# Enable debug output
exec 1> >(tee -a "/tmp/umu-launcher.log")
exec 2>&1

echo "Starting UMU Launcher at $(date)"
echo "Current directory: $(pwd)"
echo "Script location: $0"

# Change to the project directory
cd "$(dirname "$0")"
echo "Changed to directory: $(pwd)"

# Make sure DISPLAY is set
if [ -z "$DISPLAY" ]; then
    export DISPLAY=:0
    echo "Set DISPLAY to :0"
else
    echo "DISPLAY is already set to: $DISPLAY"
fi

# Make sure PYTHONPATH includes the current directory
export PYTHONPATH="$PYTHONPATH:$(pwd)"
echo "PYTHONPATH set to: $PYTHONPATH"

# Launch the application
echo "Launching Python application..."
/usr/bin/python3 main.py "$@"
echo "Python application exited with code: $?"
