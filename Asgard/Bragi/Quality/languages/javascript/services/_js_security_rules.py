"""JavaScript security rules (regex-based)."""

import re
from typing import List

from Asgard.Bragi.Quality.languages.javascript.models.js_models import (
    JSFinding,
    JSRuleCategory,
    JSSeverity,
)
from Asgard.Bragi.Quality.utilities.secret_snippet import mask_quoted_literals


def _make_finding(
    file_path: str,
    line_number: int,
    rule_id: str,
    category: JSRuleCategory,
    severity: JSSeverity,
    title: str,
    description: str,
    code_snippet: str = "",
    fix_suggestion: str = "",
) -> JSFinding:
    return JSFinding(
        file_path=file_path,
        line_number=line_number,
        column=0,
        rule_id=rule_id,
        category=category,
        severity=severity,
        title=title,
        description=description,
        code_snippet=code_snippet.rstrip(),
        fix_suggestion=fix_suggestion,
    )


def check_sql_injection(file_path: str, lines: List[str], enabled: bool = True) -> List[JSFinding]:
    """js.sql-injection: template literal or string concat in db query."""
    if not enabled:
        return []
    pattern = re.compile(r'db\.query\s*\(\s*(?:`[^`]*\$\{|"[^"]*"\s*\+|\'[^\']*\'\s*\+)')
    return [
        _make_finding(
            file_path, i + 1, "js.sql-injection",
            JSRuleCategory.SECURITY, JSSeverity.ERROR,
            "SQL Injection via String Concatenation or Template Literal",
            "Building SQL queries with string concatenation or template literals is vulnerable to injection.",
            line, "Use parameterised queries with placeholders."
        )
        for i, line in enumerate(lines) if pattern.search(line)
    ]


def check_hardcoded_credentials(file_path: str, lines: List[str], enabled: bool = True) -> List[JSFinding]:
    """js.hardcoded-credentials: const password or apiKey assigned to a string literal."""
    if not enabled:
        return []
    pattern = re.compile(r'(?:const|let|var)\s+(?:password|passwd|apiKey|api_key|secret|token)\s*=\s*["\'][^"\']{4,}["\']', re.IGNORECASE)
    return [
        _make_finding(
            file_path, i + 1, "js.hardcoded-credentials",
            JSRuleCategory.SECURITY, JSSeverity.ERROR,
            "Hardcoded Credential",
            "Credentials in source code are a security risk.",
            mask_quoted_literals(line), "Use environment variables (process.env.SECRET) instead."
        )
        for i, line in enumerate(lines) if pattern.search(line)
    ]


def check_command_injection(file_path: str, lines: List[str], enabled: bool = True) -> List[JSFinding]:
    """js.command-injection: exec or execSync with template literal containing variable."""
    if not enabled:
        return []
    pattern = re.compile(r'(?:exec|execSync)\s*\(\s*`[^`]*\$\{')
    return [
        _make_finding(
            file_path, i + 1, "js.command-injection",
            JSRuleCategory.SECURITY, JSSeverity.ERROR,
            "Command Injection via Template Literal",
            "Passing user-controlled data to exec/execSync allows arbitrary command execution.",
            line, "Use execFile with an argument array, never shell interpolation."
        )
        for i, line in enumerate(lines) if pattern.search(line)
    ]


# Browser DOM sinks: assigning anything but a literal to innerHTML/outerHTML, or
# calling document.write with anything but a literal.
_XSS_DOM_SINK = re.compile(
    # The negative lookahead excludes whitespace as well as the quote characters.
    # Without that, `\s*` backtracks to zero width, the lookahead then sees a
    # space rather than the quote that follows it, and `x.innerHTML = "literal"`
    # matches -- a false positive the original single-sink version of this rule
    # carried.
    r'(?:\.(?:inner|outer)HTML\s*=\s*(?![\s"\'`])|document\.write(?:ln)?\s*\(\s*(?![\s"\'`]))'
)

# React's explicit escape hatch from JSX escaping -- the direct analogue of Go's
# template.HTML() cast, which go.xss already flags.
_XSS_REACT_SINK = re.compile(r'dangerouslySetInnerHTML')

# Server response sinks. res.write/res.end/res.send write straight into the
# response body with no escaping of any kind, so a non-literal argument is the
# server-side equivalent of the innerHTML case above.
_XSS_RESPONSE_SINK = re.compile(
    r'\bres(?:ponse)?\.(?:write|end|send)\s*\(\s*(?![\s"\'`)])'
)

