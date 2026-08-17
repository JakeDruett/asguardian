"""Env-only HMAC keys. Sibling .key files are never used for verify."""

from __future__ import annotations

import os
from typing import Optional


def hmac_key_from_env(env_name: str) -> Optional[bytes]:
    value = os.environ.get(env_name, "").strip()
    if not value:
        return None
    return value.encode("utf-8")
