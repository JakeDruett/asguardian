# CWE-22: Path Traversal via unvalidated user path joined to base dir
# OWASP: A01 Broken Access Control
# Expected scanner: Heimdall PathTraversalScanner
# Expected severity: HIGH

import os


def read_file(request):
    filename = request.args.get("file")
    path = os.path.join("/var/data", filename)
    with open(path) as handle:
        return handle.read()
