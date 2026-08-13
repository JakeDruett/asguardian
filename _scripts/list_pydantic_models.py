#!/usr/bin/env python3
"""
List every public Pydantic model defined inside the Asgard package.

The output (one ``module.ClassName`` per line, sorted, deterministic) is the
denominator for L3 contract-test coverage tracking — see
``_Docs/Planning/TestCoverage/L3_Plan.md`` Phase 1.

Usage:
    python3 _scripts/list_pydantic_models.py            # print to stdout
    python3 _scripts/list_pydantic_models.py | wc -l    # count models
"""

import importlib
import inspect
import pkgutil
import sys
from pathlib import Path

# Make the repo root importable regardless of the caller's cwd.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def iter_public_models():
    import Asgard
    from pydantic import BaseModel

    seen = set()
    for module_info in pkgutil.walk_packages(Asgard.__path__, Asgard.__name__ + "."):
        try:
            mod = importlib.import_module(module_info.name)
        except Exception:
            # Optional dependencies / platform-specific modules: skip,
            # never fail the inventory.
            continue
        for name, obj in inspect.getmembers(mod, inspect.isclass):
            if name.startswith("_"):
                continue
            try:
                if not (issubclass(obj, BaseModel) and obj is not BaseModel):
                    continue
            except TypeError:
                continue
            if obj.__module__ != mod.__name__:
                continue  # only report where the model is defined
            qualified = f"{obj.__module__}.{name}"
            if qualified not in seen:
                seen.add(qualified)
                yield qualified


def main() -> int:
    for qualified in sorted(iter_public_models()):
        print(qualified)
    return 0


if __name__ == "__main__":
    sys.exit(main())
