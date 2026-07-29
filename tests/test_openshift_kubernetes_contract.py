from pathlib import Path
from unittest.mock import patch

import pytest

from src.openshift import OpenShiftClient, OpenShiftConfig
from src.openshift.kubernetes_factory import (
    KubernetesOpenShiftServiceFactory,
)


@pytest.fixture
def kubeconfig_path(tmp_path: Path) -> Path:
    path = tmp_path / "config"
    path.write_text(
        """
apiVersion: v1
kind: Config
clusters:
  - name: qa
    cluster:
      server: https://cluster.example.test:6443
      insecure-skip-tls-verify: true
contexts:
  - name: qa
    context:
      cluster: qa
      namespace: ignored-by-client
      user: qa
current-context: qa
users:
  - name: qa
    user:
      token: test-token
""".strip(),
        encoding="utf-8",
    )
    return path


@pytest.mark.parametrize("auth_mode", ["kubeconfig", "auto"])
def test_factory_builds_isolated_official_kubernetes_client(
        kubeconfig_path,
        auth_mode,
):
    from kubernetes import client as kubernetes_client

    original = kubeconfig_path.read_text(encoding="utf-8")
    default_host = (
        kubernetes_client.Configuration.get_default_copy().host
    )
    config = OpenShiftConfig(
        namespace="airflow",
        auth_mode=auth_mode,
        kubeconfig_path=str(kubeconfig_path),
        context="qa",
        verify_ssl=True,
    )

    core_api, api_client = (
        KubernetesOpenShiftServiceFactory().create(config)
    )
    try:
        assert isinstance(core_api, kubernetes_client.CoreV1Api)
        assert api_client.configuration.host == (
            "https://cluster.example.test:6443"
        )
        assert api_client.configuration.verify_ssl is True
        assert api_client.configuration.api_key["authorization"] == (
            "Bearer test-token"
        )
    finally:
        api_client.close()

    assert kubeconfig_path.read_text(encoding="utf-8") == original
    assert (
        kubernetes_client.Configuration.get_default_copy().host
        == default_host
    )


def test_delete_uid_precondition_matches_generated_sdk_contract():
    from kubernetes import client as kubernetes_client

    api_client = kubernetes_client.ApiClient()
    core_api = kubernetes_client.CoreV1Api(api_client)
    openshift = OpenShiftClient(
        OpenShiftConfig(namespace="airflow"),
        core_api=core_api,
    )

    try:
        with patch.object(
                api_client,
                "call_api",
                return_value=kubernetes_client.V1Pod(),
        ) as call_api:
            openshift.delete_pod(
                "scheduler-42",
                grace_period_seconds=0,
                expected_uid="uid-42",
            )
    finally:
        api_client.close()

    request = call_api.call_args
    assert request.args[:2] == (
        "/api/v1/namespaces/{namespace}/pods/{name}",
        "DELETE",
    )
    assert request.kwargs["body"] == {
        "apiVersion": "v1",
        "kind": "DeleteOptions",
        "preconditions": {"uid": "uid-42"},
    }
    assert request.kwargs["_request_timeout"] == (5.0, 30.0)
