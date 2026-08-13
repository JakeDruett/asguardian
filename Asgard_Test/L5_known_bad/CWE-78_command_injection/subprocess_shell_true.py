# CWE-78: OS Command Injection via shell=True with user input
# OWASP: A03 Injection
# Expected scanner: Heimdall InjectionDetectionService
# Expected severity: CRITICAL

import subprocess


def run_tool(user_arg):
    subprocess.call("convert " + user_arg + " out.png", shell=True)
