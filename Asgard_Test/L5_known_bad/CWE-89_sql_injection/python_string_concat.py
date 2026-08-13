# CWE-89: SQL Injection via string concatenation
# OWASP: A03 Injection
# Expected scanner: Heimdall InjectionDetectionService
# Expected severity: CRITICAL


def get_user(cursor, username):
    query = "SELECT * FROM users WHERE name = '" + username + "'"
    cursor.execute(query)
    return cursor.fetchall()
