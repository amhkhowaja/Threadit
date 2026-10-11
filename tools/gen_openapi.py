from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from services.post_read.app import create_app as read_app
from services.post_write.app import create_app as write_app

_SPEC_PATH = Path(__file__).resolve().parents[1] / "openapi" / "v1.json"


def build_spec() -> dict[str, Any]:
    write = write_app().openapi()
    read = read_app().openapi()

    paths: dict[str, Any] = {}
    for source in (write, read):
        for path, item in source["paths"].items():
            if path == "/healthz":
                continue
            paths.setdefault(path, {}).update(item)

    components = {}
    for source in (write, read):
        components.update(source.get("components", {}).get("schemas", {}))

    return {
        "openapi": "3.1.0",
        "info": {"title": "Threadit API", "version": "1.0.0"},
        "paths": dict(sorted(paths.items())),
        "components": {"schemas": dict(sorted(components.items()))},
    }


def main() -> None:
    spec = build_spec()
    _SPEC_PATH.parent.mkdir(parents=True, exist_ok=True)
    _SPEC_PATH.write_text(json.dumps(spec, indent=2, sort_keys=True) + "\n")
    print(f"wrote {_SPEC_PATH}")


if __name__ == "__main__":
    main()
