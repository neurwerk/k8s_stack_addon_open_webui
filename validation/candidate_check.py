"""Check local wheels in isolation; this does not create an installable release lock."""

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import tempfile
import tomllib
from email.parser import BytesParser
from pathlib import Path
from zipfile import ZipFile


def wheel_info(path: Path, expected_hash: str | None = None) -> dict[str, str]:
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    if expected_hash is not None and digest != expected_hash:
        raise ValueError("candidate wheel hash mismatch")
    with ZipFile(path) as wheel:
        metadata = BytesParser().parsebytes(
            wheel.read(
                next(name for name in wheel.namelist() if name.endswith(".dist-info/METADATA"))
            )
        )
    return {
        "name": metadata["Name"],
        "version": metadata["Version"],
        "sha256": digest,
        "path": str(path),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tooling-wheel", type=Path, required=True)
    parser.add_argument("--tooling-sha256", required=True)
    parser.add_argument("--setup-wheel", type=Path, required=True)
    parser.add_argument("--setup-sha256", required=True)
    parser.add_argument("--base", type=Path, required=True)
    parser.add_argument("--python", default="3.12")
    args = parser.parse_args()
    if os.geteuid() == 0:
        parser.error("run the candidate check as a non-root user")
    root = Path(__file__).resolve().parents[1]
    work = Path(tempfile.mkdtemp(prefix="webui-candidate-", dir="/tmp/opencode"))
    env = {
        key: value
        for key, value in os.environ.items()
        if key not in {"PYTHONPATH", "PYTHONHOME", "VIRTUAL_ENV"}
    }
    env.update(
        PYTHONDONTWRITEBYTECODE="1",
        BASE_REPO=str(args.base.resolve()),
        UV_LINK_MODE="copy",
    )

    def run(argv: list[str], *, required: bool = True) -> int:
        result = subprocess.run(argv, cwd=work, env=env, check=False)
        if required and result.returncode:
            raise SystemExit(result.returncode)
        return result.returncode

    wheels = [
        wheel_info(args.tooling_wheel.resolve(), args.tooling_sha256),
        wheel_info(args.setup_wheel.resolve(), args.setup_sha256),
    ]
    shutil.copytree(
        root / "tooling",
        work / "product",
        ignore=shutil.ignore_patterns(
            ".venv", "__pycache__", ".pytest_cache", ".ruff_cache", "dist"
        ),
    )
    run(["uv", "build", "--wheel", str(work / "product"), "--out-dir", str(work / "dist")])
    wheels.append(wheel_info(next((work / "dist").glob("*.whl"))))
    project = tomllib.loads((root / "tooling/pyproject.toml").read_text())
    dependencies = [f"{item['name']}=={item['version']}" for item in wheels]
    # These explicit uv sources and their generated lock exist only outside Git.
    config = (
        '[project]\nname="webui-candidate-check"\nversion="0.0.0"\nrequires-python=">=3.12"\ndependencies='
        + json.dumps(dependencies + project["dependency-groups"]["dev"])
        + "\n[tool.uv.sources]\n"
    )
    for item in wheels:
        config += f"{json.dumps(item['name'])} = {{ path = {json.dumps(item['path'])} }}\n"
    (work / "pyproject.toml").write_text(config)
    run(["uv", "sync", "--no-editable", "--python", args.python])
    binary = work / ".venv/bin"
    evidence = {
        "wheels": wheels,
        "uid": os.geteuid(),
        "definitionSha256": hashlib.sha256(
            (root / "release/manifest.yaml").read_bytes()
        ).hexdigest(),
        "baseManifestSha256": hashlib.sha256(
            (args.base / "release/manifest.yaml").read_bytes()
        ).hexdigest(),
        "checks": {},
    }
    print(json.dumps({"candidate": str(work), **evidence}, indent=2), flush=True)
    commands = {
        "installed-imports": [
            str(binary / "python"),
            "-I",
            "-c",
            "import pathlib,sys,open_webui_tooling,k8s_stack_tooling,openbao_stack_setup; "
            "prefix=pathlib.Path(sys.prefix); "
            "modules=(open_webui_tooling,k8s_stack_tooling,openbao_stack_setup); "
            "assert all(pathlib.Path(m.__file__).is_relative_to(prefix) for m in modules); "
            "print(*(m.__file__ for m in modules),sep='\\n')",
        ],
        "installed-command": [str(binary / "open-webui-validate"), str(root)],
        "definition-and-base": [
            str(binary / "addon-check"),
            str(root),
            "--base",
            str(args.base.resolve()),
        ],
        "lint": [
            str(binary / "ruff"),
            "check",
            "--config",
            str(root / "tooling/pyproject.toml"),
            str(root / "tooling"),
            str(root / "validation/candidate_check.py"),
        ],
        "format": [
            str(binary / "ruff"),
            "format",
            "--check",
            "--config",
            str(root / "tooling/pyproject.toml"),
            str(root / "tooling"),
            str(root / "validation/candidate_check.py"),
        ],
        "types": [
            str(binary / "ty"),
            "check",
            "--project",
            str(root / "tooling"),
            "--python",
            str(binary / "python"),
        ],
        "tests": [
            str(binary / "python"),
            "-I",
            "-m",
            "pytest",
            "-p",
            "no:cacheprovider",
            str(root / "tooling/tests"),
            "-q",
        ],
    }
    for name, command in commands.items():
        evidence["checks"][name] = run(command, required=False)
    readonly = work / "readonly"
    (readonly / "release").mkdir(parents=True)
    shutil.copyfile(root / "release/manifest.yaml", readonly / "release/manifest.yaml")
    for tree in (work / ".venv", readonly):
        for path in tree.rglob("*"):
            if not path.is_symlink():
                path.chmod(0o555 if path.is_dir() or path.stat().st_mode & 0o111 else 0o444)
        tree.chmod(0o555)
    env["HOME"] = str(readonly)
    evidence["checks"]["nonroot-readonly-command"] = run(
        [str(binary / "open-webui-validate"), str(readonly)], required=False
    )
    (work / "evidence.json").write_text(json.dumps(evidence, indent=2) + "\n")
    print(f"Candidate evidence: {work / 'evidence.json'}", flush=True)
    raise SystemExit(int(any(evidence["checks"].values())))


if __name__ == "__main__":
    main()
