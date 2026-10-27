# Development

Run from the add-on root with the exact selected Base checkout:

```bash
mise exec -- make check BASE_REPO=/absolute/path/to/base
```

The tooling project pins SDK `0.14.0` and development-only setup `0.7.0`. Their planned GitHub wheel sources are explicit in [pyproject.toml](../../tooling/pyproject.toml); a release needs those published assets and a genuine committed `tooling/uv.lock`. Candidate wheel installations do not establish release readiness. Never commit local paths or fabricated hashes in a lock.

Required tests exercise the installed setup planner, key preservation, direct Secret mappings, approved browser settings and actual Helm image consumers. Missing setup dependencies or `BASE_REPO` fail, rather than silently skip. CI acquires the manifest's Base prerequisite and runs the same checks. Kubeconform skips missing CRD schemas; rendering is not runtime acceptance.

The existing `tooling-candidate-check` target accepts reviewed wheel paths and SHA-256 hashes for isolated candidate checks. Its temporary local sources and lock remain outside Git. The [common Dockerfile](../../tooling/Dockerfile) installs one locked environment, uses a pinned Python base and runs non-root.
