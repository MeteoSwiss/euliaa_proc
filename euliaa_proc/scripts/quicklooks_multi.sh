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
    # Warning: This assumes the order of keys in the YAML file is consistent. If the order changes, this will break.
    L2A_DIR=$(yq ".campaign.$campaign[0].L2A_DIR" "$CONFIG")
    L1_DIR=$(yq ".campaign.$campaign[1].L1_DIR" "$CONFIG")
    QUICKLOOKS_DIR=$(yq ".campaign.$campaign[2].QUICKLOOKS_DIR" "$CONFIG")
    L1_QUICKLOOKS_DIR=$(yq ".campaign.$campaign[3].L1_QUICKLOOKS_DIR" "$CONFIG")
    FIG_PREFIX=$(yq ".campaign.$campaign[4].FIG_PREFIX" "$CONFIG")
    L1_FIG_PREFIX=$(yq ".campaign.$campaign[5].L1_FIG_PREFIX" "$CONFIG")
    WIND_STR=$(yq ".campaign.$campaign[6].WIND_STR" "$CONFIG")
    BSC_STR=$(yq ".campaign.$campaign[7].BSC_STR" "$CONFIG")
    T_STR=$(yq ".campaign.$campaign[8].T_STR" "$CONFIG")
    MASK_FLAG=$(yq ".campaign.$campaign[9].MASK_FLAG" "$CONFIG")
    # Ensure L2A_DIR ends with a '/'
    if [[ "$L2A_DIR" != */ ]]; then
        L2A_DIR="${L2A_DIR}/"
    fi
    # L2A_DIR_W_DATE=${L2A_DIR}${year}/${month}/${day}/
    # file_list=$(s3cmd ls "${L2A_DIR_W_DATE}" 2>/dev/null | awk '{print $4}')
    # # file_list=$(s3cmd ls "${L2A_DIR_W_DATE}L2A*${date}*" 2>/dev/null | awk '{print $4}')
    
    # if [ -z "$file_list" ]; then
    #     echo "No L2A files found for date $date in $L2A_DIR_W_DATE, trying subdirectories..."
    #     file_list=$(s3cmd ls --recursive "${L2A_DIR}*" | grep "${year}/${month}/${day}.*\.nc$" 2>/dev/null | awk '{print $4}')
        
    # fi

    file_list=$(s3cmd ls --recursive "${L2A_DIR}*" | grep "20MIN/${year}/${month}/${day}.*\.nc$" 2>/dev/null | awk '{print $4}')
    file_list_l1=$(ls ${L1_DIR}/EULIAA_L1_${year}-${month}-${day}*.h5)     # L1 files cannot be read directly from S3, so we use the path of the mounted bucket

    # echo "L2A files found: $file_list"
    # echo "L1 files found: $file_list_l1"

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
    
    if [ -z "$file_list_l1" ]; then
        echo "No L1 files found for date $date in $L1_DIR_W_DATE or its subdirectories. Skipping campaign."
    else
        $HOME/.env_euliaa/bin/python $HOME/euliaa_proc/euliaa_proc/quicklooks_signal.py --l1_file_list $file_list_l1 --fig_dir "$L1_QUICKLOOKS_DIR" --fig_prefix ${L1_FIG_PREFIX}
        $HOME/.env_euliaa/bin/python $HOME/euliaa_proc/euliaa_proc/quicklooks_signal_interactive.py --l1_file_list $file_list_l1 --fig_dir "$L1_QUICKLOOKS_DIR" --fig_prefix ${L1_FIG_PREFIX}
        if [ $? -ne 0 ]; then
            echo "  ✗ Error running quicklooks signal for $campaign"
        fi
    fi
    echo "----------------------------------------"
done

echo "All campaigns processed."
