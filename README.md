# euliaa_proc

This repository contains the codes to process EULIAA lidar data.

The most important script in operational use is `processing_manager.py`:
- handles bucket_notifications and launches l1->l2 processing upon upload of a new h5 file to the l1 bucket
- using the settings defined in `config/config_main_s3.yaml`, which in turn refers to other config files
- l2a and l2b netCDF files are written to l2 bucket
- specific l2 netCDF file containing only wind is also created, following the E-PROFILE DWL toolbox format; this is for dissemination of wind data onto GTS through E-PROFILE/UKMO.
- temperature BUFR message is also created.

Quicklooks are handled independently as we don't want one quicklook per file but rather a daily one -> this is done in the crontab (can be adapted), for example:
> `1,31 * * * * /home/acbr/.env_euliaa/bin/python /home/acbr/euliaa_proc/euliaa_proc/quicklooks.py --l2a_file_list $(s3cmd ls s3://euliaa-l2/TESTS/L2A_20250723* | awk '{print $4}') --fig_dir s3://euliaa-quicklooks/quicklooks/`

