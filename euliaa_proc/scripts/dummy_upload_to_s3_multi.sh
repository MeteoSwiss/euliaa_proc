#!/bin/bash
# TIMESTAMP="2025-11-16_12-00-00"

TIMESTAMP=$(date '+%Y-%m-%d_%H-%M-%S')

SRC1="/home/oper/euliaa_proc/data/BankExport3.h5"
SRC2="/home/oper/euliaa_proc/data/EULIAA_L1_2025-08-20_QC_noAPD.h5"
DST1="s3://euliaa-l1/TESTS/Test/EULIAA_L1_Te_$TIMESTAMP.h5"
DST11="s3://euliaa-l1/TESTS/Test/20MIN/EULIAA_L120MIN_Te_$TIMESTAMP.h5"
DST12="s3://euliaa-l1/TESTS/Test/60MIN/EULIAA_L160MIN_Te_$TIMESTAMP.h5"
DST2="s3://euliaa-l1/TESTS/Kuehlungsborn/EULIAA_L1_Kb_$TIMESTAMP.h5"
DST21="s3://euliaa-l1/TESTS/Kuehlungsborn/20MIN/EULIAA_L120MIN_Kb_$TIMESTAMP.h5"
DST22="s3://euliaa-l1/TESTS/Kuehlungsborn/60MIN/EULIAA_L160MIN_Kb_$TIMESTAMP.h5"

# s3cmd put "$SRC1" "$DST1"
# s3cmd put "$SRC2" "$DST2"
s3cmd put "$SRC1" "$DST11"
sleep 10
s3cmd put "$SRC1" "$DST12"
# wait 30 seconds
sleep 15
s3cmd put "$SRC2" "$DST21"
sleep 10
s3cmd put "$SRC2" "$DST22"