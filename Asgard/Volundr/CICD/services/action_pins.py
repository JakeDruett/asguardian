"""
Curated SHA pin-map for well-known GitHub Actions.

Mutable tag references (``actions/checkout@v4``) are a supply-chain attack
vector: tags can be force-pushed to point at malicious commits (see the
March 2026 TeamPCP tag-poisoning incident against trivy-action). Every
``uses:`` reference the generator emits is therefore resolved to a full
40-character commit SHA, with the human-readable tag preserved as a
trailing comment.

The pin map below is curated data refreshed at release time (pair the
generated workflows with the Renovate config snippet from
``renovate_pin_config()`` to keep pins current). Unknown actions supplied
by the user are passed through unchanged and surface as a
``VOL-CICD-0002`` finding unless already SHA-pinned or suppressed.
"""

import re
from typing import Dict, Optional, Tuple

# tag-ref -> (full commit SHA, resolved version comment)
# NOTE: refreshed at release time; see module docstring.
KNOWN_ACTION_PINS: Dict[str, Tuple[str, str]] = {
    "actions/checkout@v4": ("11bd71901bbe5b1630ceea73d27597364c9af683", "v4.2.2"),
    "actions/checkout@v5": ("08c6903cd8c0fde910a37f88322edcfb5dd907a8", "v5.0.0"),
    "actions/setup-python@v5": ("a26af69be951a213d495a4c3e4e4022e16d87065", "v5.6.0"),
    "actions/setup-node@v4": ("49933ea5288caeca8642d1e84afbd3f7d6820020", "v4.4.0"),
    "actions/cache@v4": ("5a3ec84eff668545956fd18022155c47e93e2684", "v4.2.3"),
    "actions/upload-artifact@v4": ("ea165f8d65b6e75b540449e92b4886f43607fa02", "v4.6.2"),
    "actions/download-artifact@v4": ("d3f86a106a0bac45b974a628896c90dbdf5c8093", "v4.3.0"),
    "actions/attest-build-provenance@v2": ("e8998f949152b193b063cb0ec769d69d929409be", "v2.4.0"),
    "docker/build-push-action@v5": ("4a13e500e55cf31b7a5d59a38ab2040ab0f42f56", "v5.1.0"),
    "docker/build-push-action@v6": ("263435318d21b8e681c14492fe198d362a7d2c83", "v6.18.0"),
    "docker/login-action@v3": ("74a5d142397b4f367a81961eba4e8cd7edddf772", "v3.4.0"),
    "docker/setup-buildx-action@v3": ("b5ca514318bd6ebac0fb2aedd5d36ec1b5c232a2", "v3.10.0"),
    "aws-actions/configure-aws-credentials@v4": ("b47578312673ae6fa5b5096b330d9fbac3d116df", "v4.2.1"),
    "google-github-actions/auth@v2": ("ba79af03959ebeac9769e648f473a284504d9193", "v2.1.10"),
    "azure/login@v2": ("a457da9ea143d694b1b9c7c869ebb04ebe844ef5", "v2.3.0"),
    "hashicorp/vault-action@v3": ("7709c609789c5e27b757a85817483caadbb5939a", "v3.3.0"),
    "step-security/harden-runner@v2": ("0634a2670c59f64b4a01f0f96f84700a4088b9f0", "v2.12.0"),
    "anchore/sbom-action@v0": ("e11c554f704a0b820cbf8c51673f6945e0731532", "v0.20.0"),
    "pypa/gh-action-pypi-publish@release/v1": (
        "dc37677b2e1c63e2034f94d8a5b11f265b73ba33",
        "v1.14.2",
    ),
    "pypa/gh-action-pypi-publish@v1": (
        "dc37677b2e1c63e2034f94d8a5b11f265b73ba33",
        "v1.14.2",
    ),
    "github/codeql-action/upload-sarif@v3": (
        "f3712979fa5f215279b101dd0a2e3bdfb4353324",
        "v3.37.7",
    ),
}

