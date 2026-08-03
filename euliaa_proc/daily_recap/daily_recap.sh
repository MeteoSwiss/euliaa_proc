#!/bin/bash

# Daily Recap Script for S3 Uploads
# Reports files uploaded to S3 buckets in the previous day

set -e

# Configuration
YESTERDAY=$(date -d "yesterday" +%Y-%m-%d)
# YESTERDAY=$(date +%Y-%m-%d)
FILE_RECAP="/home/oper/daily_recaps/daily_recap_${YESTERDAY}.txt"
FILE_RECAP_HTML="/home/oper/daily_recaps/daily_recap_${YESTERDAY}.html"
BUCKETS=("s3://euliaa-l1" "s3://euliaa-l2" "s3://euliaa-quicklooks/campaigns" "s3://euliaa-eprofile" "s3://euliaa-daily" "s3://euliaa-val" "s3://euliaa-val-gkh")
TMP_DIR=$(mktemp -d)

cleanup() {
    rm -rf "$TMP_DIR"
}

trap cleanup EXIT

get_bucket_cache_file() {
    local bucket=$1
    local safe_name
    safe_name=$(echo "$bucket" | sed 's|[^a-zA-Z0-9]|_|g')
    echo "${TMP_DIR}/${safe_name}.list"
}

html_escape() {
    local s="$1"
    s=${s//&/&amp;}
    s=${s//</&lt;}
    s=${s//>/&gt;}
    s=${s//\"/&quot;}
    s=${s//\'/&#39;}
    printf '%s' "$s"
}

# Function to get files uploaded yesterday from a bucket
get_yesterday_files() {
    local bucket=$1
    local date
    local filepath

    # Get list of all files with their last modified date
    s3cmd ls "${bucket}/" --recursive | while read -r line; do
        # Parse the s3cmd ls output (format: date time size filename)
        date=$(echo "$line" | awk '{print $1}')
        filepath=$(echo "$line" | awk '{for(i=4;i<=NF;i++) printf "%s%s", (i==4?"":" "), $i; print ""}')
        
        # Check if file was modified yesterday
        if [[ "$date" == "$YESTERDAY" ]]; then
            echo "$filepath"
        fi
    done
}

# Function to analyze and report files by campaign and subdirectory
analyze_bucket_txt() {
    local bucket=$1
    local cache_file=$2
    local files
    local normalized_files=""
    local total_files
    local campaign
    local subdir
    local filepath
    
    echo -e "ANALYZING BUCKET: ${bucket}"
    files=$(cat "$cache_file")

    # echo $files
    if [[ -z "$files" ]]; then
        echo -e "No files uploaded"
        echo ""
        return
    fi
    
    # Count total files
    total_files=$(echo "$files" | wc -l)
    echo -e "TOTAL FILES UPLOADED: ${total_files}"
    echo ""

    # if [[ "$total_files" -lt 4 ]]; then
    #     echo -e "Files uploaded yesterday:"
    #     echo "$files" | while read -r filepath; do
    #         echo -e "  - ${filepath}"
    #     done
    #     echo ""
    # else
    #     echo -e "Files uploaded yesterday (first 2 and last 1):"
    #     echo "$files" | head -n 2 | while read -r filepath; do
    #         echo -e "  - ${filepath}"
    #     done
    #     echo ""
    #     echo "$files" | tail -n 1 | while read -r filepath; do
    #         echo -e "  - ${filepath}"
    #     done
    #     echo ""
    # fi
    
    # Group by campaign (first level directory) and subdirectories
    # Create associative arrays for counting
    declare -A campaign_counts
    declare -A subdir_counts
    
    while IFS= read -r filepath; do
        # Strip bucket prefix if present (s3://bucket-name/)
        filepath=$(echo "$filepath" | sed "s|^${bucket}/||" | sed 's/^\s*//' | sed 's/\s*$//')
        
        # Skip empty lines
        [[ -z "$filepath" ]] && continue

        normalized_files+="${filepath}"$'\n'
        
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

    list_direct_files() {
        local target_subdir=$1
        while IFS= read -r filepath; do
            [[ -z "$filepath" ]] && continue
            if [[ "$(dirname "$filepath")" == "$target_subdir" ]]; then
                echo "$filepath"
            fi
        done <<< "$normalized_files"
    }
    
    # Sort and display results by campaign
    while IFS= read -r campaign; do
        echo -e "\nCampaign: ${campaign}"
        echo -e "  Total files: ${campaign_counts[$campaign]}"
        
        echo -e "  Subdirectories:"
        
        # Show subdirectories for this campaign
        while IFS= read -r subdir; do
            if [[ "$subdir" == "$campaign"* ]]; then
                echo -e "    - ${subdir}: ${subdir_counts[$subdir]} file(s)"
                if [[ ${subdir_counts[$subdir]} -lt 2 ]]; then
                    list_direct_files "$subdir" | while read -r filepath; do
                        echo -e "      - ${filepath}"
                    done
                else
                    # list_direct_files "$subdir" | head -n 2 | while read -r filepath; do
                    #     echo -e "      - ${filepath}"
                    # done
                    # echo "      ..."
                    list_direct_files "$subdir" | tail -n 1 | while read -r filepath; do
                        echo -e "...      - ${filepath}"
                    done
                fi
            fi
        done < <(printf '%s\n' "${!subdir_counts[@]}" | sort)
    done < <(printf '%s\n' "${!campaign_counts[@]}" | sort)
    
    echo ""
}

analyze_bucket_html() {
    local bucket=$1
    local cache_file=$2
    local files
    local normalized_files=""
    local total_files
    local campaign
    local subdir
    local filepath

    files=$(cat "$cache_file")

    echo "    <section class=\"bucket\">"
    echo "      <h2>Bucket: $(html_escape "$bucket")</h2>"

    if [[ -z "$files" ]]; then
        echo "      <p class=\"empty\">No files uploaded.</p>"
        echo "    </section>"
        return
    fi

    declare -A campaign_counts
    declare -A subdir_counts

    while IFS= read -r filepath; do
        filepath=$(echo "$filepath" | sed "s|^${bucket}/||" | sed 's/^\s*//' | sed 's/\s*$//')
        [[ -z "$filepath" ]] && continue

        normalized_files+="${filepath}"$'\n'

        campaign=$(echo "$filepath" | cut -d'/' -f1)
        subdir=$(dirname "$filepath")

        if [[ -n "$campaign" ]]; then
            campaign_counts["$campaign"]=$((${campaign_counts["$campaign"]:-0} + 1))
            subdir_counts["$subdir"]=$((${subdir_counts["$subdir"]:-0} + 1))
        fi
    done <<< "$files"

    list_direct_files() {
        local target_subdir=$1
        while IFS= read -r filepath; do
            [[ -z "$filepath" ]] && continue
            if [[ "$(dirname "$filepath")" == "$target_subdir" ]]; then
                echo "$filepath"
            fi
        done <<< "$normalized_files"
    }

    total_files=$(echo "$files" | wc -l)
    echo "      <p class=\"total\">Total files uploaded: <strong>${total_files}</strong></p>"

    while IFS= read -r campaign; do
        echo "      <details class=\"campaign\">"
        echo "        <summary>Campaign: $(html_escape "$campaign") (${campaign_counts[$campaign]} file(s))</summary>"

        while IFS= read -r subdir; do
            if [[ "$subdir" == "$campaign"* ]]; then
                echo "        <details class=\"subdir\">"
                echo "          <summary>$(html_escape "$subdir") (${subdir_counts[$subdir]} file(s))</summary>"
                echo "          <ul>"
                list_direct_files "$subdir" | while read -r filepath; do
                    echo "            <li>$(html_escape "$filepath")</li>"
                done
                echo "          </ul>"
                echo "        </details>"
            fi
        done < <(printf '%s\n' "${!subdir_counts[@]}" | sort)

        echo "      </details>"
    done < <(printf '%s\n' "${!campaign_counts[@]}" | sort)

    echo "    </section>"
}

# Process each bucket

for bucket in "${BUCKETS[@]}"; do
    get_yesterday_files "$bucket" > "$(get_bucket_cache_file "$bucket")"
done


{
    echo -e "============================================" 
    echo -e "Daily S3 Upload Recap for ${YESTERDAY}"
    echo -e "============================================"
    echo "" 
    echo ""

    for bucket in "${BUCKETS[@]}"; do
        analyze_bucket_txt "$bucket" "$(get_bucket_cache_file "$bucket")"
        echo -e "============================================"
        echo "" 
        echo "" 
    done

    echo -e "Recap complete!" 
} > "$FILE_RECAP"

{
    echo "<!DOCTYPE html>"
    echo "<html lang=\"en\">"
    echo "<head>"
    echo "  <meta charset=\"UTF-8\">"
    echo "  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\">"
    echo "  <title>Daily S3 Upload Recap - ${YESTERDAY}</title>"
    echo "  <style>"
    echo "    :root { color-scheme: light; }"
    echo "    body { margin: 0; padding: 24px; font-family: 'Segoe UI', Tahoma, sans-serif; background: #f4f6f8; color: #1f2933; }"
    echo "    .wrap { max-width: 1200px; margin: 0 auto; }"
    echo "    h1 { margin-top: 0; margin-bottom: 6px; font-size: 1.8rem; }"
    echo "    .date { margin-bottom: 22px; color: #52606d; }"
    echo "    .bucket { background: #fff; border: 1px solid #d9e2ec; border-radius: 10px; padding: 16px 18px; margin-bottom: 16px; box-shadow: 0 1px 2px rgba(16, 24, 40, 0.05); }"
    echo "    .bucket h2 { margin: 0 0 8px; font-size: 1.15rem; }"
    echo "    .total { margin: 0 0 12px; }"
    echo "    .empty { color: #7b8794; margin: 0; }"
    echo "    details { margin: 6px 0; }"
    echo "    summary { cursor: pointer; font-weight: 600; }"
    echo "    .subdir summary { font-weight: 500; }"
    echo "    ul { margin: 8px 0 10px 18px; padding: 0; }"
    echo "    li { margin: 2px 0; word-break: break-all; font-family: Consolas, 'Courier New', monospace; font-size: 0.92rem; }"
    echo "  </style>"
    echo "</head>"
    echo "<body>"
    echo "  <main class=\"wrap\">"
    echo "    <h2>Daily S3 Upload Recap</h2>"
    echo "    <p class=\"date\">Date analyzed: ${YESTERDAY}</p>"

    for bucket in "${BUCKETS[@]}"; do
        analyze_bucket_html "$bucket" "$(get_bucket_cache_file "$bucket")"
    done

    echo "  </main>"
    echo "</body>"
    echo "</html>"
} > "$FILE_RECAP_HTML"

s3cmd put "$FILE_RECAP" "s3://euliaa-recaps/"
s3cmd put "$FILE_RECAP_HTML" "s3://euliaa-recaps/"