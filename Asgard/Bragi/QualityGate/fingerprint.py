"""
Finding Fingerprints — stable identity for analysis findings.

Implements the fingerprint scheme from the Heimdall-09 / Bragi-06 plans:

    fingerprint = sha256(rule_id + path + signature + line + message)

The AST node signature is a structural hash of the innermost enclosing
function/class (or the whole module) with all line/column information
excluded, so refactors that merely shift lines do not churn fingerprints.

Anchor quality (best available wins):
    - "ast":     Python source parsed; enclosing-node structural hash.
    - "snippet": whitespace-normalized snippet hash (interim fallback for
                 languages without AST anchoring yet).
    - "file":    rule + file + line + message (and a full-source hash when
                 source is present but not parseable).

Line and message are always mixed into the digest so two findings of the
same rule in one file cannot collapse to a single baseline entry.

Caller-supplied fingerprints are not trusted unless they carry an HMAC
over the digest (`ASGARD_QG_HMAC_KEY`). That key is the same env var as
the baseline store; this module never writes or reads the store key file.

No network access, no external services, no project-specific assumptions.
"""

import ast
import hashlib
import hmac
import os
import re
from pathlib import PurePath
from typing import Optional

_HMAC_ENV = "ASGARD_QG_HMAC_KEY"
_SIGNED_PREFIX = "qg1."
_HEX64 = r"[0-9a-f]{64}"
_SIGNED_RE = re.compile(rf"^{re.escape(_SIGNED_PREFIX)}({_HEX64})\.({_HEX64})$")


def normalize_path(file_path: str) -> str:
    """Normalize a file path for fingerprinting: POSIX separators, no leading './'."""
    path = PurePath(str(file_path).strip().replace("\\", "/")).as_posix()
    while path.startswith("./"):
        path = path[2:]
    return path


def normalize_snippet(snippet: str) -> str:
    """Collapse all whitespace so formatting changes do not churn fingerprints."""
    return " ".join(snippet.split())


def _signing_key(key: Optional[bytes] = None) -> Optional[bytes]:
    if key is not None:
        return key
    env = os.environ.get(_HMAC_ENV, "").strip()
    if env:
        return env.encode("utf-8")
    return None


def sign_fingerprint(digest: str, key: Optional[bytes] = None) -> str:
    """Wrap a sha256 hex digest in an HMAC so the gate can trust it."""
    secret = _signing_key(key)
    if secret is None:
        raise ValueError(f"{_HMAC_ENV} is not set; cannot sign a fingerprint")
    if not re.fullmatch(_HEX64, digest or ""):
        raise ValueError("fingerprint digest must be a sha256 hex string")
    mac = hmac.new(secret, digest.encode("ascii"), hashlib.sha256).hexdigest()
    return f"{_SIGNED_PREFIX}{digest}.{mac}"


def is_signed_fingerprint(value: str, key: Optional[bytes] = None) -> bool:
    """True when `value` is an HMAC-wrapped digest verifiable with the gate key."""
    match = _SIGNED_RE.fullmatch(value or "")
    if match is None:
        return False
    secret = _signing_key(key)
    if secret is None:
        return False
    digest, mac = match.group(1), match.group(2)
    expected = hmac.new(secret, digest.encode("ascii"), hashlib.sha256).hexdigest()
    return hmac.compare_digest(mac, expected)


def unsigned_fingerprint(value: str, key: Optional[bytes] = None) -> Optional[str]:
    """Return the digest inside a valid signed fingerprint, else None."""
    if not is_signed_fingerprint(value, key):
        return None
    match = _SIGNED_RE.fullmatch(value or "")
    return match.group(1) if match else None


