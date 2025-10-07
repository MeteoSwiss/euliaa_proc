#!/bin/bash
TIMESTAMP=$(date '+%Y%m%d_%H%M%S')
SRC="/home/oper/euliaa_proc/data/BankExport3.h5"
DST="s3://euliaa-l1/TESTS/BankExport_$TIMESTAMP.h5"
s3cmd put "$SRC" "$DST"