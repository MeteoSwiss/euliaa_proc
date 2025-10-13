#!/bin/bash
CONFIG=${HOME}/euliaa_proc/euliaa_proc/config/config_quicklooks_multi.yaml
date=$(date +%Y%m%d)

echo "Processing quicklooks for date: $date"
echo "Using config: $CONFIG"

# Check if config file exists
if [ ! -f "$CONFIG" ]; then
    echo "Error: Config file not found: $CONFIG"
    exit 1
fi

# Get all campaign names from the YAML file
campaigns=$(yq '.campaign | keys | .[]' "$CONFIG")
for campaign in $campaigns; do
    echo "Quicklooks for campaign: $campaign"
    
    # Extract L2A_DIR and QUICKLOOKS_DIR for this campaign
    L2A_DIR=$(yq ".campaign.$campaign[0].L2A_DIR" "$CONFIG")
    QUICKLOOKS_DIR=$(yq ".campaign.$campaign[1].QUICKLOOKS_DIR" "$CONFIG")
    FIG_PREFIX=$(yq ".campaign.$campaign[2].FIG_PREFIX" "$CONFIG")
    
    # Ensure L2A_DIR ends with a '/'
    if [[ "$L2A_DIR" != */ ]]; then
        L2A_DIR="${L2A_DIR}/"
    fi
    file_list=$(s3cmd ls "${L2A_DIR}L2A_${date}*" 2>/dev/null | awk '{print $4}')
    
    if [ -z "$file_list" ]; then
        echo "  No L2A files found for date $date in $L2A_DIR"
    else
       $HOME/.env_euliaa/bin/python $HOME/euliaa_proc/euliaa_proc/quicklooks.py --l2a_file_list $file_list --fig_dir "$QUICKLOOKS_DIR" --fig_prefix ${FIG_PREFIX}
        
        if [ $? -ne 0 ]; then
            echo "  ✗ Error running quicklooks for $campaign"
        fi
    fi
    
    echo "----------------------------------------"
done

echo "All campaigns processed."
