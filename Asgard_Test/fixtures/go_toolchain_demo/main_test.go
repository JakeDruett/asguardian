// Deliberately contains one passing and one failing test for Asgard's Go
// toolchain-orchestration tests (go test -json parsing).
package main

import "testing"

func TestAddPasses(t *testing.T) {
	if Add(2, 3) != 5 {
		t.Fatal("Add(2, 3) should be 5")
	}
}

func TestAddFailsOnPurpose(t *testing.T) {
	if Add(2, 2) != 5 {
		t.Errorf("Add(2, 2) = %d, want %d", Add(2, 2), 5)
	}
}
