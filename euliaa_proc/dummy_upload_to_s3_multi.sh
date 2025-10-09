#!/bin/bash
TIMESTAMP=$(date '+%Y%m%d_%H%M%S')

SRC1="/home/oper/euliaa_proc/data/BankExport3.h5"
SRC2="/home/oper/euliaa_proc/data/EULIAA_L1_2025-08-20_QC_noAPD.h5"
DST1="s3://euliaa-l1/TESTS/Test/EULIAA_L1_Te_$TIMESTAMP.h5"
DST2="s3://euliaa-l1/TESTS/Kuehlungsborn/EULIAA_L1_Kb_$TIMESTAMP.h5"

s3cmd put "$SRC1" "$DST1"
s3cmd put "$SRC2" "$DST2"