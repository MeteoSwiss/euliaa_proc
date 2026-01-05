#!/bin/bash

# Daily Recap Script for S3 Uploads
# Reports files uploaded to S3 buckets in the previous day

set -e

# Configuration
YESTERDAY=$(date -d "yesterday" +%Y-%m-%d)
# YESTERDAY=$(date +%Y-%m-%d)
FILE_RECAP="/home/oper/daily_recaps/daily_recap_${YESTERDAY}.txt"
BUCKETS=("s3://euliaa-l1" "s3://euliaa-l2" "s3://euliaa-quicklooks/campaigns" "s3://euliaa-eprofile" "s3://euliaa-daily" "s3://euliaa-val" "s3://euliaa-val-gkh")

# Function to get files uploaded yesterday from a bucket
get_yesterday_files() {
    local bucket=$1
    # Get list of all files with their last modified date
    s3cmd ls "${bucket}/" --recursive | while read -r line; do
        # Parse the s3cmd ls output (format: date time size filename)
        date=$(echo "$line" | awk '{print $1}')
        filepath=$(echo "$line" | awk '{for(i=4;i<=NF;i++) printf "%s ", $i; print ""}')
        
        # Check if file was modified yesterday
        if [[ "$date" == "$YESTERDAY" ]]; then
            echo "$filepath"
        fi
    done
}

# Function to analyze and report files by campaign and subdirectory
analyze_bucket() {
    local bucket=$1
    
    echo -e "ANALYZING BUCKET: ${bucket}"
    # Get all files from yesterday
    files=$(get_yesterday_files "$bucket")

    # echo $files
    if [[ -z "$files" ]]; then
        echo -e "No files uploaded yesterday"
        echo ""
        return
    fi
    
    # Count total files
    total_files=$(echo "$files" | wc -l)
    echo -e "TOTAL FILES UPLOADED: ${total_files}"
    echo ""
    
    # Group by campaign (first level directory) and subdirectories
    # Create associative arrays for counting
    declare -A campaign_counts
    declare -A subdir_counts
    
    while IFS= read -r filepath; do
        # Strip bucket prefix if present (s3://bucket-name/)
        filepath=$(echo "$filepath" | sed "s|^${bucket}/||" | sed 's/^\s*//' | sed 's/\s*$//')
        
        # Skip empty lines
        [[ -z "$filepath" ]] && continue
        
        # Extract campaign (first directory)
        campaign=$(echo "$filepath" | cut -d'/' -f1)
        
        # Extract subdirectory path (everything up to the filename)
        subdir=$(dirname "$filepath")
        
        if [[ -n "$campaign" ]]; then
            # Count files per campaign
            campaign_counts["$campaign"]=$((${campaign_counts["$campaign"]:-0} + 1))
            
            # Count files per subdirectory
            subdir_counts["$subdir"]=$((${subdir_counts["$subdir"]:-0} + 1))
        fi
    done <<< "$files"
    
    # Sort and display results by campaign
    for campaign in "${!campaign_counts[@]}"; do
        echo -e "\nCampaign: ${campaign}"
        echo -e "  Total files: ${campaign_counts[$campaign]}"
        
        echo -e "  Subdirectories:"
        
        # Show subdirectories for this campaign
        for subdir in "${!subdir_counts[@]}"; do
            if [[ "$subdir" == "$campaign"* ]]; then
                echo -e "    - ${subdir}: ${subdir_counts[$subdir]} file(s)"
            fi
        done
    done # | sort
    
    echo ""
}

# Process each bucket


{
    echo -e "============================================" 
    echo -e "Daily S3 Upload Recap for ${YESTERDAY}"
    echo -e "============================================"
    echo "" 
    echo ""

    for bucket in "${BUCKETS[@]}"; do
        analyze_bucket "$bucket" 
        echo -e "============================================"
        echo "" 
        echo "" 
    done

    echo -e "Recap complete!" 
} > "$FILE_RECAP"
