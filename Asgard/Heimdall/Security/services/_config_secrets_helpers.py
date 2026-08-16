"""
Heimdall Config Secrets Scanner - pure helper functions.

Standalone utilities for placeholder detection, entropy calculation,
value masking, key classification, and data structure flattening.
These have no dependency on scanner state.
"""

import math
import re
from typing import Any, Dict, Iterator, List, Optional, Set, Tuple

from Asgard.Heimdall.Security.utilities.security_utils import mask_secret


# Whole-value token words only. Bare "<" / substring hits drop real secrets.
PLACEHOLDER_FRAGMENTS = (
    "changeme",
    "todo",
    "replace",
    "example",
    "placeholder",
    "insert",
)

MAX_FLATTEN_DEPTH = 32

_PLACEHOLDER_TOKEN_RE = re.compile(
    r"^(?:"
    + "|".join(re.escape(token) for token in PLACEHOLDER_FRAGMENTS)
    + r")(?:[-_][A-Za-z0-9._-]{0,64})?$",
    re.IGNORECASE,
)
_PLACEHOLDER_TEMPLATE_RE = re.compile(
    r"^(?:"
    r"\$\{[^{}]{1,128}\}"
    r"|{{[^{}]{1,128}}}"
    r"|<[^<>]{1,128}>"
    r")$"
)
_PLACEHOLDER_DUMMY_RE = re.compile(r"^(?:x{5,64}|0{5,64})$", re.IGNORECASE)
_PLACEHOLDER_YOUR_RE = re.compile(r"^your[-_][A-Za-z0-9._-]{0,128}$", re.IGNORECASE)


def is_placeholder(value: str) -> bool:
    """Return True if the whole value is a placeholder-shaped token."""
    if not value:
        return True
    stripped = value.strip()
    if not stripped:
        return True
    if _PLACEHOLDER_TEMPLATE_RE.fullmatch(stripped):
        return True
    if _PLACEHOLDER_DUMMY_RE.fullmatch(stripped):
        return True
    if _PLACEHOLDER_YOUR_RE.fullmatch(stripped):
        return True
    return bool(_PLACEHOLDER_TOKEN_RE.fullmatch(stripped))


def shannon_entropy(text: str) -> float:
    """Calculate the Shannon entropy of a string."""
    if not text:
        return 0.0
    freq: Dict[str, int] = {}
    for char in text:
        freq[char] = freq.get(char, 0) + 1
    length = len(text)
    entropy = 0.0
    for count in freq.values():
        probability = count / length
        if probability > 0:
            entropy -= probability * math.log2(probability)
    return entropy


def mask_value(value: str) -> str:
    """Return a last-2 (or length-only) mask. Never prints both ends."""
    return mask_secret(value)


def is_credential_key(key: str, credential_key_names: List[str]) -> bool:
    """Return True if the key name suggests it holds a credential."""
    key_lower = key.lower()
    for fragment in credential_key_names:
        if fragment in key_lower:
            return True
    return False


def flatten_dict(
    data: Any,
    prefix: str = "",
    *,
    max_depth: int = MAX_FLATTEN_DEPTH,
    _depth: int = 0,
    _seen: Optional[Set[int]] = None,
) -> Iterator[Tuple[str, str, Any]]:
    """
    Recursively yield (context_path, key, value) tuples from a nested dict/list.

    Depth-capped and cycle-safe. Aliased/cyclic YAML nodes are visited once.
    """
    if _depth > max_depth:
        return
    if isinstance(data, (dict, list)):
        if _seen is None:
            _seen = set()
        marker = id(data)
        if marker in _seen:
            return
        _seen.add(marker)
    if isinstance(data, dict):
        for key, value in data.items():
            full_path = f"{prefix}.{key}" if prefix else key
            if isinstance(value, (dict, list)):
                yield from flatten_dict(
                    value,
                    full_path,
                    max_depth=max_depth,
                    _depth=_depth + 1,
                    _seen=_seen,
                )
            else:
                yield full_path, key, value
    elif isinstance(data, list):
        for idx, item in enumerate(data):
            full_path = f"{prefix}[{idx}]"
            if isinstance(item, (dict, list)):
                yield from flatten_dict(
                    item,
                    full_path,
                    max_depth=max_depth,
                    _depth=_depth + 1,
                    _seen=_seen,
                )
            else:
                yield full_path, str(idx), item
