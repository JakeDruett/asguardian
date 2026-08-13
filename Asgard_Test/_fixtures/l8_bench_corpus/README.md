# L8 Benchmark Corpus

Small, fully synthetic repository used only for L8 performance budgeting
(`Asgard_Test/L8_PerfBudgets/test_corpus_and_self_scan.py`). The code is
deliberately seeded with scanner-relevant constructs (string-built SQL,
subprocess calls, weak hashes, fake-looking credentials) so scanners do real
work instead of fast-path skipping.

Everything here is fake: no credential is real, no code is executed by any
test. Do not "fix" the vulnerabilities — the corpus content is part of the
benchmark's determinism.
