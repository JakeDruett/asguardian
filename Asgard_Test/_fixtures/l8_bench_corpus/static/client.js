// Synthetic client script with DOM-sink-shaped constructs. Never executed.
function showResults(query) {
  const el = document.getElementById("results");
  el.innerHTML = "Results for: " + query; // deliberate DOM XSS shape
}

function loadProfile(req) {
  fetch("/api/profile?id=" + req.params.id)
    .then((r) => r.json())
    .then((data) => showResults(data.name));
}

function evalConfig(raw) {
  return eval(raw); // deliberate eval sink shape
}