# The same response calls, plus header writes, carrying request-derived data on
# the same line -- the direct analogue of php.xss's `echo $_GET`.
_XSS_REQUEST_ECHO = re.compile(
    r'\bres(?:ponse)?\.(?:write|writeHead|end|send|setHeader)\s*\([^)]*\breq(?:uest)?\.'
)


def check_xss(file_path: str, lines: List[str], enabled: bool = True) -> List[JSFinding]:
    """js.xss: unescaped output to a browser DOM sink or an HTTP response body."""
    if not enabled:
        return []
    findings = []
    for i, line in enumerate(lines):
        if len(line) > 4096:
            # Minified bundles produce one enormous line whose every construct
            # matches something. php.xss skips these for the same reason.
            continue
        if _XSS_DOM_SINK.search(line) or _XSS_REACT_SINK.search(line):
            findings.append(_make_finding(
                file_path, i + 1, "js.xss",
                JSRuleCategory.SECURITY, JSSeverity.ERROR,
                "Cross-Site Scripting (XSS) via a DOM sink",
                "Writing unsanitised data to innerHTML, outerHTML, document.write or "
                "dangerouslySetInnerHTML enables XSS attacks.",
                line, "Use textContent instead of innerHTML, or sanitise input with DOMPurify."
            ))
        elif _XSS_RESPONSE_SINK.search(line) or _XSS_REQUEST_ECHO.search(line):
            findings.append(_make_finding(
                file_path, i + 1, "js.xss",
                JSRuleCategory.SECURITY, JSSeverity.ERROR,
                "Cross-Site Scripting (XSS) via an HTTP response body",
                "res.write/res.end/res.send emit their argument into the response body "
                "verbatim, with no escaping. Writing a non-literal value -- especially one "
                "derived from the request -- into an HTML response enables XSS.",
                line, "Render through a template that escapes by default, or escape the "
                      "value explicitly before writing it."
            ))
    return findings


def check_path_traversal(file_path: str, lines: List[str], enabled: bool = True) -> List[JSFinding]:
    """js.path-traversal: fs.readFile or fs.readFileSync with req. variable."""
    if not enabled:
        return []
    pattern = re.compile(r'fs\.(?:readFile|readFileSync)\s*\([^)]*req\.')
    return [
        _make_finding(
            file_path, i + 1, "js.path-traversal",
            JSRuleCategory.SECURITY, JSSeverity.ERROR,
            "Path Traversal via User-Controlled File Path",
            "Using request parameters directly in file-read calls allows path traversal.",
            line, "Validate and sanitise the path; use path.resolve() and check it stays within the expected root."
        )
        for i, line in enumerate(lines) if pattern.search(line)
    ]


def check_weak_crypto(file_path: str, lines: List[str], enabled: bool = True) -> List[JSFinding]:
    """js.weak-crypto: crypto.createHash with md5 or sha1."""
    if not enabled:
        return []
    pattern = re.compile(r"crypto\.createHash\s*\(\s*['\"](?:md5|sha1)['\"]", re.IGNORECASE)
    return [
        _make_finding(
            file_path, i + 1, "js.weak-crypto",
            JSRuleCategory.SECURITY, JSSeverity.ERROR,
            "Weak Cryptographic Hash Algorithm",
            "MD5 and SHA1 are cryptographically broken and should not be used for security purposes.",
            line, "Use crypto.createHash('sha256') or stronger, or bcrypt for passwords."
        )
        for i, line in enumerate(lines) if pattern.search(line)
    ]


def check_no_prototype_pollution(file_path: str, lines: List[str], enabled: bool = True) -> List[JSFinding]:
    """js.no-prototype-pollution: __proto__ assignment."""
    if not enabled:
        return []
    pattern = re.compile(r'__proto__\s*=')
    return [
        _make_finding(
            file_path, i + 1, "js.no-prototype-pollution",
            JSRuleCategory.SECURITY, JSSeverity.ERROR,
            "Prototype Pollution via __proto__ Assignment",
            "Assigning to __proto__ can pollute the prototype chain and cause security vulnerabilities.",
            line, "Use Object.create(null) for safe property maps and avoid __proto__ assignments."
        )
        for i, line in enumerate(lines) if pattern.search(line)
    ]


_SECURITY_RULES = [
    check_sql_injection,
    check_hardcoded_credentials,
    check_command_injection,
    check_xss,
    check_path_traversal,
    check_weak_crypto,
    check_no_prototype_pollution,
]
