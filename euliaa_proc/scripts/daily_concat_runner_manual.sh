for year in 2025; do
    for month in 11 12; do
        for day in 01 02 03 04 05 06 07 08 09 10 11 12 13 14 15 16 17 18 19 20 21 22 23 24 25 26 27 28 29 30 31; do
            /home/oper/euliaa_proc/euliaa_proc/scripts/daily_concat.sh ${year}-${month}-${day} -b s3://euliaa-l2/Andoya/L2A/ -o s3://euliaa-daily/Andoya/ -t 10MIN -c /home/oper/euliaa_proc/euliaa_proc/config/config_qc_w_correction.yaml --campaign Andoya
            /home/oper/euliaa_proc/euliaa_proc/scripts/daily_concat.sh ${year}-${month}-${day} -b s3://euliaa-l2/Andoya/L2A/ -o s3://euliaa-daily/Andoya/ -t 20MIN -c /home/oper/euliaa_proc/euliaa_proc/config/config_qc_w_correction.yaml --campaign Andoya
            /home/oper/euliaa_proc/euliaa_proc/scripts/daily_concat.sh ${year}-${month}-${day} -b s3://euliaa-l2/Andoya/L2A/ -o s3://euliaa-daily/Andoya/ -t 60MIN -c /home/oper/euliaa_proc/euliaa_proc/config/config_qc_w_correction.yaml --campaign Andoya
        done
    done
done
