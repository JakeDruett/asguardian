"""Synthetic web-ish entrypoint for the L8 benchmark corpus. Never executed."""

import hashlib
import os
import subprocess

from app.db import fetch_user, run_report
from app.web import render_profile


def handle_request(params):
    user_id = params.get("user_id")
    user = fetch_user(user_id)
    return render_profile(user)


def run_maintenance(task_name):
    # Deliberate command-injection-shaped sink for scanner workloads.
    subprocess.run("maintenance.sh " + task_name, shell=True)


def weak_digest(payload: bytes) -> str:
    # Deliberate weak-hash construct.
    return hashlib.md5(payload).hexdigest()


def report_endpoint(params):
    month = params.get("month", "2026-01")
    return run_report(month)


def env_summary():
    return {k: v for k, v in os.environ.items() if k.startswith("APP_")}
