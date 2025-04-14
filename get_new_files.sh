#!/bin/bash

file_list=$(s3cmd ls s3://euliaa-l1/TESTS/ | awk '{print $4}')
# echo $file_list

# reference_date="2023-10-01 00:00:00"
source $(dirname "$0")/reference_date1.sh

for file in $file_list; do
    # Skip if the file is not a .h5 file
    if [[ $file != *.h5 ]]; then
        continue
    fi

    file_name=$(basename "$file")
    # Extract the date from the file name
    date_time=$(echo "$file_name" | grep -oE '[0-9]{4}-[0-9]{2}-[0-9]{2}_[0-9]{2}-[0-9]{2}-[0-9]{2}')
    if [[ -z "$date_time" ]]; then
        continue
    fi
    echo "Extracted date: $date_time"

    if [[ "$date_time" > "$reference_date" ]]; then
        echo "File $file is newer than $reference_date"
        # Add your processing logic here
        echo "reference_date='$date_time'" > reference_date.sh
    else
        echo "File $file is not newer than $reference_date"
    fi

done
