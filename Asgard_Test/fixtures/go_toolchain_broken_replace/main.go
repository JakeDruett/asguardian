// Deliberately references a `replace` directive that points at a relative
// sibling path guaranteed never to exist on disk, for Asgard's Go
// toolchain-orchestration tests (go build compile-failure fixture).
//
// This replaces a fixture that used to point GoBuildAnalyzer at the real
// GAIA/Keryx checkout, whose own go.mod replaces gaia/lexicon with a
// relative sibling path that only fails to resolve when GAIA and Lexicon
// are cloned as true siblings under the same parent directory -- a layout
// this sandbox does not always have (see TestGoBuildRealKeryxFailure's own
// history: a Lexicon checkout appearing nested under GAIA/ made that
// replace resolve and the "known failing" build start succeeding, an
// accident of sandbox layout rather than a change in GoBuildAnalyzer's
// correctness). This fixture reproduces the same class of real compiler
// failure -- an unresolved relative `replace` path, a genuine `go build`
// exit and stderr, not a synthetic ToolFinding -- without depending on
// what else happens to be checked out alongside this repository.
package main

import missingdep "example.com/asguardian-fixture-missing-dep"

func main() {
	missingdep.DoSomething()
}
