#!/bin/bash

start="2026-07-20"
end=$(date +%Y-%m-%d)  # current date

current="$start"

while [ "$(date -d "$current" +%Y%m%d)" -le "$(date -d "$end" +%Y%m%d)" ]; do
    year=$(date -d "$current" +%Y)
    month=$(date -d "$current" +%m)
    day=$(date -d "$current" +%d)

    echo "Running for $year-$month-$day"
    /home/oper/euliaa_proc/euliaa_proc/scripts/quicklooks_multi.sh --year "$year" --month "$month" --day "$day"

    # move to next day
    current=$(date -d "$current + 1 day" +%Y-%m-%d)
done