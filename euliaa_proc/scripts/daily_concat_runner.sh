#!/bin/bash

# daily_concat_runner.sh - Concatenate daily NetCDF files (default: of the previous day) from S3 bucket
# Usage: ./daily_concat_runner.sh [YYYYMMDD] [options]

# Should be put in crontab to activate concatenation + upload to s3 bucket for GEO knowledgehub
#  ./euliaa_proc/euliaa_proc/daily_concat_runner.sh -b s3://euliaa-l2/Kuehlungsborn/ -o s3://euliaa-l2/DAILY/Kuehlungsborn/
#  ./euliaa_proc/euliaa_proc/daily_concat_runner.sh -b s3://euliaa-l2/Andoya/ -o s3://euliaa-l2/DAILY/Andoya/
#  ./euliaa_proc/euliaa_proc/daily_concat_runner.sh -b s3://euliaa-l2/OHP/ -o s3://euliaa-l2/DAILY/OHP/
#  ./euliaa_proc/euliaa_proc/daily_concat_runner.sh -b s3://euliaa-l2/Jungfraujoch/ -o s3://euliaa-l2/DAILY/Jungfraujoch/
#  ./euliaa_proc/euliaa_proc/daily_concat_runner.sh -b s3://euliaa-l2/Payerne/ -o s3://euliaa-l2/DAILY/Payerne/
#  ./euliaa_proc/euliaa_proc/daily_concat_runner.sh -b s3://euliaa-l2/Maido/ -o s3://euliaa-l2/DAILY/Maido/


set -e  # Exit on any error

# Default values
S3_BUCKET="s3://euliaa-l2"
OUTPUT_BUCKET="s3://euliaa-l2/DAILY"
VERBOSE=""
DRY_RUN=false

# Function to display usage
usage() {
    echo "Usage: $0 [YYYYMMDD] [OPTIONS]"
    echo ""
    echo "Process and concatenate NetCDF files for a specific date"
    echo ""
    echo "Arguments:"
    echo "  YYYYMMDD          Date in YYYYMMDD format (default: yesterday's date)"
    echo ""
    echo "Options:"
    echo "  -b, --bucket BUCKET      Source S3 bucket (default: s3://euliaa-l2)"
    echo "  -o, --output BUCKET      Output S3 bucket (default: s3://euliaa-l2/DAILY)"
    echo "  -v, --verbose            Enable verbose output"
    echo "  -d, --dry-run            Show what would be done without executing"
    echo "  -h, --help               Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0                    # Process yesterday's data"
    echo "  $0 20240115          # Process specific date"
    echo "  $0 20240115 --verbose"
    echo "  $0 --dry-run         # Dry run for yesterday's data"
    echo "  $0 20240115 --dry-run"
    exit 1
}

# Function to log messages
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"
}

# Parse command line arguments
# Check if first argument is a date (8 digits) or an option
if [ $# -eq 0 ] || [[ "$1" == -* ]]; then
    # No date provided or first arg is an option, use yesterday's date
    DATE=$(date -d "yesterday" +%Y%m%d)
    log "No date specified, using yesterday's date: $DATE"
else
    # First argument is the date
    DATE="$1"
    shift
fi

while [[ $# -gt 0 ]]; do
    case $1 in
        -b|--bucket)
            S3_BUCKET="$2"
            shift 2
            ;;
        -o|--output)
            OUTPUT_BUCKET="$2"
            shift 2
            ;;
        -v|--verbose)
            VERBOSE="--verbose"
            shift
            ;;
        -d|--dry-run)
            DRY_RUN=true
            shift
            ;;
        -h|--help)
            usage
            ;;
        *)
            echo "Unknown option: $1"
            usage
            ;;
    esac
done

# Normalize bucket paths - remove trailing slashes
S3_BUCKET="${S3_BUCKET%/}"
OUTPUT_BUCKET="${OUTPUT_BUCKET%/}"

log "Starting daily concatenation for date: $DATE"
log "Source bucket: $S3_BUCKET"
log "Output bucket: $OUTPUT_BUCKET"

# Use s3cmd ls to find files
S3CMD="s3cmd ls $S3_BUCKET/ --recursive"

# Get list of files matching the date pattern
FILES_LIST=$(eval "$S3CMD" | grep "\.nc$" | grep "$DATE" | awk '{print $4}')

if [ -z "$FILES_LIST" ]; then
    log "ERROR: No NetCDF files found for date $DATE"
    exit 1
fi

# Count files
FILE_COUNT=$(echo "$FILES_LIST" | wc -l)
log "Found $FILE_COUNT NetCDF files for date $DATE"

if [ "$DRY_RUN" = true ]; then
    log "DRY RUN - Would process the following files:"
    echo "$FILES_LIST"
    log "Output would be: $OUTPUT_BUCKET/L2A_$DATE.nc"
    exit 0
fi

# Display files to be processed
log "Files to be concatenated:"
echo "$FILES_LIST" | while read -r file; do
    echo "  - $file"
done

# Prepare output path
OUTPUT_FILE="$OUTPUT_BUCKET/L2A_$DATE.nc"

# Find the daily_concat.py script
# SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONCAT_SCRIPT="$HOME/euliaa_proc/euliaa_proc/daily_concat.py"

# if [ ! -f "$CONCAT_SCRIPT" ]; then
#     # Try alternative locations
#     if [ -f "$(dirname "$SCRIPT_DIR")/euliaa_proc/daily_concat.py" ]; then
#         CONCAT_SCRIPT="$(dirname "$SCRIPT_DIR")/euliaa_proc/daily_concat.py"
#     elif [ -f "euliaa_proc/daily_concat.py" ]; then
#         CONCAT_SCRIPT="euliaa_proc/daily_concat.py"
#     else
#         log "ERROR: Cannot find daily_concat.py script"
#         exit 1
#     fi
# fi

log "Using concatenation script: $CONCAT_SCRIPT"

# Run the concatenation
log "Starting concatenation process..."

# Convert file list to space-separated arguments
FILES_ARGS=$(echo "$FILES_LIST" | tr '\n' ' ')

# Build the command
CONCAT_CMD="python $CONCAT_SCRIPT $FILES_ARGS --output $OUTPUT_FILE $VERBOSE"

# Execute the concatenation
if eval "$CONCAT_CMD"; then
    log "SUCCESS: Daily concatenation completed, Output file: $OUTPUT_FILE"
    
    # Check if output file exists
    CHECK_CMD="s3cmd ls $OUTPUT_FILE"
    
    if eval "$CHECK_CMD" >/dev/null 2>&1; then
        FILE_SIZE=$(eval "$CHECK_CMD" | awk '{print $3}')
        log "Output file size: $FILE_SIZE bytes"
    fi
else
    log "ERROR: Concatenation failed"
    exit 1
fi

log "Process completed successfully"