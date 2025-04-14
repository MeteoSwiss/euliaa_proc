#!/bin/bash

SRC=/data/euliaa-l1/TESTS/ #s3://euliaa-l1/TESTS/
DEST=/data/euliaa-l2/TESTS/ # for now, not directly in s3 but through mounted dir

# file_list=$(s3cmd ls $SRC_BUCKET | awk '{print $4}')
file_list=$(ls $SRC)
# reference_date="2023-10-01 00:00:00"
echo $file_list
source $(dirname "$0")/reference_date.sh

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
        output_nc_l2A=L2A_${date_time}.nc
        output_nc_l2B=L2B_${date_time}.nc
        echo "Processing $file to $output_nc_l2A and $output_nc_l2B"
        python3 write_netcdf.py --hdf5_file $SRC/$file --output_nc_l2A $DEST/$output_nc_l2A --output_nc_l2B $DEST/$output_nc_l2B
        if [[ $? -eq 0 ]]; then
            echo "Processing successful. Updating reference date."
            echo "reference_date='$date_time'" > $(dirname "$0")/reference_date.sh
        else
            echo "Processing failed. Reference date not updated."
        fi

    else
        echo "File $file is not newer than $reference_date"
    fi

done