_SHA_RE = re.compile(r"^[0-9a-f]{40}$")
_DIGEST_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
_FLOATING_IMAGE_TAGS = frozenset({"latest", "current"})
_PRIVILEGED_TRUE = frozenset({"true", "yes", "1", "on"})
_PRIVILEGED_OPT_RE = re.compile(r"(?:^|\s)--privileged(?:\s|=|$)")

# image ref -> (canonical name:tag, digest). Refreshed at release time.
KNOWN_IMAGE_PINS: Dict[str, Tuple[str, str]] = {
    "ubuntu:24.04": (
        "ubuntu:24.04",
        "sha256:561618e2c15bf2397621dd04f96926663a3b5616c189cf7e38db7e82f5c538ea",
    ),
    "ubuntu:latest": (
        "ubuntu:24.04",
        "sha256:561618e2c15bf2397621dd04f96926663a3b5616c189cf7e38db7e82f5c538ea",
    ),
    "ubuntu:22.04": (
        "ubuntu:22.04",
        "sha256:3b06811b2afd352be909dd088a004166d665dc76d38b13eada33522a9d915c6f",
    ),
    "ubuntu:20.04": (
        "ubuntu:20.04",
        "sha256:8feb4d8ca5354def3d8fce243717141ce31e2c428701f6682bd2fafe15388214",
    ),
    "cimg/base:current": (
        "cimg/base:current",
        "sha256:e8f07526f593ac5dee29362b7f98c6fec94c412722d6bbece731e4cc885abccb",
    ),
    "rhysd/actionlint:1.7.7": (
        "rhysd/actionlint:1.7.7",
        "sha256:887a259a5a534f3c4f36cb02dca341673c6089431057242cdc931e9f133147e9",
    ),
}


def is_digest_pinned(image: str) -> bool:
    """True if the container image is pinned to a sha256 digest."""
    if "@" not in image:
        return False
    return bool(_DIGEST_RE.match(image.rsplit("@", 1)[1].lower()))


def is_floating_image_tag(image: str) -> bool:
    """True for untagged images or mutable ``:latest`` / ``:current`` tags."""
    if is_digest_pinned(image):
        return False
    name = image.split("@", 1)[0].rsplit("/", 1)[-1]
    if ":" not in name:
        return True
    return name.rsplit(":", 1)[1].lower() in _FLOATING_IMAGE_TAGS


def pin_container_image(image: str, *, require_digest: bool = False) -> str:
    """Rewrite a known image to ``name:tag@sha256:…``; reject floating tags.

    Versioned tags that are not in the pin map pass through unless
    ``require_digest`` is set (used for ``docker://`` action refs).
    """
    text = (image or "").strip()
    if not text:
        raise ValueError("image reference must not be empty")
    if is_digest_pinned(text):
        return text
    pin = KNOWN_IMAGE_PINS.get(text)
    if pin is not None:
        name, digest = pin
        return f"{name}@{digest}"
    if is_floating_image_tag(text):
        raise ValueError(f"Refusing floating image tag: {image}")
    if require_digest:
        raise ValueError(f"Refusing image not pinned by digest: {image}")
    return text


def _is_privileged_flag(value: object) -> bool:
    if value is True:
        return True
    if isinstance(value, str) and value.strip().lower() in _PRIVILEGED_TRUE:
        return True
    return False


def service_requests_privileged(spec: object) -> bool:
    """True if a GHA/GitLab service spec enables privileged mode."""
    if not isinstance(spec, dict):
        return False
    if _is_privileged_flag(spec.get("privileged")):
        return True
    options = spec.get("options")
    if isinstance(options, str) and _PRIVILEGED_OPT_RE.search(options):
        return True
    if isinstance(options, dict) and _is_privileged_flag(options.get("privileged")):
        return True
    return False


