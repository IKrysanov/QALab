"""Фабрика официального Kubernetes Python client для OpenShift."""

from __future__ import annotations

from .config import OpenShiftConfig
from .exceptions import (
    OpenShiftConfigurationError,
    OpenShiftDependencyError,
)
from .protocols import CoreV1Service, KubernetesApiClient


class KubernetesOpenShiftServiceFactory:
    """Создаёт изолированный ``ApiClient`` без глобальной конфигурации SDK."""

    def create(
            self,
            config: OpenShiftConfig,
    ) -> tuple[CoreV1Service, KubernetesApiClient]:
        try:
            from kubernetes import client, config as kube_config
            from kubernetes.config.config_exception import ConfigException
        except ImportError as exc:
            raise OpenShiftDependencyError(
                "kubernetes is required for OpenShiftClient; "
                "install project requirements"
            ) from exc

        configuration = client.Configuration()
        try:
            if config.auth_mode == "in_cluster":
                kube_config.load_incluster_config(
                    client_configuration=configuration,
                )
            elif config.auth_mode == "kubeconfig":
                kube_config.load_kube_config(
                    config_file=config.kubeconfig_path,
                    context=config.context,
                    client_configuration=configuration,
                    persist_config=False,
                )
            else:
                if (
                        config.kubeconfig_path is not None
                        or config.context is not None
                ):
                    kube_config.load_kube_config(
                        config_file=config.kubeconfig_path,
                        context=config.context,
                        client_configuration=configuration,
                        persist_config=False,
                    )
                else:
                    try:
                        kube_config.load_incluster_config(
                            client_configuration=configuration,
                        )
                    except ConfigException:
                        configuration = client.Configuration()
                        kube_config.load_kube_config(
                            client_configuration=configuration,
                            persist_config=False,
                        )
        except Exception as exc:
            raise OpenShiftConfigurationError(
                "Failed to load Kubernetes authentication configuration: "
                f"mode={config.auth_mode!r}, cause_type={type(exc).__name__}"
            ) from exc

        if config.verify_ssl is not None:
            configuration.verify_ssl = config.verify_ssl
        if config.ssl_ca_cert is not None:
            configuration.ssl_ca_cert = config.ssl_ca_cert
        # Polling-ретраи принадлежат OpenShiftClient и ограничены wait_timeout.
        # Скрытые urllib3 retries умножают задержку каждого polling-вызова,
        # а при неверном CA создают впечатление бесконечного повтора.
        configuration.retries = 0

        api_client = client.ApiClient(configuration=configuration)
        return client.CoreV1Api(api_client), api_client
