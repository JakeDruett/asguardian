# CWE-330: Use of Insufficiently Random Values (random for a security token)
# OWASP: A02 Cryptographic Failures
# Expected scanner: Heimdall CryptographicValidationService
# Expected severity: HIGH

import random
import string


def session_token():
    return "".join(random.choice(string.ascii_letters) for _ in range(32))
