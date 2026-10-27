# neurwerk.base - Open WebUI Add-on

The Open WebUI add-on packages Open WebUI for neurwerk.base with shared identity, AI gateway access, and PostgreSQL integration. See the [neurwerk.base website](https://base.neurwerk.com/) for more information.

## Stack

| Repository | Purpose |
| --- | --- |
| [Base](https://github.com/neurwerk/k8s_stack_base) | Shared platform charts and release packages. |
| [Studio](https://github.com/neurwerk/k8s_stack_studio) | Platform dashboard and API. |
| [Tooling](https://github.com/neurwerk/k8s_stack_tooling) | Setup automation, operational tools, and operations image. |
| [PII Engine](https://github.com/neurwerk/k8s_stack_pii_engine) | Personal-information detection and safety policies. |
| [Gateway Processor](https://github.com/neurwerk/k8s_stack_agentgateway_extproc) | Connects gateway traffic to the PII Engine. |
| [API Key Bridge](https://github.com/neurwerk/k8s_stack_keycloak_api_key_bridge) | Issues and validates API keys using Keycloak permissions. |
| [Keycloak Theme](https://github.com/neurwerk/k8s_stack_keycloak_theme) | Keycloak login and email themes. |

## Add-ons

Optional products are packaged separately from Base. See each repository's documentation and release manifest for availability and prerequisites.

| Repository | Purpose |
| --- | --- |
| [Dify](https://github.com/neurwerk/k8s_stack_addon_dify) | Dify deployment and API/web customizations. |
| [LibreChat](https://github.com/neurwerk/k8s_stack_addon_librechat) | LibreChat deployment and platform integration. |
| [Open WebUI](https://github.com/neurwerk/k8s_stack_addon_open_webui) | Open WebUI deployment and platform integration. **(this repository)** |
| [Pipecat](https://github.com/neurwerk/k8s_stack_addon_pipecat) | Self-hosted voice bots and browser UI with platform identity and AI gateway integration. |

## Examples

| Repository | Purpose |
| --- | --- |
| [Example Client](https://github.com/neurwerk/k8s_stack_client_example_com) | Example client settings and Flux deployment setup. |

## Documentation

See [Repository documentation](docs/README.md) and the [release manifest](release/manifest.yaml).

## Contributing and support

Use [GitHub Issues](https://github.com/neurwerk/k8s_stack_addon_open_webui/issues) for reproducible bugs and focused feature requests. See the [development guide](docs/development/README.md) before proposing changes.

## Security

Report vulnerabilities privately through [GitHub security advisories](https://github.com/neurwerk/k8s_stack_addon_open_webui/security/advisories/new).

## Licensing

This repository does not currently include a project license or third-party notices file; do not assume its contents are MIT-licensed. The upstream Open WebUI application has its own [license](https://github.com/open-webui/open-webui/blob/main/LICENSE); consult the license for the application version selected in the [release manifest](release/manifest.yaml).
