# CWE-79: Reflected XSS via unescaped user input in an HTML response
# OWASP: A03 Injection
# Expected scanner: Heimdall InjectionDetectionService / FrontendSecurityScanner
# Expected severity: HIGH


def search(request):
    term = request.args.get("q", "")
    return "<html><body>Results for " + term + "</body></html>"
