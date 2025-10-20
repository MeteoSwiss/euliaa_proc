#!/bin/bash

# Script to remove log files older than 1 month (30 days)
# Usage: ./cleanup_old_logs.sh [path_to_logs_directory]

# Configuration
LOGS_DIR="${1:-./logs}"  # Use argument or default to ./logs
DAYS_OLD=7

# Check if logs directory exists
if [ ! -d "$LOGS_DIR" ]; then
    echo "Error: Directory '$LOGS_DIR' does not exist."
    exit 1
fi

echo "Cleaning up logs older than $DAYS_OLD days in: $LOGS_DIR"

# Find and delete old log files
echo -e "Files to be deleted:"
find "$LOGS_DIR" -type f -name "*.log*" -mtime +$DAYS_OLD -exec ls -lh {} \;

find "$LOGS_DIR" -type f -name "*.log*" -mtime +$DAYS_OLD -delete

echo "Cleanup completed!"
