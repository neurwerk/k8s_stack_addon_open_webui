"""Exercise the product definition with the real, separately packaged setup planner."""

from pathlib import Path
from unittest.mock import Mock

import pytest
from k8s_stack_tooling.addons import load_manifest
from openbao_stack_setup import client as client_module
from openbao_stack_setup import declarative

ROOT = Path(__file__).resolve().parents[2]


def test_definition_retry_preserves_keys_and_scoped_readers() -> None:
    addon = load_manifest(ROOT / "release/manifest.yaml")
    setups = {addon.metadata.name: addon.spec.setup}
    snapshots = {}
    client = Mock(spec=client_module.OpenBaoClient)
    client.read_secret.side_effect = snapshots.get
    initial = declarative.plan_credentials(client, setups)
    assert initial.added_fields == 5
    assert len(initial.writes) == 3
    # Simulate interruption after one record; the engine must preserve that record.
    first = initial.writes[0]
    snapshots[first.path] = client_module.SecretRecord(values=first.values, version=1)
    resumed = declarative.plan_credentials(client, setups)
    assert first.path not in {write.path for write in resumed.writes}
    for write in resumed.writes:
        snapshots[write.path] = client_module.SecretRecord(values=write.values, version=1)
    retained = {path: dict(record.values) for path, record in snapshots.items()}
    retry = declarative.plan_credentials(client, setups)
    assert retry.added_fields == 0
    assert not retry.writes
    assert retained == {path: record.values for path, record in snapshots.items()}
    readers = {
        reader.role: set(reader.records) for reader in declarative.compose_readers(setups)
    }
    assert readers["auth-keycloak"] == {"addons/open-webui/oidc"}
    assert readers["infra-postgres-operations"] == {"addons/open-webui/database"}
    assert readers["addon-open-webui-runtime"] == set(snapshots)
    assert "frontend-open-webui" not in readers
    assert not declarative.handover_definitions(setups, {})
    # Invalid retained encryption material must fail rather than silently regenerate.
    snapshots["addons/open-webui/runtime"].values["oauthClientInfoEncryptionKey"] = "invalid"
    with pytest.raises(client_module.OpenBaoError):
        declarative.plan_credentials(client, setups)
    client.write_secret.assert_not_called()
