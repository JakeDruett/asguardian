// Deliberately contains type errors for Asgard's Node toolchain-orchestration tests.
function add(a: number, b: number): number {
  return a + b;
}

const result: string = add(1, 2);
console.log(undeclaredIdentifier);
