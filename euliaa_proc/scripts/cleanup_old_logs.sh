#!/bin/bash

# Script to remove log files older than 7 days and daily recaps older than 30 days.
# Usage: ./cleanup_old_logs.sh [path_to_logs_directory]

# Configuration
LOGS_DIR=/home/oper/euliaa_proc/euliaa_proc/logs  # Use argument or default to ./logs
DAYS_OLD=7
RECAPS_DIR=/home/oper/daily_recaps
DAYS_OLD_RECAPS=30

# Check if logs directory exists
if [ ! -d "$LOGS_DIR" ]; then
    echo "Error: Directory '$LOGS_DIR' does not exist."
    exit 1
fi
if [ ! -d "$RECAPS_DIR" ]; then
    echo "Error: Directory '$RECAPS_DIR' does not exist."
    exit 1
fi

echo "Cleaning up logs older than $DAYS_OLD days in: $LOGS_DIR"
# Find and delete old log files
echo -e "Files to be deleted:"
find "$LOGS_DIR" -type f -name "*.log*" -mtime +$DAYS_OLD -exec ls -lh {} \;
find "$LOGS_DIR" -type f -name "*.log*" -mtime +$DAYS_OLD -delete

echo "Cleaning up daily recaps older than $DAYS_OLD_RECAPS days in: $RECAPS_DIR"
# Find and delete old log files
echo -e "Files to be deleted:"
find "$RECAPS_DIR" -type f -name "*.log*" -mtime +$DAYS_OLD_RECAPS -exec ls -lh {} \;
find "$RECAPS_DIR" -type f -name "*.log*" -mtime +$DAYS_OLD_RECAPS -delete

echo "Cleanup completed!"
