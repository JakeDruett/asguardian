"""CHC-0008: OpenAPI/compat YAML alias cycles do not recurse forever."""

import yaml

from Asgard.Forseti.Compatibility.utilities.compat_utils import collect_refs
from Asgard.Forseti.OpenAPI.utilities._openapi_spec_utils import get_all_refs, iter_refs


def _cyclic_mapping():
    return yaml.safe_load("a: &a\n  b: *a\n")


def test_collect_refs_survives_self_alias():
    acc: set[str] = set()
    collect_refs(_cyclic_mapping(), acc)
    assert acc == set()


def test_get_all_refs_survives_self_alias():
    assert get_all_refs(_cyclic_mapping()) == set()


def test_iter_refs_survives_self_alias():
    assert list(iter_refs(_cyclic_mapping())) == []
