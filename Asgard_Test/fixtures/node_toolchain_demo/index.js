// Deliberately contains ESLint violations for Asgard's Node toolchain-orchestration tests.
function dangerouslyRun(input) {
  eval(input);
  var flag = 1;
  if (flag == 1) {
    console.log("one");
  }
  let unusedVariable = 5;
}
module.exports = dangerouslyRun;
