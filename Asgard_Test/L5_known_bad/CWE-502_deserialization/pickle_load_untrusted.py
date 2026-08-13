# CWE-502: Deserialization of Untrusted Data via pickle.loads
# OWASP: A08 Software and Data Integrity Failures
# Expected scanner: Heimdall DeserializationScanner
# Expected severity: CRITICAL

import pickle


def deserialize(user_data):
    return pickle.loads(user_data)
