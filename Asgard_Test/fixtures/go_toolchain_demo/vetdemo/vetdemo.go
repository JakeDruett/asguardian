// Deliberately contains a go vet finding (Printf format/argument mismatch)
// for Asgard's Go toolchain-orchestration tests. Kept in its own package,
// away from main_test.go, so it does not interfere with the go-test
// fixture (see the note in ../main.go).
package vetdemo

import "fmt"

func BadPrintf() {
	fmt.Printf("count: %d\n", "not-a-number")
}