def _enclosing_node_signature(source: str, line: int) -> Optional[tuple]:
    """
    Structural hash of the innermost function/class enclosing `line`,
    or of the whole module if the line sits at top level.

    Returns (signature, node_start_line) or None when the source cannot
    be parsed as Python.
    """
    try:
        tree = ast.parse(source)
    except (SyntaxError, ValueError):
        return None

    enclosing: ast.AST = tree
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            start = node.lineno
            end = getattr(node, "end_lineno", None) or start
            if start <= line <= end:
                # Prefer the innermost (smallest) enclosing scope
                if enclosing is tree:
                    enclosing = node
                else:
                    cur_start = getattr(enclosing, "lineno", 0)
                    cur_end = getattr(enclosing, "end_lineno", 10 ** 9)
                    if start >= cur_start and end <= cur_end:
                        enclosing = node

    # ast.dump with default settings excludes lineno/col_offset attributes,
    # giving a purely structural representation.
    structure = ast.dump(enclosing)
    start_line = int(getattr(enclosing, "lineno", 1) or 1)
    return hashlib.sha256(structure.encode("utf-8")).hexdigest(), start_line


def _locator(line: Optional[int], relative_to: Optional[int] = None) -> str:
    if line is None:
        return ""
    try:
        n = int(line)
    except (TypeError, ValueError):
        return ""
    if relative_to is not None:
        return str(n - int(relative_to))
    return str(n)


def compute_fingerprint(
    rule_id: str,
    file_path: str,
    *,
    source: Optional[str] = None,
    line: Optional[int] = None,
    snippet: Optional[str] = None,
    message: Optional[str] = None,
) -> str:
    """
    Compute a stable fingerprint for a finding.

    Args:
        rule_id: Rule identifier (e.g. "SQLI", "complexity.max").
        file_path: Path of the file containing the finding.
        source: Full source text of the file (enables AST anchoring for Python).
        line: 1-based line number of the finding within `source`.
        snippet: Source snippet at the finding site (interim non-AST anchor).
        message: Finding message; always mixed into the digest.

    Returns:
        Hex sha256 fingerprint. Same finding after a pure line-shift refactor
        keeps the same fingerprint when AST anchoring is available.
    """
    return fingerprint_with_anchor(
        rule_id, file_path, source=source, line=line, snippet=snippet,
        message=message,
    )[0]


def fingerprint_finding(finding, source: Optional[str] = None) -> str:
    """Compute the fingerprint for a GateFinding-shaped object."""
    return compute_fingerprint(
        finding.rule_id,
        finding.file_path,
        source=source,
        line=getattr(finding, "line", None),
        snippet=getattr(finding, "snippet", None) or None,
        message=getattr(finding, "message", None) or None,
    )


def fingerprint_with_anchor(
    rule_id: str,
    file_path: str,
    *,
    source: Optional[str] = None,
    line: Optional[int] = None,
    snippet: Optional[str] = None,
    message: Optional[str] = None,
) -> tuple:
    """
    Compute (fingerprint, anchor) where anchor is 'ast', 'snippet', or 'file'.

    The digest always includes line (relative to the AST node when anchored)
    and the normalized message so same-rule findings in one file stay distinct.
    """
    norm_path = normalize_path(file_path)

    signature = None
    anchor = "file"
    node_start = None
    if source is not None and line is not None:
        ast_hit = _enclosing_node_signature(source, line)
        if ast_hit is not None:
            signature, node_start = ast_hit
            anchor = "ast"
    if signature is None and snippet:
        normalized = normalize_snippet(snippet)
        if normalized:
            signature = hashlib.sha256(normalized.encode("utf-8")).hexdigest()
            anchor = "snippet"
    if signature is None and source:
        signature = hashlib.sha256(source.encode("utf-8")).hexdigest()
        anchor = "file"
    if signature is None:
        signature = ""
        anchor = "file"

    locator = _locator(line, node_start if anchor == "ast" else None)
    payload = "\x00".join([
        str(rule_id),
        norm_path,
        signature,
        locator,
        normalize_snippet(message or ""),
    ])
    return hashlib.sha256(payload.encode("utf-8")).hexdigest(), anchor
