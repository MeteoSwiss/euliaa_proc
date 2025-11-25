#!/bin/bash

# daily_concat_runner.sh - Concatenate daily NetCDF files (default: of the previous day) from S3 bucket
# Usage: ./daily_concat_runner.sh [YYYYMMDD] [options]

# Should be put in crontab to activate concatenation + upload to s3 bucket for GEO knowledgehub
# ./euliaa_proc/euliaa_proc/scripts/daily_concat_runner.sh -b s3://euliaa-l2/TESTS/Kuehlungsborn/L2A/ -o s3://euliaa-daily/Kuehlungsborn/ -t 20MIN -c euliaa_proc/euliaa_proc/config/config_qc_w_correction.yaml 
# ./euliaa_proc/euliaa_proc/scripts/daily_concat_runner.sh -b s3://euliaa-l2/TESTS/Kuehlungsborn/L2A/ -o s3://euliaa-daily/Kuehlungsborn/ -t 60MIN -c euliaa_proc/euliaa_proc/config/config_qc_w_correction.yaml 
# ./euliaa_proc/euliaa_proc/scripts/daily_concat_runner.sh -b s3://euliaa-l2/Andoya/L2A/ -o s3://euliaa-daily/Andoya/ -t 20MIN -c euliaa_proc/euliaa_proc/config/config_qc_w_correction.yaml 
# ./euliaa_proc/euliaa_proc/scripts/daily_concat_runner.sh -b s3://euliaa-l2/Andoya/L2A/ -o s3://euliaa-daily/Andoya/ -t 60MIN -c euliaa_proc/euliaa_proc/config/config_qc_w_correction.yaml 
# ./euliaa_proc/euliaa_proc/scripts/daily_concat_runner.sh -b s3://euliaa-l2/OHP/L2A/ -o s3://euliaa-daily/OHP/ -t 20MIN -c euliaa_proc/euliaa_proc/config/config_qc_w_correction.yaml
# ./euliaa_proc/euliaa_proc/scripts/daily_concat_runner.sh -b s3://euliaa-l2/OHP/L2A/ -o s3://euliaa-daily/OHP/ -t 60MIN -c euliaa_proc/euliaa_proc/config/config_qc_w_correction.yaml
# ./euliaa_proc/euliaa_proc/scripts/daily_concat_runner.sh -b s3://euliaa-l2/Jungfraujoch/L2A/ -o s3://euliaa-daily/Jungfraujoch/ -t 20MIN -c euliaa_proc/euliaa_proc/config/config_qc_w_correction.yaml
# ./euliaa_proc/euliaa_proc/scripts/daily_concat_runner.sh -b s3://euliaa-l2/Jungfraujoch/L2A/ -o s3://euliaa-daily/Jungfraujoch/ -t 60MIN -c euliaa_proc/euliaa_proc/config/config_qc_w_correction.yaml
# ./euliaa_proc/euliaa_proc/scripts/daily_concat_runner.sh -b s3://euliaa-l2/Payerne/L2A/ -o s3://euliaa-daily/Payerne/ -t 20MIN -c euliaa_proc/euliaa_proc/config/config_qc_w_correction.yaml
# ./euliaa_proc/euliaa_proc/scripts/daily_concat_runner.sh -b s3://euliaa-l2/Payerne/L2A/ -o s3://euliaa-daily/Payerne/ -t 60MIN -c euliaa_proc/euliaa_proc/config/config_qc_w_correction.yaml
# ./euliaa_proc/euliaa_proc/scripts/daily_concat_runner.sh -b s3://euliaa-l2/Maido/L2A/ -o s3://euliaa-daily/Maido/ -t 20MIN -c euliaa_proc/euliaa_proc/config/config_qc_w_correction.yaml
# ./euliaa_proc/euliaa_proc/scripts/daily_concat_runner.sh -b s3://euliaa-l2/Maido/L2A/ -o s3://euliaa-daily/Maido/ -t 60MIN -c euliaa_proc/euliaa_proc/config/config_qc_w_correction.yaml



set -e  # Exit on any error
source /home/oper/.env_euliaa/bin/activate

# Default values
S3_BUCKET="s3://euliaa-l2"
OUTPUT_BUCKET="s3://euliaa-daily"
VERBOSE=""
DRY_RUN=false

