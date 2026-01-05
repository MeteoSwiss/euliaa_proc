#!/bin/bash
CONFIG=${HOME}/euliaa_proc/euliaa_proc/config/config_quicklooks_multi.yaml
while [[ "$#" -gt 0 ]]; do
    case $1 in
        --year) year="$2"; shift ;;
        --month) month="$2"; shift ;;
        --day) day="$2"; shift ;;
    esac
    shift
done

if [ -z "$year" ]; then
    year=$(date +%Y)
fi
if [ -z "$month" ]; then
    month=$(date +%m)
fi
if [ -z "$day" ]; then
    day=$(date +%d)
fi

date=${year}${month}${day}
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
    WIND_STR=$(yq ".campaign.$campaign[3].WIND_STR" "$CONFIG")
    BSC_STR=$(yq ".campaign.$campaign[4].BSC_STR" "$CONFIG")
    T_STR=$(yq ".campaign.$campaign[5].T_STR" "$CONFIG")
    MASK_FLAG=$(yq ".campaign.$campaign[6].MASK_FLAG" "$CONFIG")
    # Ensure L2A_DIR ends with a '/'
    if [[ "$L2A_DIR" != */ ]]; then
        L2A_DIR="${L2A_DIR}/"
    fi
    L2A_DIR_W_DATE=${L2A_DIR}${year}/${month}/${day}/
    file_list=$(s3cmd ls "${L2A_DIR_W_DATE}" 2>/dev/null | awk '{print $4}')
    # file_list=$(s3cmd ls "${L2A_DIR_W_DATE}L2A*${date}*" 2>/dev/null | awk '{print $4}')
    
    if [ -z "$file_list" ]; then
        echo "No L2A files found for date $date in $L2A_DIR_W_DATE, trying subdirectories..."
        file_list=$(s3cmd ls --recursive "${L2A_DIR}*" | grep "${year}/${month}/${day}" 2>/dev/null | awk '{print $4}')
        
    fi
    if [ -z "$file_list" ]; then
        echo "No L2A files found for date $date in $L2A_DIR_W_DATE or its subdirectories. Skipping campaign."
    else
        echo "$HOME/.env_euliaa/bin/python $HOME/euliaa_proc/euliaa_proc/quicklooks.py --l2a_file_list $file_list --fig_dir "$QUICKLOOKS_DIR" --fig_prefix ${FIG_PREFIX} --wind_str ${WIND_STR} --bsc_str ${BSC_STR} --T_str ${T_STR} --mask_flag ${MASK_FLAG}"
        $HOME/.env_euliaa/bin/python $HOME/euliaa_proc/euliaa_proc/quicklooks.py --l2a_file_list $file_list --fig_dir "$QUICKLOOKS_DIR" --fig_prefix ${FIG_PREFIX} --wind_str ${WIND_STR} --bsc_str ${BSC_STR} --T_str ${T_STR} --mask_flag ${MASK_FLAG}
        $HOME/.env_euliaa/bin/python $HOME/euliaa_proc/euliaa_proc/quicklooks_interactive.py --l2a_file_list $file_list --fig_dir "$QUICKLOOKS_DIR" --fig_prefix ${FIG_PREFIX} --wind_str ${WIND_STR} --bsc_str ${BSC_STR} --T_str ${T_STR} --mask_flag ${MASK_FLAG}
        if [ $? -ne 0 ]; then
            echo "  ✗ Error running quicklooks for $campaign"
        fi
    fi
    
    echo "----------------------------------------"
done

echo "All campaigns processed."
