# CWE-327: Use of a Broken or Risky Cryptographic Algorithm (MD5 for passwords)
# OWASP: A02 Cryptographic Failures
# Expected scanner: Heimdall CryptographicValidationService
# Expected severity: HIGH

import hashlib


def hash_password(password):
    return hashlib.md5(password.encode()).hexdigest()
