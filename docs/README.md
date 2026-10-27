# Open WebUI

- [Architecture](architecture/README.md): product ownership and direct credential delivery.
- [Development](development/README.md): locked dependencies and required integration checks.
- [Operations](operations/README.md): approvals, delivery ordering and release gates.

The [release manifest](../release/manifest.yaml) owns prerequisites and package definitions. Clients own immutable source selection, approvals and Flux order.
