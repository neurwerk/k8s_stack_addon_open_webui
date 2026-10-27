# Architecture

Open WebUI uses shared identity, gateway and PostgreSQL services. Product charts supply nonsecret settings and Secret references. External Secrets reads canonical add-on records and directly produces `frontend-open-webui-secret`; credentials never enter Helm values.

The runtime SecretStore uses `addon-open-webui-runtime` with the existing ServiceAccount and SecretStore names. Database and browser identity delivery use composed Base readers. The product tooling package contains a thin validator; shared Tooling owns parsing, credential reconciliation, access and lifecycle operations.

See the [manifest](../../release/manifest.yaml) for exact readers, outputs, images and restart targets.
