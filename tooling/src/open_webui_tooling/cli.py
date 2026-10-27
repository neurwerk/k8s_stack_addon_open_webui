"""Validate Open WebUI definitions using the shared public parser."""

import argparse
from pathlib import Path

from k8s_stack_tooling.addons import ContractError, load_manifest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path, help="Open WebUI repository")
    parser.add_argument("--list-packages", action="store_true")
    args = parser.parse_args(argv)
    try:
        addon = load_manifest(args.root / "release/manifest.yaml")
        if addon.metadata.name != "open-webui":
            raise ContractError("expected the Open WebUI add-on")
    except ContractError as exc:
        parser.exit(1, f"{exc}\n")
    if args.list_packages:
        for package in addon.spec.packages:
            print(package.path)
    else:
        print("Open WebUI definition schema is valid")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
