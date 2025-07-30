#!/bin/bash
date=$(date +%Y%m%d)
/home/acbr/.env_euliaa/bin/python /home/acbr/euliaa_proc/euliaa_proc/quicklooks.py --l2a_file_list $(s3cmd ls s3://euliaa-l2/TESTS/L2A_${date}* | awk '{print $4}') --fig_dir s3://euliaa-quicklooks/quicklooks/