"""
Shared parsing for the `go build`/`go vet` diagnostic line format.

Both tools report compiler/vet diagnostics in the same textual shape:
``<file>:<line>:<column>: <message>``, with file paths relative to the
module directory the tool was invoked from. Multi-package runs additionally
emit a ``# <import path>`` header line before each package's diagnostics,
purely for human grouping -- it carries no information the file path does
not already, so it is skipped rather than parsed.

Verified against real `go build`/`go vet` output (go1.24.7 and go1.25.1,
this sandbox) for: a Printf format-verb mismatch (vet), an undefined
identifier (build), a cross-module `replace` directive pointing at a path
that does not exist on a fresh checkout (build, no `#` header -- this is
the exact failure GAIA/Keryx/go.mod's `replace gaia/lexicon => ../Lexicon/
LexiconGo` produces from outside a GAIA/Lexicon checkout), and a malformed
go.mod (a one-line `go: errors parsing go.mod: ...` message with no
file:line:col shape at all, which must not be silently read as zero
diagnostics).
"""

import re
from pathlib import Path
from typing import List, NamedTuple

_DIAGNOSTIC_RE = re.compile(r"^(?P<file>[^\s:][^:]*):(?P<line>\d+):(?P<column>\d+):\s*(?P<message>.+)$")


class GoDiagnostic(NamedTuple):
    """A single parsed `<file>:<line>:<col>: <message>` line."""
    file_path: str
    line_number: int
    column: int
    message: str


def parse_diagnostics(output: str, module_dir: Path, root: Path) -> List[GoDiagnostic]:
    """
    Parse every `file:line:col: message` line in *output*.

    Lines that do not match the shape (package `# ...` headers, bare
    `go: ...` tooling errors, blank lines) are skipped -- callers must
    treat a nonzero exit with zero parsed diagnostics as a tool failure,
    not a clean run, since that shape mismatch is exactly what a fatal
    non-per-file error (a malformed go.mod, an unresolved module) looks
    like.
    """
    diagnostics: List[GoDiagnostic] = []
    for line in output.splitlines():
        match = _DIAGNOSTIC_RE.match(line.strip())
        if not match:
            continue
        file_str = match.group("file")
        try:
            absolute = (module_dir / file_str).resolve()
            relative_path = str(absolute.relative_to(root))
        except ValueError:
            relative_path = file_str
        diagnostics.append(
            GoDiagnostic(
                file_path=relative_path,
                line_number=int(match.group("line")),
                column=int(match.group("column")),
                message=match.group("message").strip(),
            )
        )
    return diagnostics
