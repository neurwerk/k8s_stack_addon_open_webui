"""Product preservation and integration with the public definition interface."""

import json
import os
import subprocess
from pathlib import Path

import pytest
import yaml
from k8s_stack_tooling.addons import (
    ContractError,
    check,
    load_manifest,
    resolve_browser_identity,
)
from k8s_stack_tooling.addons.helm_images import validate_helm_images
from k8s_stack_tooling.addons.validation import render as render_package

from open_webui_tooling.cli import main

ROOT = Path(__file__).resolve().parents[2]


def render(
    chart: Path, *values: Path, namespace: str = "frontend-open-webui"
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            "helm",
            "template",
            "open-webui-test",
            str(chart),
            "--namespace",
            namespace,
            *[arg for path in values for arg in ("--values", str(path))],
        ],
        capture_output=True,
        text=True,
        check=False,
        timeout=60,
    )


def test_product_definition_uses_shared_validation(capsys: pytest.CaptureFixture[str]) -> None:
    assert main([str(ROOT)]) == 0
    assert "definition schema is valid" in capsys.readouterr().out
    check(ROOT)
    check(ROOT, installable=True)


def test_direct_delivery_preserves_application_keys_without_helm_credentials() -> None:
    resources = list(
        yaml.safe_load_all((ROOT / "releases/open-webui/secret-sync/runtime.yaml").read_text())
    )
    external = next(item for item in resources if item["kind"] == "ExternalSecret")
    store = next(item for item in resources if item["kind"] == "SecretStore")
    auth = store["spec"]["provider"]["vault"]["auth"]["kubernetes"]
    assert auth["role"] == "addon-open-webui-runtime"
    assert auth["serviceAccountRef"]["name"] == "frontend-open-webui-external-secrets"
    target = external["spec"]["target"]
    assert target["name"] == "frontend-open-webui-secret"
    assert target["creationPolicy"] == "Owner"
    assert target["deletionPolicy"] == "Retain"
    assert target["template"]["mergePolicy"] == "Merge"
    assert not target["template"].get("data")
    assert not target["template"].get("templateFrom")
    mapping = {
        row["secretKey"]: (row["remoteRef"]["key"], row["remoteRef"]["property"])
        for row in external["spec"]["data"]
    }
    assert mapping == {
        "DATABASE_PASSWORD": ("addons/open-webui/database", "password"),
        "OAUTH_CLIENT_SECRET": ("addons/open-webui/oidc", "clientSecret"),
        "WEBUI_SECRET_KEY": ("addons/open-webui/runtime", "webuiSecretKey"),
        "OAUTH_SESSION_TOKEN_ENCRYPTION_KEY": (
            "addons/open-webui/runtime",
            "oauthSessionTokenEncryptionKey",
        ),
        "OAUTH_CLIENT_INFO_ENCRYPTION_KEY": (
            "addons/open-webui/runtime",
            "oauthClientInfoEncryptionKey",
        ),
    }
    result = render(ROOT / "charts/open-webui/shared", ROOT / "validation/helm-values.yaml")
    assert result.returncode == 0, result.stderr
    assert all(item["kind"] != "Secret" for item in yaml.safe_load_all(result.stdout))
    app = render(ROOT / "charts/open-webui/app", ROOT / "validation/helm-values.yaml")
    assert app.returncode == 0, app.stderr
    deployment = next(
        item for item in yaml.safe_load_all(app.stdout) if item["kind"] == "Deployment"
    )
    container = deployment["spec"]["template"]["spec"]["containers"][0]
    assert {"secretRef": {"name": target["name"]}} in container["envFrom"]
    assert (
        deployment["metadata"]["annotations"]["secret.reloader.stakater.com/reload"]
        == target["name"]
    )


def test_shared_chart_rejects_retired_secret_values(tmp_path: Path) -> None:
    retired = tmp_path / "retired.yaml"
    retired.write_text("frontendOpenWebuiSecrets: {}\n")
    result = render(
        ROOT / "charts/open-webui/shared", ROOT / "validation/helm-values.yaml", retired
    )
    assert result.returncode != 0
    assert "frontendOpenWebuiSecrets" in result.stderr


def test_model_modes_leave_mcp_authentication_unchanged(tmp_path: Path) -> None:
    mcp = tmp_path / "mcp.yaml"
    mcp.write_text(
        "frontendOpenWebui:\n  mcp:\n    enabled: true\n    servers: [sample]\n"
        "mcp-servers:\n  enabled: true\n  catalog:\n    custom:\n"
        "      - {name: sample, enabled: true, contextforge: false}\n"
    )
    result = render(
        ROOT / "charts/open-webui/shared", ROOT / "validation/helm-values.yaml", mcp
    )
    assert result.returncode == 0, result.stderr
    config = next(
        item for item in yaml.safe_load_all(result.stdout) if item["kind"] == "ConfigMap"
    )
    connections = json.loads(config["data"]["OPENAI_API_CONFIGS"])
    models = {model: entry for entry in connections.values() for model in entry["model_ids"]}
    assert models["local-model"]["headers"] == {"X-Neurwerk-Credential-Mode": "none"}
    assert models["example-chat"]["headers"] == {"X-Neurwerk-Credential-Mode": "global"}
    assert "example-personal-chat" not in models
    servers = json.loads(config["data"]["TOOL_SERVER_CONNECTIONS"])
    assert len(servers) == 1
    assert servers[0]["headers"] == {"X-Session-ID": "{{CHAT_ID}}"}


