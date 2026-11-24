#!/usr/bin/env python3
"""
Event-driven quicklook production.

processing_manager_multi.py drops an empty marker file <campaign>__<YYYY-MM-DD> in QUEUE_DIR for every
L1 file it processes (created once; its mtime = first upload since the day was last plotted).
This worker, run from cron under flock, plots every queued (campaign, day) whose marker is older than
--settle minutes, newest day first so near-real-time data is never stuck behind a large re-upload.

A marker is moved to QUEUE_DIR/inprogress/ *before* plotting: files arriving during plotting create a
fresh marker, so that day is plotted again on a later run and nothing is lost.

Usage:
  quicklooks_queue_worker.py                      # process the queue (cron)
  quicklooks_queue_worker.py --enqueue Andoya 2026-05-30 2026-06-01   # manual backfill
  quicklooks_queue_worker.py --list               # show pending markers
"""
import argparse
import datetime as dt
import os
import re
import subprocess
import sys
import time

QUEUE_DIR = os.environ.get('EULIAA_QL_QUEUE_DIR', '/home/oper/ql_queue')
INPROGRESS_DIR = os.path.join(QUEUE_DIR, 'inprogress')
QL_SCRIPT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'quicklooks_multi.sh')
MARKER_RE = re.compile(r'^(?P<campaign>[A-Za-z0-9_\-]+)__(?P<date>\d{4}-\d{2}-\d{2})$')


def log(msg):
    print(f'{dt.datetime.now():%Y-%m-%d %H:%M:%S} [ql-queue] {msg}', flush=True)


def pending(settle_s):
    """Markers ready to be processed, newest day first."""
    ready = []
    now = time.time()
    for name in os.listdir(QUEUE_DIR):
        m = MARKER_RE.match(name)
        path = os.path.join(QUEUE_DIR, name)
        if m is None or not os.path.isfile(path):
            continue
        if now - os.path.getmtime(path) >= settle_s:
            ready.append((m.group('date'), m.group('campaign'), name))
    return sorted(ready, reverse=True)


def recover_inprogress():
    """Markers left in inprogress/ by a crashed run go back to the queue (we hold the flock, so no other worker)."""
    for name in os.listdir(INPROGRESS_DIR):
        src, dst = os.path.join(INPROGRESS_DIR, name), os.path.join(QUEUE_DIR, name)
        if os.path.exists(dst):
            os.remove(src)
        else:
            os.rename(src, dst)
        log(f'Recovered interrupted marker {name}')


def run_one(date, campaign, name, timeout_s):
    claimed = os.path.join(INPROGRESS_DIR, name)
    os.rename(os.path.join(QUEUE_DIR, name), claimed)
    y, mo, d = date.split('-')
    log(f'Quicklooks for {campaign} {date}')
    t0 = time.time()
    try:
        rc = subprocess.run(['bash', QL_SCRIPT, '--campaign', campaign, '--year', y, '--month', mo, '--day', d],
                            timeout=timeout_s).returncode
        log(f'Done {campaign} {date} (rc={rc}, {time.time() - t0:.0f}s)')
    except subprocess.TimeoutExpired:
        log(f'TIMEOUT after {timeout_s}s for {campaign} {date}, skipping')
    os.remove(claimed)  # no automatic retry: a failing day would otherwise loop forever; re-enqueue manually


def enqueue(campaign, start, end):
    day, last = dt.date.fromisoformat(start), dt.date.fromisoformat(end)
    while day <= last:
        path = os.path.join(QUEUE_DIR, f'{campaign}__{day.isoformat()}')
        if not os.path.exists(path):
            open(path, 'a').close()
            os.utime(path, (0, 0))  # epoch mtime: ready immediately, no settle wait
        log(f'Enqueued {campaign} {day}')
        day += dt.timedelta(days=1)


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--settle', type=float, default=10, help='minutes a marker must age before plotting (default 10)')
    p.add_argument('--max-runtime', type=float, default=0,
                   help='stop picking new jobs after this many minutes (0 = until queue empty)')
    p.add_argument('--timeout', type=float, default=60, help='max minutes per campaign-day (default 60)')
    p.add_argument('--enqueue', nargs=3, metavar=('CAMPAIGN', 'START', 'END'), help='queue a date range (YYYY-MM-DD)')
    p.add_argument('--list', action='store_true', help='list queued markers and exit')
    a = p.parse_args()

    os.makedirs(INPROGRESS_DIR, exist_ok=True)
    if a.enqueue:
        enqueue(*a.enqueue)
        return
    if a.list:
        for date, campaign, _ in pending(0):
            print(campaign, date)
        return

    recover_inprogress()
    t_start = time.time()
    while True:
        jobs = pending(a.settle * 60)
        if not jobs:
            break
        run_one(*jobs[0], timeout_s=a.timeout * 60)  # re-scan after each job so new NRT markers jump ahead
        if a.max_runtime and time.time() - t_start > a.max_runtime * 60:
            log('Max runtime reached, remaining markers left for next run')
            break


if __name__ == '__main__':
    sys.exit(main())
