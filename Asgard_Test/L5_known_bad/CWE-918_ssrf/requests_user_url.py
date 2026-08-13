# CWE-918: Server-Side Request Forgery via user-controlled URL
# OWASP: A10 Server-Side Request Forgery
# Expected scanner: Heimdall SSRFXXEScanner
# Expected severity: HIGH

import requests


def fetch(request):
    url = request.args.get("url")
    return requests.get(url).text
