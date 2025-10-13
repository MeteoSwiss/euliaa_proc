#!/bin/bash
DATE=$(date '+%Y%m%d')
SRC_BUCKET="s3://euliaa-l2/TESTS/L2A_${DATE}_000001.nc"
DST="s3://euliaa-l2/DAILY/"
mkdir -p tmp
s3cmd get "${SRC_BUCKET}" tmp/
SRC_LOCAL="tmp/L2A_${DATE}_000001.nc"
s3cmd put "${SRC_LOCAL}" "$DST"
rm tmp/*