# euliaa_proc

This repository contains the codes to process EULIAA lidar data.

The most important script in operational use is `processing_manager.py`:
- handles bucket_notifications and launches l1->l2 processing upon upload of a new h5 file to the l1 bucket
- using the settings defined in `config/config_main_s3.yaml`, which in turn refers to other config files
- l2a and l2b netCDF files are written to l2 bucket
- specific l2 netCDF file containing only wind is also created, following the E-PROFILE DWL toolbox format; this is for dissemination of wind data onto GTS through E-PROFILE/UKMO.
- temperature BUFR message is also created.

Quicklooks are handled independently as we don't want one quicklook per file but rather a daily one -> this is done in the crontab (can be adapted), using a dedicated bash script "quicklooks.sh"