# Function to display usage
usage() {
    echo "Usage: $0 [YYYYMMDD] [OPTIONS]"
    echo ""
    echo "Cconcatenate NetCDF files for a specific date"
    echo ""
    echo "Arguments:"
    echo "  YYYYMMDD          Date in YYYYMMDD format (default: yesterday's date)"
    echo ""
    echo "Options:"
    echo "  -b, --bucket BUCKET      Source S3 bucket directory (default: s3://euliaa-l2)"
    echo "  -o, --output BUCKET      Output S3 bucket directory (default: s3://euliaa-l2/DAILY)"
    echo "  -v, --verbose            Enable verbose output"
    echo "  -d, --dry-run            Show what would be done without executing"
    echo "  -t, --time_integration   Time integration (e.g., 20MIN, 60MIN) (default: '')"
    echo "  -c, --config FILE        Path to configuration file (config_qc containing VARIABLES_TO_KEEP_DAILY)"
    echo "  -h, --help               Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0                    # Process yesterday's data"
    echo "  $0 2024-01-15          # Process specific date"
    echo "  $0 2024-01-15 --verbose"
    echo "  $0 --dry-run         # Dry run for yesterday's data"
    echo "  $0 2024-01-15 --dry-run"
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
    DATE=$(date -d "yesterday" +%Y-%m-%d)
    log "No date specified, using yesterday's date: $DATE"
else
    # First argument is the date
    DATE="$1"
    shift
fi

while [[ $# -gt 0 ]]; do
    case $1 in
        -c|--config)
            CONFIG_FILE="$2"
            shift 2
            ;;
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
        -t|--time_integration)
            TIME_INTEGRATION="$2"
            shift 2
            ;;
        --campaign)
            CAMPAIGN="$2"
            shift 2
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
S3_BUCKET=${S3_BUCKET}/${TIME_INTEGRATION}
S3_BUCKET="${S3_BUCKET%/}"
OUTPUT_BUCKET="${OUTPUT_BUCKET%/}"

[ -n "$CAMPAIGN" ] && CAMPAIGN="${CAMPAIGN}_"

log "Starting daily concatenation for date: $DATE"
log "Source bucket: $S3_BUCKET"
log "Output bucket: $OUTPUT_BUCKET"

# Use s3cmd ls to find files
S3CMD="s3cmd ls $S3_BUCKET/ --recursive"
echo $S3CMD
# Get list of files matching the date pattern
FILES_LIST=$(eval "$S3CMD" | grep "\.nc$" | grep "_${DATE}_" | awk '{print $4}')
if [ -z "$FILES_LIST" ]; then
    log "ERROR: No NetCDF files found for date $DATE"
    exit 1
fi

OUTPUT_FILE="$OUTPUT_BUCKET/L2A${TIME_INTEGRATION}_${CAMPAIGN}${DATE}.nc"


if [ "$DRY_RUN" = true ]; then
    log "DRY RUN - Would process the following files:"
    echo "$FILES_LIST"
    log "Output would be: ${OUTPUT_FILE}"
    exit 0
fi

# Display files to be processed
log "Files to be concatenated:"
echo "$FILES_LIST" | while read -r file; do
    echo "  - $file"
done

# Prepare output path

# Find the daily_concat.py script
CONCAT_SCRIPT="$HOME/euliaa_proc/euliaa_proc/daily_concat.py"

# Convert file list to space-separated arguments
FILES_ARGS=$(echo "$FILES_LIST" | tr '\n' ' ')

# Build the command
CONCAT_CMD="python $CONCAT_SCRIPT $FILES_ARGS --output $OUTPUT_FILE $VERBOSE --config $CONFIG_FILE"

# Execute the concatenation
if eval "$CONCAT_CMD"; then
    log "SUCCESS: Daily concatenation completed, Output file: $OUTPUT_FILE"
    
    # Check if output file exists
    CHECK_CMD="s3cmd ls $OUTPUT_FILE"
    
    if eval "$CHECK_CMD" >/dev/null 2>&1; then
        FILE_SIZE=$(eval "$CHECK_CMD" | awk '{print $3}')
        log "Output file size: $FILE_SIZE bytes"
    else
        log "ERROR: Output file not found after concatenation"
        exit 1
    fi
else
    log "ERROR: Concatenation failed"
    exit 1
fi
