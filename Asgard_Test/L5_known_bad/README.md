# L5 Known-Bad Fixture Library

Canonical library of minimal known-bad samples, one directory per CWE.
Every fixture is a **ground truth**: the mapped scanner MUST produce the
expected finding when run against it. If a scanner stops flagging its
fixture, the scanner is broken — never adjust the fixture to quiet a test.

Rules:

- Each fixture is < 30 lines and carries a header comment identifying the
  CWE and the expected detection signature.
- Fixture directories are named `<CWE-id>_<slug>`.
- Tests must scan fixtures **from a neutral temp dir** (`tempfile.mkdtemp`)
  or via content-based APIs — never from pytest `tmp_path` and never with a
  path containing `test`, so test-context suppression heuristics cannot mute
  the finding.
- Every fixture must be listed in the manifest below (enforced by
  `Asgard_Test/L5_Meta/test_regulatory_mapping.py`).

## Manifest

| Fixture | CWE | Reference | Expected scanner | Expected finding |
|---|---|---|---|---|
| CWE-89_sql_injection/python_string_concat.py | CWE-89 | OWASP A03 | Heimdall InjectionDetectionService | SQL injection, CRITICAL |
| CWE-78_command_injection/subprocess_shell_true.py | CWE-78 | OWASP A03 | Heimdall InjectionDetectionService | Command injection, CRITICAL |
| CWE-79_xss/flask_unescaped_response.py | CWE-79 | OWASP A03 | Heimdall Injection/Frontend scanners | Reflected XSS, HIGH |
| CWE-22_path_traversal/open_user_path.py | CWE-22 | OWASP A01 | Heimdall PathTraversalScanner | Path traversal, HIGH |
| CWE-502_deserialization/pickle_load_untrusted.py | CWE-502 | OWASP A08 | Heimdall DeserializationScanner | Unsafe pickle.loads, CRITICAL |
| CWE-798_hardcoded_secrets/aws_access_key.py | CWE-798 | OWASP A07 | Heimdall SecretsDetectionService | Hardcoded AWS credentials, CRITICAL |
| CWE-327_weak_crypto/md5_password.py | CWE-327 | OWASP A02 | Heimdall CryptographicValidationService | MD5 password hashing, HIGH |
| CWE-330_weak_random/random_token.py | CWE-330 | OWASP A02 | Heimdall CryptographicValidationService | Non-CSPRNG token, HIGH |
| CWE-918_ssrf/requests_user_url.py | CWE-918 | OWASP A10 | Heimdall SSRFXXEScanner | SSRF via user URL, HIGH |
| CWE-319_cleartext_transmission/mixed_content_page.html | CWE-319 | OWASP A02 | Freya scan_static_dom | Active mixed content |
| CWE-250_unnecessary_privileges/Dockerfile.root_user | CWE-250 | CIS-Docker-4.1 | Volundr DockerfileValidator | DL3002 root user (+ DL3007 latest tag) |
| CWE-250_unnecessary_privileges/k8s_privileged_deployment.yaml | CWE-250 | CIS-K8s-5.2.1 | Volundr KubernetesValidator | privileged-container ERROR |
| CWE-284_improper_access_control/terraform_open_security_group.tf | CWE-284 | CIS-AWS-5.2 | Volundr TerraformValidator | VOL-TF-0005 / VOL-TF-0006 |
| CWE-311_missing_encryption/terraform_unencrypted_rds.tf | CWE-311 | CIS-AWS-2.3.1 | Volundr TerraformValidator | VOL-TF-0004 |
| CWE-94_code_injection/github_workflow_script_injection.yml | CWE-94 | CIS-SupplyChain-1.3 | Volundr find_untrusted_interpolations | untrusted `github.event.*` interpolation |
| CWE-439_behavioral_change/openapi_v1.json | CWE-439 | SemVer/OpenAPI | Forseti CompatEngineService | baseline (pair) |
| CWE-439_behavioral_change/openapi_v2_removed_field.json | CWE-439 | SemVer/OpenAPI | Forseti CompatEngineService | removed field → breaking, FAILED |
| CWE-439_behavioral_change/schema_v1.sql | CWE-439 | — | Forseti SchemaDiffService | baseline (pair) |
| CWE-439_behavioral_change/schema_v2_dropped_column.sql | CWE-439 | — | Forseti SchemaDiffService | DROP COLUMN → has_breaking_changes |
