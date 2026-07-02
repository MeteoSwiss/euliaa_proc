#!/bin/bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_PREFIX="[daily_recap_email]"

if [[ "${GENERATE_RECAP_FIRST:-0}" == "1" ]]; then
	echo "${LOG_PREFIX} $(date -u +"%Y-%m-%dT%H:%M:%SZ") starting daily recap generation"
	"${SCRIPT_DIR}/daily_recap.sh"
fi

echo "${LOG_PREFIX} $(date -u +"%Y-%m-%dT%H:%M:%SZ") sending recap email"

python3 "${SCRIPT_DIR}/send_daily_recap_email.py"

echo "${LOG_PREFIX} $(date -u +"%Y-%m-%dT%H:%M:%SZ") completed successfully"
