# euliaa_proc

Processing code for EULIAA lidar data: reads L1 HDF5 files and produces L2 netCDF products,
E-PROFILE wind files, BUFR messages and quicklooks.

Further documentation (MeteoSwiss internal): [Confluence page](https://meteoswiss.atlassian.net/wiki/spaces/MDA/pages/679937188/EULIAA+processing+and+data+flow).

## Data flow

```
s3://euliaa-l1  (L1 HDF5 uploaded by IAP)
      |  bucket notification -> processing_manager_multi.py
      v
s3://euliaa-l2         L2A / L2B netCDF (+ BUFR/ for temperature BUFR)
s3://euliaa-eprofile   wind-only netCDF in E-PROFILE DWL format
   -> copied to s3://eprofile-dl-l1 for GTS dissemination via E-PROFILE/UKMO
s3://euliaa-daily      daily concatenated files (cron, daily_concat.sh)
s3://euliaa-quicklooks daily quicklooks (cron, quicklooks_multi.sh)
```

## Requirements

- Python >= 3.10, < 3.12
- `s3cmd` (used for all S3 transfers) and `yq` (used by the shell scripts)
- European Weather Cloud bucket credentials, none of which are in the repo:
  - `~/.s3cfg` — s3cmd config for the EULIAA buckets
  - `~/.s3cfg_eprofile` — s3cmd config for the operational E-PROFILE bucket
  - `~/.aws/credentials`, `~/.aws/config` — used by boto3
  - `~/.config/euliaa/credentials.yaml` — keys/endpoints for the notification topic
    (`access_key_id`, `secret_access_key`, `topic_name`, `endpoint`, `ceph_endpoint`,
    `region_name`, `bucket_name`)

## Install

```bash
git clone https://github.com/MeteoSwiss/euliaa_proc.git
cd euliaa_proc
python3 -m venv ~/.env_euliaa
source ~/.env_euliaa/bin/activate
pip install -e .
```

On the operational VM the environment already exists at `~/.env_euliaa` and the repo at
`~/euliaa_proc`. **To do - this could be improved - Config files and shell scripts contain absolute paths** (`/home/oper/...`),
so adapt them if you install elsewhere.

## Configuration

All config files are in `euliaa_proc/config/`:

| File | Role |
| --- | --- |
| `config_main/config_main_s3_<campaign>.yaml` | entry point per campaign: output buckets, BUFR types, paths to the other configs |
| `config_nc/config_nc_<campaign>.yaml` | netCDF variables, dimensions, attributes, HDF5 → netCDF mapping |
| `config_qc_w_correction.yaml` | QC thresholds, velocity/azimuth corrections, variable lists |
| `config_eprofile_wind_*.yaml` | netCDF variables etc. corresponding to output format for E-Profile (copied from L1_DWL template) |
| `config_quicklooks_multi.yaml` | paths and configs for quicklooks, per campaign |
| `config_log.yaml` | log level and log file location (`euliaa_proc/logs/`) |

**To add a campaign**: copy and adapt `config_main_s3_<campaign>.yaml` and
`config_nc_<campaign>.yaml`, add the campaign to `config_quicklooks_multi.yaml`, and add a branch
for its L1 bucket prefix in the `if/elif` block of `processing_manager_multi.py`.

## Running

### Operationally (bucket notifications)

`processing_manager_multi.py` is a Flask/waitress app listening on port 8080. It receives an S3
notification for each new `.h5` file in `s3://euliaa-l1`, selects the config from the campaign
folder in the object key, and runs the full L1→L2 pipeline. It runs as a systemd service:

```bash
sudo systemctl status  processing_manager_multi
sudo systemctl restart processing_manager_multi
journalctl -u processing_manager_multi -f     # live logs
```

The integration time is read from the filename (`dT20min`, `dT60min`, ...) and decides which
products are treated as operational (wind for 20MIN, temperature for 60MIN, both for 120MIN). **If working with a new integration time -> the code must be adjusted**

### Manually on a single file

`euliaa_proc/main.py` provides a CLI to run the pipeline on a local file without S3
(`python main.py --help`); by default it writes L2A only.

Note: L1 HDF5 files cannot be read directly from S3 — they are first downloaded to `~/tmp/` and
deleted afterwards.

To test as closely to automatic ppipeline as it gets:
```python
from euliaa_proc.processing_manager_multi import run_processing_pipeline

run_processing_pipeline(
    's3://euliaa-l1/Andoya/EULIAA_L1_2026-06-20_03-20-00_dT20min_dH250m_OL.h5',
    'euliaa_proc/config/config_main/config_main_s3_Andoya.yaml',
    operational_product={'wind': 1, 'temperature': 0, 'backscatter': 1},
    integration_time_str='20MIN',
)
```

### Quicklooks, daily files, recap (crontab)

These are **not** triggered by notifications. If needed (e.g. old data uploaded), run manually.

```bash
euliaa_proc/scripts/quicklooks_multi.sh [--year YYYY --month MM --day DD]   # every 5 min
euliaa_proc/scripts/daily_concat_runner.sh                                  # daily, wraps daily_concat.sh
euliaa_proc/daily_recap/daily_recap.sh                                      # daily bucket report
euliaa_proc/scripts/cleanup_old_logs.sh                                     # log rotation
```

`daily_concat.sh --help` documents its options (date, source/output bucket, integration time).
`run_quicklooks_multi_on_date_period.sh` reprocesses quicklooks over a date range.

## Code layout

```
euliaa_proc/
  processing_manager_multi.py  operational entry point (notification listener + pipeline)
  main.py                      Runner class: run_processing, write_l2a/l2b, eprofile, bufr
  measurement.py               H5Reader: read L1, QC flags, SNR, clouds, corrections
  write_netcdf.py              Writer: netCDF output (local or S3)
  eprofile_wind.py             E-PROFILE DWL wind product
  eprofile_bsc.py              E-PROFILE ALC backscatter product (not used operationally)
  nc2bufr.py                   BUFR encoding
  daily_concat.py              concatenation of L2A files over a day
  quicklooks*.py               static (matplotlib) and interactive (plotly) quicklooks
  utils/                       cloud detection, config, data and file helpers
  bucket_notifications/        create/list/delete S3 notification topics
  config/                      all yaml configs
  scripts/                     cron and helper bash scripts
  daily_recap/                 daily bucket report + email
```

## Troubleshooting

### Bucket notifications stopped working

This has happened after heavy code changes with many service stops/restarts. **Stop the service
first**, then from `euliaa_proc/euliaa_proc/bucket_notifications`:

```bash
python3 delete_topic.py
python3 remove_notifications.py
python3 delete_topic.py
python3 list_topics.py                    # must NOT list topic-euliaa-l1; if it does, repeat the above
python3 create_topic_and_notification.py
python3 list_topics.py                    # topic-euliaa-l1 should now appear (possibly twice)
```

Then test:

1. Terminal 1: `python3 processing_manager_multi.py`
2. Terminal 2: `euliaa_proc/scripts/dummy/dummy_upload_to_s3_multi.sh`
3. Terminal 1 should log the incoming notification and start processing.

### A file was not processed

Exceptions are caught per file and the pipeline moves on, so check
`journalctl -u processing_manager_multi` or `euliaa_proc/logs/`. Note also that an E-PROFILE wind
file is skipped on purpose if another one was uploaded less than `integration_time - 4` minutes
earlier, to avoid overlapping data.

