#!/usr/bin/env python3
"""Send yesterday's daily recap as a plain-text email body via Gmail SMTP."""

from __future__ import annotations

import os
import smtplib
import ssl
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage
from pathlib import Path


@dataclass
class EmailConfig:
    smtp_host: str
    smtp_port: int
    smtp_user: str
    smtp_password: str
    sender: str
    recipients: list[str]
    subject_prefix: str


def load_env_file(env_path: Path) -> None:
    if not env_path.exists():
        raise FileNotFoundError(
            f"Credentials file not found: {env_path}. "
            "Create it from daily_recap_email.env.example and chmod 600."
        )

    for line in env_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ[key] = value


def get_required_env(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise ValueError(f"Missing required environment variable: {name}")
    return value


def load_config() -> EmailConfig:
    env_path = Path(os.environ.get("EULIAA_EMAIL_ENV_FILE", "/home/oper/.config/euliaa/daily_recap_email.env"))
    load_env_file(env_path)

    recipients_raw = get_required_env("EULIAA_EMAIL_RECIPIENTS")
    recipients = [r.strip() for r in recipients_raw.split(",") if r.strip()]
    if not recipients:
        raise ValueError("EULIAA_EMAIL_RECIPIENTS must contain at least one email address")

    smtp_password = get_required_env("EULIAA_SMTP_APP_PASSWORD")
    if smtp_password == "REPLACE_WITH_GMAIL_APP_PASSWORD":
        raise ValueError("EULIAA_SMTP_APP_PASSWORD is still a placeholder value")

    return EmailConfig(
        smtp_host=os.environ.get("EULIAA_SMTP_HOST", "smtp.gmail.com"),
        smtp_port=int(os.environ.get("EULIAA_SMTP_PORT", "587")),
        smtp_user=get_required_env("EULIAA_SMTP_USER"),
        smtp_password=smtp_password,
        sender=os.environ.get("EULIAA_EMAIL_SENDER", get_required_env("EULIAA_SMTP_USER")),
        recipients=recipients,
        subject_prefix=os.environ.get("EULIAA_EMAIL_SUBJECT_PREFIX", "EULIAA Daily Recap"),
    )


def get_yesterday_utc_date() -> str:
    now_utc = datetime.now(timezone.utc)
    return (now_utc - timedelta(days=1)).strftime("%Y-%m-%d")


def get_recap_path(yesterday_date: str) -> Path:
    recap_dir = Path(os.environ.get("EULIAA_RECAP_DIR", "/home/oper/daily_recaps"))
    return recap_dir / f"daily_recap_{yesterday_date}.txt"


def build_message(config: EmailConfig, recap_path: Path, recap_content: str, recap_date: str) -> EmailMessage:
    msg = EmailMessage()
    msg["From"] = config.sender
    msg["To"] = ", ".join(config.recipients)
    msg["Subject"] = f"{config.subject_prefix} - {recap_date}"
    msg.set_content(recap_content)
    msg["X-EULIAA-Recap-File"] = str(recap_path)
    return msg


def send_message(config: EmailConfig, msg: EmailMessage) -> None:
    context = ssl.create_default_context()
    if config.smtp_port == 465:
        with smtplib.SMTP_SSL(config.smtp_host, config.smtp_port, timeout=30, context=context) as server:
            server.login(config.smtp_user, config.smtp_password)
            server.send_message(msg)
    else:
        with smtplib.SMTP(config.smtp_host, config.smtp_port, timeout=30) as server:
            server.ehlo()
            server.starttls(context=context)
            server.ehlo()
            server.login(config.smtp_user, config.smtp_password)
            server.send_message(msg)


def main() -> int:
    try:
        config = load_config()
        recap_date = get_yesterday_utc_date()
        recap_path = get_recap_path(recap_date)

        if not recap_path.exists():
            raise FileNotFoundError(f"Recap file does not exist: {recap_path}")

        recap_content = recap_path.read_text(encoding="utf-8").strip()
        if not recap_content:
            raise ValueError(f"Recap file is empty: {recap_path}")

        msg = build_message(config, recap_path, recap_content, recap_date)
        send_message(config, msg)

        print(f"[OK] Recap email sent for {recap_date} to {', '.join(config.recipients)}")
        return 0
    except Exception as exc:  # noqa: BLE001
        print(f"[ERROR] Failed to send recap email: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