def test_actual_package_images_with_nonsecret_values_only() -> None:
    base_path = os.environ.get("BASE_REPO")
    if not base_path:
        pytest.fail("BASE_REPO is required for candidate Base integration")
    base = Path(base_path)
    addon = load_manifest(ROOT / "release/manifest.yaml")
    packages = {
        package.name: render_package(ROOT / package.path, root=ROOT)
        for package in addon.spec.packages
    }
    configmaps = {
        (item["metadata"]["namespace"], item["metadata"]["name"]): item
        for resources in packages.values()
        for item in resources
        if item["kind"] == "ConfigMap"
    }
    values = yaml.safe_load((ROOT / "validation/helm-values.yaml").read_text())
    approval = yaml.safe_load((ROOT / "validation/oidc-approval-values.yaml").read_text())
    # Explicit synthetic approvals, with real Base defaults and generated settings.
    inputs = {
        ("auth-keycloak", "auth-keycloak-app-defaults"): yaml.safe_load(
            (base / "releases/keycloak/app-defaults.yaml").read_text()
        ),
        ("auth-keycloak", "client-values"): values,
        ("auth-keycloak", "keycloak-product-values"): {
            "authKeycloak": approval["authKeycloak"]
        },
        ("auth-keycloak", "open-webui-oidc-approval-values"): {
            "clientApproval": approval["clientApproval"]
        },
        ("frontend-open-webui", "client-values"): values,
        ("frontend-open-webui", "open-webui-product-values"): {},
        ("frontend-open-webui", "open-webui-agentgateway-model-values"): {},
        ("frontend-open-webui", "client-openrouter-catalog-values"): {},
        ("infra-cert-manager", "client-values"): values,
    }
    for (namespace, name), data in inputs.items():
        configmaps[(namespace, name)] = {
            "apiVersion": "v1",
            "kind": "ConfigMap",
            "metadata": {"namespace": namespace, "name": name},
            "data": {"values.yaml": yaml.safe_dump(data)},
        }
    settings = render(
        ROOT / "charts/open-webui/oidc",
        ROOT / "validation/helm-values.yaml",
        ROOT / "validation/oidc-approval-values.yaml",
        namespace="auth-keycloak",
    )
    assert settings.returncode == 0, settings.stderr
    configmaps[("auth-keycloak", "open-webui-oidc-settings")] = yaml.safe_load(settings.stdout)
    for resources in packages.values():
        for resource in resources:
            if resource["kind"] == "HelmRelease":
                assert all(
                    ref["kind"] == "ConfigMap" for ref in resource["spec"].get("valuesFrom", [])
                )
    validate_helm_images(
        addon,
        packages,
        sources={
            ("GitRepository", "flux-system", "k8s-stack"): base,
            ("GitRepository", "flux-system", "open-webui-addon"): ROOT,
        },
        configmaps=configmaps,
        kube_version="1.34.1",
        api_versions=(
            "gateway.networking.k8s.io/v1",
            "external-secrets.io/v1",
            "policy.cert-manager.io/v1alpha1",
        ),
    )


@pytest.mark.parametrize(
    "missing", [None, "redirectUris", "webOrigins", "postLogoutRedirectUris"]
)
def test_oidc_settings_require_exact_client_approval(
    tmp_path: Path, missing: str | None
) -> None:
    base = os.environ.get("BASE_REPO")
    if not base:
        pytest.fail("BASE_REPO is required for candidate Base integration")
    settings = render(
        ROOT / "charts/open-webui/oidc",
        ROOT / "validation/helm-values.yaml",
        namespace="auth-keycloak",
    )
    assert settings.returncode == 0, settings.stderr
    generated = yaml.safe_load(settings.stdout)["data"]["values.yaml"]
    values = tmp_path / "settings.yaml"
    values.write_text(generated)
    approval = yaml.safe_load((ROOT / "validation/oidc-approval-values.yaml").read_text())
    release = yaml.safe_load((ROOT / "releases/open-webui/oidc/oidc.yaml").read_text())
    approval.update(release["spec"]["values"])
    if missing:
        approval["clientApproval"][missing] = []
    approved = tmp_path / "approval.yaml"
    approved.write_text(yaml.safe_dump(approval))
    identity = load_manifest(ROOT / "release/manifest.yaml").spec.identities[0]
    effective = {**yaml.safe_load(generated), **approval}
    if missing:
        with pytest.raises(ContractError):
            resolve_browser_identity(identity, effective)
    else:
        resolved = resolve_browser_identity(identity, effective)
        assert resolved.browser is not None
        assert resolved.browser.redirect_uris == approval["clientApproval"]["redirectUris"]
    result = render(
        Path(base) / "charts/keycloak/addon-oidc", values, approved, namespace="auth-keycloak"
    )
    if missing:
        assert result.returncode != 0
        assert "approv" in result.stderr.lower()
    else:
        assert result.returncode == 0, result.stderr
        job = next(item for item in yaml.safe_load_all(result.stdout) if item["kind"] == "Job")
        env = {
            entry["name"]: entry.get("value")
            for entry in job["spec"]["template"]["spec"]["containers"][0]["env"]
        }
        assert env["KC_REDIRECT_URIS"] == env["KC_APPROVED_REDIRECT_URIS"]
        assert env["KC_WEB_ORIGINS"] == env["KC_APPROVED_WEB_ORIGINS"]
        assert (
            env["KC_POST_LOGOUT_REDIRECT_URIS"] == env["KC_APPROVED_POST_LOGOUT_REDIRECT_URIS"]
        )
