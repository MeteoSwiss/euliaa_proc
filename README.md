# euliaa_proc

This repository contains the codes to process EULIAA lidar data.

The most important script in operational use is `processing_manager_multi.py`:
- handles bucket_notifications and launches l1->l2 processing upon upload of a new h5 file to the l1 bucket s3://euliaa-l1
- using the settings defined in `config/config_main_s3_${campaign_name}.yaml`, which in turn refers to other config files
- l2a and l2b netCDF files are written to l2 bucket s3://euliaa-l2
- specific l2 netCDF file containing only wind is also created (s3://euliaa-eprofile/EProfile_DWL/), following the E-PROFILE DWL toolbox format; this is for dissemination of wind data onto GTS through E-PROFILE/UKMO.
- temperature BUFR message is also created.

Quicklooks are handled independently as we don't want one quicklook per file but rather a daily one -> this is done in the crontab (can be adapted), using a dedicated bash script "quicklooks.sh"

See confluence page https://meteoswiss.atlassian.net/wiki/spaces/MDA/pages/679937188/EULIAA+processing+and+data+flow .

### Bucket notifications
It has happened that the notification system bugs, often when heavy code modifs were made, associated with lots of stops/restarts of the processing manager.
In that case, **stop the service**, then go to `euliaa_proc/euliaa_proc/bucket_notifications` and run:
- `python3 delete_topic.py`
- `python3 remove_notifications.py`
- `python3 delete_topic.py` once again
- `python3 list_topics.py` -> you should NOT see any topic containing `topic-euliaa-l1`. If you still see it, go again through the previous steps. 
- `python3 create_topic_and_notification.py`
- then again `python3 list_topics.py` -> you should now see `topic-euliaa-l1` (possibly listed twice, this is beyond my understanding)
Now the notification service should work again.
To test: 
- in a first terminal, manually launch `python3 processing_manager_multi.py`
- from a second terminal, manual test upload to bucket, e.g. with `scripts/dummy_upload_multi.sh`
- you should see something happening in the first terminal

