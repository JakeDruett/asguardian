// Deliberately mis-formatted (irregular spacing) for Asgard's Go
// toolchain-orchestration tests (gofmt drift + go test failure fixture).
// The go vet fixture lives in ./vetdemo instead of here, since `go test`
// itself runs a default vet pass on a package before building its test
// binary -- keeping the vet-triggering code in the same package as
// main_test.go's deliberately failing test would make the test binary fail
// to build at all, which is a different, already-covered fixture shape.
package main

import "fmt"

func   Add(a, b int) int   {
	return a+b
}

func main() {
	fmt.Println(Add(2, 3))
}
