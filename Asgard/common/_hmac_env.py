"""HMAC key sourcing: explicit env override, or a persisted sibling `.key` file."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional


def hmac_key_from_env(env_name: str) -> Optional[bytes]:
    value = os.environ.get(env_name, "").strip()
    if not value:
        return None
    return value.encode("utf-8")


def persisted_hmac_key(key_path: Path, *, create: bool) -> Optional[bytes]:
    """Read a 32-byte HMAC key from a sibling `.key` file, persisting a freshly
    generated one (0o600, `O_NOFOLLOW`-guarded) the first time `create=True`.

    Returns None when no key is available and none could be created -- callers
    must treat that as "cannot sign/verify" (a cache miss), never as "trust
    the payload unsigned".
    """
    if key_path.exists() and not key_path.is_symlink():
        try:
            flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
            fd = os.open(key_path, flags)
            try:
                existing = os.read(fd, 64)
            finally:
                os.close(fd)
        except OSError:
            existing = b""
        if len(existing) == 32:
            return existing
    if not create or key_path.is_symlink():
        return None
    new_key = os.urandom(32)
    flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC | getattr(os, "O_NOFOLLOW", 0)
    try:
        key_path.parent.mkdir(parents=True, exist_ok=True)
        fd = os.open(key_path, flags, 0o600)
        try:
            os.write(fd, new_key)
        finally:
            os.close(fd)
        os.chmod(key_path, 0o600)
    except OSError:
        return None
    return new_key
