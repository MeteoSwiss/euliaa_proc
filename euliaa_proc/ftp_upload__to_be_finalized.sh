#!/bin/bash

# Production FTP Upload Script
# Usage: ./ftp_upload_production.sh /path/to/file.txt [remote_filename]

# Exit on any error
set -e

# Configuration - Load environment variables + FTP credentials 
PROJECT_DIR=${HOME}/euliaa_proc/euliaa_proc/
CONFIG_FILE=${PROJECT_DIR}/config/credentials_ftp.yaml
source ${CONFIG_FILE}

# Logging
LOG_FILE="${LOG_FILE:-${PROJECT_DIR}/logs/ftp_upload.log}"
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')

# Function to log messages
log_message() {
    echo "[$TIMESTAMP] $1" | tee -a "$LOG_FILE"
}

# Function to upload file
upload_file() {
    local local_file="$1"
    local remote_file="$2"
    
    # Validate input
    if [[ ! -f "$local_file" ]]; then
        log_message "ERROR: Local file '$local_file' not found"
        return 1
    fi
    
    # Set remote filename
    if [[ -z "$remote_file" ]]; then
        remote_file=$(basename "$local_file")
    fi
    
    log_message "Starting upload: $local_file -> ftp://$FTP_HOST$REMOTE_DIR$remote_file"
    
    # Upload with curl
    if curl -u "$FTP_USER:$FTP_PASS" \
           -T "$local_file" \
           "ftp://$FTP_HOST:$FTP_PORT$REMOTE_DIR$remote_file" \
           --connect-timeout 30 \
           --max-time 300 \
           --silent \
           --show-error; then
        log_message "SUCCESS: File uploaded successfully"
        return 0
    else
        log_message "ERROR: Upload failed"
        return 1
    fi
}

# Main execution
main() {
    # Check arguments
    if [[ $# -lt 1 ]]; then
        echo "Usage: $0 <local_file> [remote_filename]"
        echo ""
        echo "Environment variables: stored in ${CONFIG_FILE}"
    fi
    
    local_file="$1"
    remote_file="$2"
    
    # Create log directory if needed
    mkdir -p "$(dirname "$LOG_FILE")"
    
    # Upload file
    if upload_file "$local_file" "$remote_file"; then
        exit 0
    else
        exit 1
    fi
}

# Run main function
main "$@"