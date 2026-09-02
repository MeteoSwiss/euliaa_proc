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

    file_list=$(s3cmd ls --recursive "${L2A_DIR}*" | grep "MIN/${year}/${month}/${day}.*\.nc$" 2>/dev/null | awk '{print $4}')
    file_list_l1=$(ls ${L1_DIR}/EULIAA_L1_${year}-${month}-${day}*.h5)     # L1 files cannot be read directly from S3, so we use the path of the mounted bucket

    # echo "L2A files found: $file_list"
    # echo "L1 files found: $file_list_l1"

    if [ -z "$file_list" ]; then
        echo "No L2A files found for date $date in $L2A_DIR_W_DATE or its subdirectories. Skipping campaign."
    else
        # Files can come from several time-integration subdirectories (e.g. L2A/20MIN/, L2A/60MIN/).
        # Produce one quicklook per integration time, with the integration as a suffix in the filename.
        integrations=$(echo "$file_list" | grep -oP '(?<=/)[0-9]+MIN(?=/)' | sort -u)
        for integration in $integrations; do
            echo "  Integration time: $integration"
            integration_file_list=$(echo "$file_list" | grep "/${integration}/")
            integration_fig_prefix="${FIG_PREFIX}${integration}_"
            echo "$HOME/.env_euliaa/bin/python $HOME/euliaa_proc/euliaa_proc/quicklooks.py --l2a_file_list $integration_file_list --fig_dir "$QUICKLOOKS_DIR" --fig_prefix ${integration_fig_prefix} --wind_str ${WIND_STR} --bsc_str ${BSC_STR} --T_str ${T_STR} --mask_flag ${MASK_FLAG}"
            $HOME/.env_euliaa/bin/python $HOME/euliaa_proc/euliaa_proc/quicklooks.py --l2a_file_list $integration_file_list --fig_dir "$QUICKLOOKS_DIR" --fig_prefix ${integration_fig_prefix} --wind_str ${WIND_STR} --bsc_str ${BSC_STR} --T_str ${T_STR} --mask_flag ${MASK_FLAG}
            $HOME/.env_euliaa/bin/python $HOME/euliaa_proc/euliaa_proc/quicklooks_interactive.py --l2a_file_list $integration_file_list --fig_dir "$QUICKLOOKS_DIR" --fig_prefix ${integration_fig_prefix} --wind_str ${WIND_STR} --bsc_str ${BSC_STR} --T_str ${T_STR} --mask_flag ${MASK_FLAG}
            if [ $? -ne 0 ]; then
                echo "  ✗ Error running quicklooks for $campaign ($integration)"
            fi
        done
    fi
    
    if [ -z "$file_list_l1" ]; then
        echo "No L1 files found for date $date in $L1_DIR_W_DATE or its subdirectories. Skipping campaign."
    else
        # L1 files live in a flat directory but can correspond to several time integrations,
        # encoded in the filename as e.g. "_dT20min_", "_dT60min_". Produce one quicklook per
        # integration time, with the integration (normalized to match the L2A convention, e.g. 20MIN) as a filename suffix.
        integrations_l1=$(echo "$file_list_l1" | grep -oP 'dT\K[0-9]+(?=min)' | sort -u)
        for integration_min in $integrations_l1; do
            integration_l1="${integration_min}MIN"
            echo "  L1 integration time: $integration_l1"
            integration_file_list_l1=$(echo "$file_list_l1" | grep "_dT${integration_min}min_")
            integration_l1_fig_prefix="${L1_FIG_PREFIX}${integration_l1}_"
            $HOME/.env_euliaa/bin/python $HOME/euliaa_proc/euliaa_proc/quicklooks_signal.py --l1_file_list $integration_file_list_l1 --fig_dir "$L1_QUICKLOOKS_DIR" --fig_prefix ${integration_l1_fig_prefix}
            $HOME/.env_euliaa/bin/python $HOME/euliaa_proc/euliaa_proc/quicklooks_signal_interactive.py --l1_file_list $integration_file_list_l1 --fig_dir "$L1_QUICKLOOKS_DIR" --fig_prefix ${integration_l1_fig_prefix}
            if [ $? -ne 0 ]; then
                echo "  ✗ Error running quicklooks signal for $campaign ($integration_l1)"
            fi
        done
    fi
    echo "----------------------------------------"
done

echo "All campaigns processed."
