# Daily Recap Email Setup

This setup sends the content of:

- `/home/oper/daily_recaps/daily_recap_<yesterday>.txt`

as a plain-text email body every day at **07:00 UTC**.

## What was added

- `euliaa_proc/scripts/send_daily_recap_email.py`
- `euliaa_proc/scripts/send_daily_recap.sh`
- `euliaa_proc/scripts/install_daily_recap_cron.sh`
- `euliaa_proc/scripts/daily_recap_email.env.example`
- local credentials file (not in git): `/home/oper/.config/euliaa/daily_recap_email.env`

## Credentials file

Edit:

- `/home/oper/.config/euliaa/daily_recap_email.env`

and replace:

- `EULIAA_SMTP_APP_PASSWORD=REPLACE_WITH_GMAIL_APP_PASSWORD`

with your real Gmail App Password for `euliaa.mch@gmail.com`.

Permissions are already restricted to owner-only (`chmod 600`).

## Schedule

Cron entry installed under user `oper`:

- `CRON_TZ=UTC`
- `0 7 * * * /bin/bash /home/oper/euliaa_proc/euliaa_proc/daily_recap/send_daily_recap.sh >> /home/oper/euliaa_proc/euliaa_proc/logs/daily_recap_email.log 2>&1`

To re-install/update this managed cron block:

```bash
/bin/bash /home/oper/euliaa_proc/euliaa_proc/scripts/install_daily_recap_cron.sh
```

## Notes

- The existing cron job already generates daily recap files at `00:05`, so the sender only emails the already-generated file by default.
- If you ever want the sender wrapper to regenerate recap first:

```bash
GENERATE_RECAP_FIRST=1 /bin/bash /home/oper/euliaa_proc/euliaa_proc/daily_recap/send_daily_recap.sh
```

## Manual test

After setting the real App Password:

```bash
/bin/bash /home/oper/euliaa_proc/euliaa_proc/scripts/send_daily_recap.sh
tail -n 50 /home/oper/euliaa_proc/euliaa_proc/logs/daily_recap_email.log
```

## Troubleshooting

- Missing recap file:
  - Verify `/home/oper/daily_recaps/daily_recap_<yesterday>.txt` exists.
- SMTP placeholder still present:
  - Replace `REPLACE_WITH_GMAIL_APP_PASSWORD` in credentials file.
- See current cron config:

```bash
crontab -l
```
