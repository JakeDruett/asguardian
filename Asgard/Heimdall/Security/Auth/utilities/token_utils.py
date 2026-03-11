"""
Heimdall Security Auth Token Utilities

Helper functions for JWT and token analysis.
"""

import re
from typing import List, Optional, Tuple


def extract_jwt_patterns(content: str) -> List[Tuple[int, str, str]]:
    """
    Find JWT encoding/decoding patterns in code.

    Args:
        content: Source code content

    Returns:
        List of (line_number, pattern_type, matched_text) tuples
    """
    patterns = [
        (r'jwt\.encode\s*\([^)]*', "jwt_encode"),
        (r'jwt\.decode\s*\([^)]*', "jwt_decode"),
        (r'PyJWT\.encode\s*\([^)]*', "pyjwt_encode"),
        (r'jose\.jwt\.\w+\s*\([^)]*', "jose_jwt"),
        (r'sign\s*\([^)]*(?:algorithm|alg)[^)]*', "sign_with_algorithm"),
        (r'verify\s*\([^)]*(?:algorithm|alg)[^)]*', "verify_with_algorithm"),
    ]

    matches = []
    lines = content.split("\n")

    for i, line in enumerate(lines, start=1):
        for pattern, pattern_type in patterns:
            match = re.search(pattern, line, re.IGNORECASE)
            if match:
                matches.append((i, pattern_type, match.group(0)))

    return matches


def find_token_expiration(content: str) -> List[Tuple[int, bool, str]]:
    """
    Find JWT token creation and check for expiration claims.

    Args:
        content: Source code content

    Returns:
        List of (line_number, has_expiration, context) tuples
    """
    results = []
    lines = content.split("\n")

    jwt_encode_pattern = re.compile(r'jwt\.encode\s*\(', re.IGNORECASE)
    exp_patterns = [
        r'["\']exp["\']',
        r'["\']expires["\']',
        r'["\']expiration["\']',
        r'timedelta',
        r'datetime\.now\(\)\s*\+',
    ]

    for i, line in enumerate(lines, start=1):
        if jwt_encode_pattern.search(line):
            context_start = max(0, i - 3)
            context_end = min(len(lines), i + 3)
            context = "\n".join(lines[context_start:context_end])

            has_exp = any(re.search(p, context) for p in exp_patterns)
            results.append((i, has_exp, context))

    return results


def extract_algorithm_from_jwt_call(code: str) -> Optional[str]:
    """
    Extract the algorithm parameter from a JWT encode/decode call.

    Args:
        code: Code snippet containing JWT call

    Returns:
        Algorithm name if found, None otherwise
    """
    algorithm_patterns = [
        r'algorithm\s*=\s*["\'](\w+)["\']',
        r'algorithms\s*=\s*\[["\'](\w+)',
        r'["\']alg["\']\s*:\s*["\'](\w+)["\']',
    ]

    for pattern in algorithm_patterns:
        match = re.search(pattern, code, re.IGNORECASE)
        if match:
            return match.group(1)

    return None


def find_session_configuration(content: str) -> List[Tuple[int, str, str]]:
    """
    Find session configuration patterns in code.

    Args:
        content: Source code content

    Returns:
        List of (line_number, config_type, value) tuples
    """
    patterns = [
        (r'SESSION_COOKIE_SECURE\s*=\s*(\w+)', "secure_cookie"),
        (r'SESSION_COOKIE_HTTPONLY\s*=\s*(\w+)', "httponly_cookie"),
        (r'SESSION_COOKIE_SAMESITE\s*=\s*["\']?(\w+)', "samesite"),
        (r'PERMANENT_SESSION_LIFETIME\s*=', "session_lifetime"),
        (r'session\.permanent\s*=\s*(\w+)', "permanent_session"),
        (r'cookie_secure\s*=\s*(\w+)', "cookie_secure"),
        (r'cookie_httponly\s*=\s*(\w+)', "cookie_httponly"),
    ]

    matches = []
    lines = content.split("\n")

    for i, line in enumerate(lines, start=1):
        for pattern, config_type in patterns:
            match = re.search(pattern, line, re.IGNORECASE)
            if match:
                value = match.group(1) if match.lastindex else "present"
                matches.append((i, config_type, value))

    return matches