def harden_service_map(services: Dict[str, object]) -> Dict[str, object]:
    """Reject privileged service containers and pin/reject floating images."""
    if not services:
        return services
    hardened: Dict[str, object] = {}
    for name, spec in services.items():
        if service_requests_privileged(spec):
            raise ValueError(f"Refusing privileged service '{name}'")
        if isinstance(spec, str):
            hardened[name] = pin_container_image(spec)
            continue
        if isinstance(spec, dict) and spec.get("image"):
            pinned_spec = dict(spec)
            pinned_spec["image"] = pin_container_image(str(spec["image"]))
            hardened[name] = pinned_spec
            continue
        hardened[name] = spec
    return hardened


def is_sha_pinned(uses: str) -> bool:
    """True if the ``uses:`` ref is a 40-char commit SHA or a docker digest."""
    if uses.startswith("docker://"):
        return is_digest_pinned(uses[len("docker://"):])
    if "@" not in uses:
        return False
    ref = uses.rsplit("@", 1)[1]
    return bool(_SHA_RE.match(ref.lower()))


def resolve_action_ref(uses: str) -> Tuple[str, Optional[str]]:
    """Resolve a ``uses:`` reference against the curated pin map.

    Returns ``(pinned_ref, version_comment)``. Local actions (``./...``)
    pass through. ``docker://`` refs are digest-pinned from
    ``KNOWN_IMAGE_PINS`` (unknown unpinned docker refs raise). Already
    SHA-pinned refs pass through unchanged (comment ``None``). Known
    mutable tags are rewritten to their SHA with the tag returned as the
    version comment. Unknown mutable tags pass through unchanged (the
    validation engine flags them as VOL-CICD-0002).
    """
    if uses.startswith("./"):
        return uses, None
    if uses.startswith("docker://"):
        pinned_image = pin_container_image(
            uses[len("docker://"):], require_digest=True
        )
        return f"docker://{pinned_image}", None
    if is_sha_pinned(uses):
        return uses, None
    pin = KNOWN_ACTION_PINS.get(uses)
    if pin is None:
        return uses, None
    sha, version = pin
    action = uses.rsplit("@", 1)[0]
    return f"{action}@{sha}", version


def pinned(action_tag: str) -> str:
    """Return the SHA-pinned form of a known action tag (for generator use)."""
    ref, _ = resolve_action_ref(action_tag)
    return ref


def version_comment(action_tag: str) -> Optional[str]:
    """Return the version comment for a known action tag, if any."""
    pin = KNOWN_ACTION_PINS.get(action_tag)
    return pin[1] if pin else None


def annotate_pinned_uses(rendered_yaml: str) -> str:
    """Append ``# vX.Y.Z`` comments to SHA-pinned ``uses:`` lines.

    PyYAML cannot emit comments, so the version-comment half of the
    pinning contract is applied as a post-processing pass over the
    rendered text.
    """
    sha_to_version = {
        sha: (tag.rsplit("@", 1)[0], version)
        for tag, (sha, version) in KNOWN_ACTION_PINS.items()
    }
    out_lines = []
    for line in rendered_yaml.splitlines():
        stripped = line.strip()
        if stripped.startswith("uses:") or stripped.startswith("- uses:"):
            for sha, (action, version) in sha_to_version.items():
                if f"{action}@{sha}" in line and "#" not in line:
                    line = f"{line}  # {version}"
                    break
        out_lines.append(line)
    return "\n".join(out_lines) + ("\n" if rendered_yaml.endswith("\n") else "")


def renovate_pin_config() -> str:
    """Renovate config snippet keeping SHA pins current (paired output)."""
    return (
        '{\n'
        '  "$schema": "https://docs.renovatebot.com/renovate-schema.json",\n'
        '  "extends": ["config:best-practices", "helpers:pinGitHubActionDigests"],\n'
        '  "packageRules": [\n'
        '    {\n'
        '      "matchManagers": ["github-actions"],\n'
        '      "pinDigests": true\n'
        '    }\n'
        '  ]\n'
        '}\n'
    )
