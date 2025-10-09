#!/bin/bash
source ${HOME}/euliaa_proc/euliaa_proc/config/config_quicklooks.conf
date=$(date +%Y%m%d)
# echo $(s3cmd ls ${L2A_DIR}L2A_${date}* | awk '{print $4}')
$HOME/.env_euliaa/bin/python $HOME/euliaa_proc/euliaa_proc/quicklooks.py --l2a_file_list $(s3cmd ls ${L2A_DIR}L2A_${date}* | awk '{print $4}') --fig_dir ${QUICKLOOKS_DIR}