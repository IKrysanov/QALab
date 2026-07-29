import json
import logging
from io import StringIO
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from src.openshift import (
    CommandResult,
    OpenShiftClient,
    OpenShiftClientClosedError,
    OpenShiftCommandFailedError,
    OpenShiftConfig,
    OpenShiftConfigurationError,
    OpenShiftContainerSelectionError,
    OpenShiftOperationError,
    OpenShiftPodSelectionError,
    OpenShiftWaitTimeoutError,
)
from src.openshift.executor import (
    KubernetesPodExecutor,
    PodExecTransportOutputTooLargeError,
    PodExecTransportTimeoutError,
)
from utils.logger import StructuredJsonFormatter, log_event


class FakeApiError(Exception):
    def __init__(
            self,
            status: int,
            reason: str,
            *,
            headers=None,
    ):
        self.status = status
        self.reason = reason
        self.headers = headers or {}


class FakeClock:
    def __init__(self):
        self.current = 0.0
        self.sleeps = []

    def monotonic(self):
        return self.current

    def sleep(self, seconds):
        self.sleeps.append(seconds)
        self.current += seconds


class FakeApiClient:
    def __init__(self):
        self.close_calls = 0
        self.close_error = None

    def close(self):
        self.close_calls += 1
        if self.close_error is not None:
            raise self.close_error


class FakeCoreApi:
    def __init__(self):
        self.calls = []
        self.list_responses = []
        self.read_responses = []
        self.list_error = None
        self.read_error = None
        self.delete_error = None
        self.log_error = None
        self.logs = "pod logs"

    def list_namespaced_pod(self, namespace, **kwargs):
        self.calls.append(("list_namespaced_pod", namespace, kwargs))
        if self.list_error is not None:
            raise self.list_error
        pods = self.list_responses.pop(0) if self.list_responses else []
        return SimpleNamespace(items=pods)

    def read_namespaced_pod(self, name, namespace, **kwargs):
        self.calls.append(("read_namespaced_pod", name, namespace, kwargs))
        if self.read_error is not None:
            raise self.read_error
        if self.read_responses:
            response = self.read_responses.pop(0)
            if isinstance(response, Exception):
                raise response
            return response
        raise FakeApiError(404, "Not Found")

    def delete_namespaced_pod(self, name, namespace, **kwargs):
        self.calls.append(("delete_namespaced_pod", name, namespace, kwargs))
        if self.delete_error is not None:
            raise self.delete_error
        return SimpleNamespace()

    def read_namespaced_pod_log(self, name, namespace, **kwargs):
        self.calls.append((
            "read_namespaced_pod_log",
            name,
            namespace,
            kwargs,
        ))
        if self.log_error is not None:
            raise self.log_error
        return self.logs

    def connect_post_namespaced_pod_exec(
            self,
            name,
            namespace,
            **kwargs,
    ):
        raise AssertionError(
            "connect_post_namespaced_pod_exec must be called through stream"
        )


class FakePodExecutor:
    def __init__(self):
        self.calls = []
        self.error = None
        self.exit_code = 0
        self.stdout = "command output\n"
        self.stderr = ""

    def execute(
            self,
            namespace,
            pod_name,
            container_name,
            command,
            *,
            timeout,
            output_limit_bytes,
    ):
        self.calls.append((
            namespace,
            pod_name,
            container_name,
            tuple(command),
            timeout,
            output_limit_bytes,
        ))
        if self.error is not None:
            raise self.error
        return CommandResult(
            namespace=namespace,
            pod_name=pod_name,
            container_name=container_name,
            command=tuple(command),
            stdout=self.stdout,
            stderr=self.stderr,
            exit_code=self.exit_code,
            duration_seconds=0.25,
        )


class FakeServiceFactory:
    def __init__(self, core_api, api_client):
        self.core_api = core_api
        self.api_client = api_client
        self.configs = []

    def create(self, config):
        self.configs.append(config)
        return self.core_api, self.api_client


def make_pod(
        name,
        uid,
        *,
        namespace="airflow",
        phase="Running",
        ready=True,
        terminating=False,
        labels=None,
        restart_count=0,
        managed=True,
        controller_name="airflow-scheduler",
        controller_uid="controller-uid",
        containers=("scheduler",),
):
    created_at = datetime(2026, 7, 29, tzinfo=timezone.utc)
    return SimpleNamespace(
        metadata=SimpleNamespace(
            name=name,
            namespace=namespace,
            uid=uid,
            labels=labels or {"app": "airflow-scheduler"},
            owner_references=(
                [
                    SimpleNamespace(
                        kind="ReplicaSet",
                        name=controller_name,
                        uid=controller_uid,
                        controller=True,
                    ),
                ]
                if managed
                else []
            ),
            creation_timestamp=created_at,
            deletion_timestamp=created_at if terminating else None,
        ),
        spec=SimpleNamespace(
            containers=[
                SimpleNamespace(name=container)
                for container in containers
            ],
            node_name="worker-1",
        ),
        status=SimpleNamespace(
            phase=phase,
            conditions=[
                SimpleNamespace(
                    type="Ready",
                    status="True" if ready else "False",
                ),
            ],
            container_statuses=[
                SimpleNamespace(restart_count=restart_count),
            ],
            pod_ip="10.0.0.42",
            start_time=created_at,
            reason=None,
            message=None,
        ),
    )


@pytest.fixture
def config():
    return OpenShiftConfig(
        namespace="airflow",
        connect_timeout=2.0,
        read_timeout=7.0,
        wait_timeout=10.0,
        poll_interval=1.0,
        log_limit_bytes=4096,
    )


@pytest.fixture
def core_api():
    return FakeCoreApi()


@pytest.fixture
def clock():
    return FakeClock()


@pytest.fixture
def client(config, core_api, clock):
    return OpenShiftClient(
        config,
        core_api=core_api,
        clock=clock,
    )


def test_config_normalizes_values():
    config = OpenShiftConfig(
        namespace=" airflow ",
        auth_mode="KUBECONFIG",
        kubeconfig_path=" /tmp/config ",
        context=" qa ",
    )

    assert config.namespace == "airflow"
    assert config.auth_mode == "kubeconfig"
    assert config.kubeconfig_path == "/tmp/config"
    assert config.context == "qa"
    assert config.request_timeout == (5.0, 30.0)


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"namespace": ""}, "namespace"),
        ({"namespace": 42}, "namespace"),
        ({"namespace": "qa", "auth_mode": "token"}, "auth_mode"),
        ({"namespace": "qa", "verify_ssl": "false"}, "verify_ssl"),
        (
            {
                "namespace": "qa",
                "auth_mode": "in_cluster",
                "context": "qa",
            },
            "in_cluster",
        ),
        (
            {
                "namespace": "qa",
                "verify_ssl": False,
                "ssl_ca_cert": "/tmp/ca.pem",
            },
            "ssl_ca_cert",
        ),
        ({"namespace": "qa", "wait_timeout": 0}, "wait_timeout"),
        (
            {"namespace": "qa", "poll_interval": float("nan")},
            "poll_interval",
        ),
        ({"namespace": "qa", "log_limit_bytes": True}, "log_limit_bytes"),
        ({"namespace": "qa", "exec_timeout": 0}, "exec_timeout"),
        (
            {"namespace": "qa", "exec_output_limit_bytes": 0},
            "exec_output_limit_bytes",
        ),
    ],
)
def test_config_rejects_invalid_values(kwargs, message):
    with pytest.raises(OpenShiftConfigurationError, match=message):
        OpenShiftConfig(**kwargs)


def test_context_manager_closes_owned_api(config, core_api):
    api_client = FakeApiClient()
    factory = FakeServiceFactory(core_api, api_client)
    managed_client = OpenShiftClient(
        config,
        service_factory=factory,
    )

    with managed_client as entered:
        assert entered is managed_client
        assert managed_client.closed is False

    assert managed_client.closed is True
    assert api_client.close_calls == 1

    managed_client.close()
    assert api_client.close_calls == 1

    with pytest.raises(OpenShiftClientClosedError, match="airflow"):
        managed_client.list_pods()


def test_context_manager_does_not_close_injected_api(config, core_api):
    api_client = FakeApiClient()
    injected_client = OpenShiftClient(
        config,
        core_api=core_api,
        api_client=api_client,
    )

    with injected_client:
        pass

    assert api_client.close_calls == 0


def test_context_manager_preserves_test_error_if_close_fails(
        config,
        core_api,
):
    api_client = FakeApiClient()
    api_client.close_error = RuntimeError("close failed")
    managed_client = OpenShiftClient(
        config,
        service_factory=FakeServiceFactory(core_api, api_client),
    )

    with pytest.raises(ValueError, match="test failed"):
        with managed_client:
            raise ValueError("test failed")

    assert managed_client.closed is True


def test_list_pods_returns_stable_models(client, core_api):
    core_api.list_responses = [[
        make_pod(
            "scheduler-42",
            "uid-42",
            restart_count=2,
        ),
    ]]

    pods = client.list_pods(
        label_selector="app=airflow-scheduler",
        field_selector="status.phase=Running",
    )

    assert len(pods) == 1
    pod = pods[0]
    assert pod.name == "scheduler-42"
    assert pod.namespace == "airflow"
    assert pod.uid == "uid-42"
    assert pod.ready is True
    assert pod.terminating is False
    assert pod.containers == ("scheduler",)
    assert pod.restart_count == 2
    assert pod.pod_ip == "10.0.0.42"
    assert pod.controller_kind == "ReplicaSet"
    assert pod.controller_name == "airflow-scheduler"
    assert pod.controller_uid == "controller-uid"
    assert core_api.calls == [(
        "list_namespaced_pod",
        "airflow",
        {
            "label_selector": "app=airflow-scheduler",
            "field_selector": "status.phase=Running",
            "_request_timeout": (2.0, 7.0),
        },
    )]


def test_find_pods_filters_ready_pods_by_name_glob(client, core_api):
    core_api.list_responses = [[
        make_pod("airflow-scheduler-7d8c", "uid-scheduler"),
        make_pod("airflow-webserver-a1b2", "uid-ready"),
        make_pod(
            "airflow-webserver-c3d4",
            "uid-pending",
            phase="Pending",
            ready=False,
        ),
    ]]

    pods = client.find_pods(
        "airflow-webserver-*",
        ready_only=True,
    )

    assert [pod.name for pod in pods] == [
        "airflow-webserver-a1b2",
    ]
    assert core_api.calls == [(
        "list_namespaced_pod",
        "airflow",
        {"_request_timeout": (2.0, 7.0)},
    )]


def test_find_pod_rejects_ambiguous_ready_matches(client, core_api):
    core_api.list_responses = [[
        make_pod("airflow-webserver-a1b2", "uid-a"),
        make_pod("airflow-webserver-c3d4", "uid-b"),
    ]]

    with pytest.raises(OpenShiftPodSelectionError) as error:
        client.find_pod("airflow-webserver-*")

    assert error.value.namespace == "airflow"
    assert error.value.name_pattern == "airflow-webserver-*"
    assert error.value.matches == (
        "airflow-webserver-a1b2",
        "airflow-webserver-c3d4",
    )


def test_find_pod_rejects_missing_match(client, core_api):
    core_api.list_responses = [[
        make_pod("airflow-scheduler-a1b2", "uid-a"),
    ]]

    with pytest.raises(OpenShiftPodSelectionError) as error:
        client.find_pod("airflow-webserver-*")

    assert error.value.matches == ()


def test_container_target_resolves_current_pod_before_each_exec(
        config,
        core_api,
        clock,
):
    pod_executor = FakePodExecutor()
    exec_client = OpenShiftClient(
        config,
        core_api=core_api,
        pod_executor=pod_executor,
        clock=clock,
    )
    core_api.list_responses = [
        [
            make_pod(
                "airflow-webserver-old",
                "uid-old",
                containers=("webserver",),
            ),
        ],
        [
            make_pod(
                "airflow-webserver-new",
                "uid-new",
                containers=("webserver",),
            ),
        ],
    ]
    web_server = exec_client.container(
        "airflow-webserver-*",
        container_name="webserver",
    )

    first = web_server.exec(("python", "--version"), check=True)
    second = web_server.sh("test -d /opt/airflow/dags", check=True)

    assert first.succeeded is True
    assert second.succeeded is True
    assert [call[1] for call in pod_executor.calls] == [
        "airflow-webserver-old",
        "airflow-webserver-new",
    ]
    assert pod_executor.calls[0][3] == ("python", "--version")
    assert pod_executor.calls[1][3] == (
        "/bin/sh",
        "-c",
        "test -d /opt/airflow/dags",
    )


def test_container_target_rejects_unknown_container(
        client,
        core_api,
):
    core_api.list_responses = [[
        make_pod(
            "airflow-webserver-a1b2",
            "uid-a",
            containers=("sidecar", "webserver"),
        ),
    ]]
    web_server = client.container(
        "airflow-webserver-*",
        container_name="missing",
    )

    with pytest.raises(OpenShiftContainerSelectionError) as error:
        web_server.exec(("true",))

    assert error.value.available_containers == (
        "sidecar",
        "webserver",
    )


def test_exec_command_returns_stdout_stderr_and_exit_code(
        config,
        core_api,
        clock,
):
    pod_executor = FakePodExecutor()
    pod_executor.stdout = "Airflow 3.0\n"
    exec_client = OpenShiftClient(
        config,
        core_api=core_api,
        pod_executor=pod_executor,
        clock=clock,
    )

    result = exec_client.exec_command(
        "airflow-webserver-a1b2",
        ("airflow", "version"),
        container="webserver",
        timeout=12,
        output_limit_bytes=2048,
    )

    assert result.stdout == "Airflow 3.0\n"
    assert result.stderr == ""
    assert result.exit_code == 0
    assert pod_executor.calls == [(
        "airflow",
        "airflow-webserver-a1b2",
        "webserver",
        ("airflow", "version"),
        12.0,
        2048,
    )]


def test_exec_command_check_raises_with_result(
        config,
        core_api,
        clock,
):
    pod_executor = FakePodExecutor()
    pod_executor.exit_code = 2
    pod_executor.stderr = "command failed"
    exec_client = OpenShiftClient(
        config,
        core_api=core_api,
        pod_executor=pod_executor,
        clock=clock,
    )

    with pytest.raises(OpenShiftCommandFailedError) as error:
        exec_client.exec_command(
            "airflow-webserver-a1b2",
            ("false",),
            container="webserver",
            check=True,
        )

    assert error.value.result.exit_code == 2
    assert error.value.result.stderr == "command failed"


@pytest.mark.parametrize(
    "command",
    ["echo ok", (), (42,), ("", "argument")],
)
def test_exec_command_validates_argv_before_transport(
        config,
        core_api,
        clock,
        command,
):
    pod_executor = FakePodExecutor()
    exec_client = OpenShiftClient(
        config,
        core_api=core_api,
        pod_executor=pod_executor,
        clock=clock,
    )

    with pytest.raises(ValueError, match="command"):
        exec_client.exec_command(
            "airflow-webserver-a1b2",
            command,
            container="webserver",
        )

    assert pod_executor.calls == []


@pytest.mark.parametrize(
    ("transport_error", "expected_error"),
    [
        (
            PodExecTransportTimeoutError("timeout"),
            "OpenShiftCommandTimeoutError",
        ),
        (
            PodExecTransportOutputTooLargeError("large"),
            "OpenShiftCommandOutputTooLargeError",
        ),
    ],
)
def test_exec_command_maps_transport_limits_to_domain_errors(
        config,
        core_api,
        clock,
        transport_error,
        expected_error,
):
    from src import openshift

    pod_executor = FakePodExecutor()
    pod_executor.error = transport_error
    exec_client = OpenShiftClient(
        config,
        core_api=core_api,
        pod_executor=pod_executor,
        clock=clock,
    )

    with pytest.raises(getattr(openshift, expected_error)):
        exec_client.exec_command(
            "airflow-webserver-a1b2",
            ("sleep", "100"),
            container="webserver",
        )


def test_get_pod_requires_running_and_ready_condition(client, core_api):
    core_api.read_responses = [
        make_pod("scheduler-42", "uid-42", phase="Pending", ready=True),
    ]

    pod = client.get_pod("scheduler-42")

    assert pod.phase == "Pending"
    assert pod.ready is False


def test_pod_exists_returns_false_only_for_not_found(client, core_api):
    core_api.read_error = FakeApiError(404, "Not Found")

    assert client.pod_exists("missing") is False


def test_pod_exists_wraps_rbac_error(client, core_api):
    core_api.read_error = FakeApiError(
        403,
        "Forbidden",
        headers={"Audit-Id": "audit-42"},
    )

    with pytest.raises(OpenShiftOperationError) as error:
        client.pod_exists("scheduler-42")

    assert error.value.operation == "read_namespaced_pod"
    assert error.value.status == 403
    assert error.value.reason == "Forbidden"
    assert error.value.request_id == "audit-42"
    assert isinstance(error.value.__cause__, FakeApiError)


def test_read_pod_logs_is_bounded_and_container_aware(client, core_api):
    logs = client.read_pod_logs(
        "scheduler-42",
        container="scheduler",
        previous=True,
        tail_lines=100,
    )

    assert logs == "pod logs"
    assert core_api.calls[-1] == (
        "read_namespaced_pod_log",
        "scheduler-42",
        "airflow",
        {
            "container": "scheduler",
            "previous": True,
            "tail_lines": 100,
            "limit_bytes": 4096,
            "timestamps": True,
            "_request_timeout": (2.0, 7.0),
        },
    )


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"tail_lines": 0}, "tail_lines"),
        ({"limit_bytes": -1}, "limit_bytes"),
        ({"container": ""}, "container"),
        ({"previous": "true"}, "previous"),
        ({"timestamps": 1}, "timestamps"),
    ],
)
def test_read_pod_logs_rejects_invalid_limits(
        client,
        kwargs,
        message,
):
    with pytest.raises(ValueError, match=message):
        client.read_pod_logs("scheduler-42", **kwargs)


def test_delete_pod_passes_bounded_request(client, core_api):
    client.delete_pod(
        "scheduler-42",
        grace_period_seconds=0,
        expected_uid="uid-42",
    )

    assert core_api.calls[-1] == (
        "delete_namespaced_pod",
        "scheduler-42",
        "airflow",
        {
            "body": {
                "apiVersion": "v1",
                "kind": "DeleteOptions",
                "preconditions": {"uid": "uid-42"},
            },
            "grace_period_seconds": 0,
            "_request_timeout": (2.0, 7.0),
        },
    )


@pytest.mark.parametrize("grace_period_seconds", [-1, 1.5, True])
def test_delete_pod_rejects_invalid_grace_period(
        client,
        grace_period_seconds,
):
    with pytest.raises(ValueError, match="grace_period_seconds"):
        client.delete_pod(
            "scheduler-42",
            grace_period_seconds=grace_period_seconds,
        )


@pytest.mark.parametrize("expected_uid", ["", 42])
def test_delete_pod_rejects_invalid_expected_uid(
        client,
        expected_uid,
):
    with pytest.raises(ValueError, match="expected_uid"):
        client.delete_pod(
            "scheduler-42",
            expected_uid=expected_uid,
        )


def test_wait_for_pod_ready_polls_transient_not_found(
        client,
        core_api,
        clock,
):
    core_api.read_responses = [
        FakeApiError(404, "Not Found"),
        make_pod("scheduler-42", "uid-42", phase="Pending", ready=False),
        make_pod("scheduler-42", "uid-42"),
    ]

    pod = client.wait_for_pod_ready(
        "scheduler-42",
        timeout=5,
        poll_interval=1,
    )

    assert pod.ready is True
    assert clock.sleeps == [1, 1]


def test_wait_for_pod_ready_has_diagnostic_timeout(
        client,
        core_api,
        clock,
):
    core_api.read_responses = [
        make_pod("scheduler-42", "uid-42", phase="Pending", ready=False),
        make_pod("scheduler-42", "uid-42", phase="Pending", ready=False),
        make_pod("scheduler-42", "uid-42", phase="Pending", ready=False),
    ]

    with pytest.raises(OpenShiftWaitTimeoutError) as error:
        client.wait_for_pod_ready(
            "scheduler-42",
            timeout=2,
            poll_interval=1,
        )

    assert error.value.timeout == 2
    assert "phase=Pending" in (error.value.last_observed or "")
    assert clock.current == 2


@pytest.mark.parametrize("timeout", [float("nan"), float("inf")])
def test_wait_for_pod_ready_rejects_non_finite_timeout(
        client,
        timeout,
):
    with pytest.raises(ValueError, match="timeout"):
        client.wait_for_pod_ready("scheduler-42", timeout=timeout)


def test_restart_pod_waits_for_uid_absent_before_deletion(
        client,
        core_api,
        clock,
):
    selector = "app=airflow-scheduler"
    target = make_pod("scheduler-a", "uid-a")
    existing_replica = make_pod("scheduler-b", "uid-b")
    replacement_pending = make_pod(
        "scheduler-c",
        "uid-c",
        phase="Pending",
        ready=False,
    )
    replacement_ready = make_pod("scheduler-c", "uid-c")
    core_api.list_responses = [
        [target, existing_replica],
        [existing_replica],
        [existing_replica, replacement_pending],
        [existing_replica, replacement_ready],
    ]

    result = client.restart_pod(
        "scheduler-a",
        label_selector=selector,
        grace_period_seconds=0,
        timeout=5,
        poll_interval=1,
    )

    assert result.previous.uid == "uid-a"
    assert result.replacement.uid == "uid-c"
    assert result.replacement.name == "scheduler-c"
    assert clock.sleeps == [1, 1]
    assert (
        "delete_namespaced_pod",
        "scheduler-a",
        "airflow",
        {
            "body": {
                "apiVersion": "v1",
                "kind": "DeleteOptions",
                "preconditions": {"uid": "uid-a"},
            },
            "grace_period_seconds": 0,
            "_request_timeout": (2.0, 7.0),
        },
    ) in core_api.calls


def test_restart_pod_by_pattern_waits_for_same_controller(
        client,
        core_api,
        clock,
):
    target = make_pod(
        "airflow-webserver-old",
        "uid-old",
        controller_name="airflow-webserver",
        controller_uid="web-controller",
    )
    same_pattern_wrong_controller = make_pod(
        "airflow-webserver-canary",
        "uid-canary",
        controller_name="airflow-webserver-canary",
        controller_uid="canary-controller",
    )
    same_controller_wrong_pattern = make_pod(
        "unrelated-name",
        "uid-unrelated",
        controller_name="airflow-webserver",
        controller_uid="web-controller",
    )
    replacement = make_pod(
        "airflow-webserver-new",
        "uid-new",
        controller_name="airflow-webserver",
        controller_uid="web-controller",
    )
    core_api.list_responses = [
        [target],
        [same_pattern_wrong_controller, same_controller_wrong_pattern],
        [same_pattern_wrong_controller, replacement],
    ]

    result = client.restart_pod_by_pattern(
        "airflow-webserver-*",
        grace_period_seconds=0,
        timeout=5,
        poll_interval=1,
    )

    assert result.previous.name == "airflow-webserver-old"
    assert result.replacement.name == "airflow-webserver-new"
    assert result.replacement.uid == "uid-new"
    assert clock.sleeps == [1]
    assert (
        "delete_namespaced_pod",
        "airflow-webserver-old",
        "airflow",
        {
            "body": {
                "apiVersion": "v1",
                "kind": "DeleteOptions",
                "preconditions": {"uid": "uid-old"},
            },
            "grace_period_seconds": 0,
            "_request_timeout": (2.0, 7.0),
        },
    ) in core_api.calls


def test_restart_pod_by_pattern_does_not_delete_ambiguous_match(
        client,
        core_api,
):
    core_api.list_responses = [[
        make_pod("airflow-webserver-a1b2", "uid-a"),
        make_pod("airflow-webserver-c3d4", "uid-b"),
    ]]

    with pytest.raises(OpenShiftPodSelectionError):
        client.restart_pod_by_pattern("airflow-webserver-*")

    assert not any(
        call[0] == "delete_namespaced_pod"
        for call in core_api.calls
    )


def test_restart_pod_rejects_selector_not_matching_target(
        client,
        core_api,
):
    core_api.list_responses = [[make_pod("scheduler-b", "uid-b")]]

    with pytest.raises(ValueError, match="does not select"):
        client.restart_pod(
            "scheduler-a",
            label_selector="app=airflow-scheduler",
        )


def test_restart_pod_rejects_unmanaged_pod_before_deletion(
        client,
        core_api,
):
    core_api.list_responses = [[
        make_pod("scheduler-a", "uid-a", managed=False),
    ]]

    with pytest.raises(OpenShiftOperationError, match="not managed"):
        client.restart_pod(
            "scheduler-a",
            label_selector="app=airflow-scheduler",
        )

    assert not any(
        call[0] == "delete_namespaced_pod"
        for call in core_api.calls
    )


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"timeout": float("nan")}, "timeout"),
        ({"poll_interval": 0}, "poll_interval"),
        ({"grace_period_seconds": -1}, "grace_period_seconds"),
    ],
)
def test_restart_pod_validates_before_api_calls(
        client,
        core_api,
        kwargs,
        message,
):
    with pytest.raises(ValueError, match=message):
        client.restart_pod(
            "scheduler-a",
            label_selector="app=airflow-scheduler",
            **kwargs,
        )

    assert core_api.calls == []


class FakeExecWebSocket:
    def __init__(self, frames, returncode=0):
        self._frames = list(frames)
        self._stdout = ""
        self._stderr = ""
        self._open = True
        self._returncode = returncode
        self.close_calls = 0

    def is_open(self):
        return self._open

    def update(self, timeout=0):
        if not self._frames:
            self._open = False
            return
        stdout, stderr = self._frames.pop(0)
        self._stdout += stdout
        self._stderr += stderr
        if not self._frames:
            self._open = False

    def read_stdout(self, timeout=0):
        output = self._stdout
        self._stdout = ""
        return output

    def read_stderr(self, timeout=0):
        output = self._stderr
        self._stderr = ""
        return output

    @property
    def returncode(self):
        return self._returncode if not self._open else None

    def close(self):
        self.close_calls += 1
        self._open = False


def test_kubernetes_executor_uses_noninteractive_stream_contract(core_api):
    websocket = FakeExecWebSocket(
        [("hello\n", ""), ("", "warning\n")],
        returncode=3,
    )
    captured = {}

    def fake_stream(api_method, *args, **kwargs):
        captured["api_method"] = api_method
        captured["args"] = args
        captured["kwargs"] = kwargs
        return websocket

    executor = KubernetesPodExecutor(
        core_api,
        stream_function=fake_stream,
        monotonic=lambda: 0.0,
    )

    result = executor.execute(
        "airflow",
        "airflow-webserver-a1b2",
        "webserver",
        ("python", "--version"),
        timeout=10,
        output_limit_bytes=1024,
    )

    assert result.stdout == "hello\n"
    assert result.stderr == "warning\n"
    assert result.exit_code == 3
    assert result.duration_seconds == 0
    assert captured["api_method"].__self__ is core_api
    assert captured["args"] == (
        "airflow-webserver-a1b2",
        "airflow",
    )
    assert captured["kwargs"] == {
        "command": ["python", "--version"],
        "container": "webserver",
        "stderr": True,
        "stdin": False,
        "stdout": True,
        "tty": False,
        "_preload_content": False,
        "_request_timeout": 10,
    }
    assert websocket.close_calls == 1


def test_kubernetes_executor_closes_websocket_on_timeout(core_api):
    websocket = FakeExecWebSocket([])
    times = iter((0.0, 2.0))
    executor = KubernetesPodExecutor(
        core_api,
        stream_function=lambda *args, **kwargs: websocket,
        monotonic=lambda: next(times),
    )

    with pytest.raises(PodExecTransportTimeoutError):
        executor.execute(
            "airflow",
            "airflow-webserver-a1b2",
            "webserver",
            ("sleep", "100"),
            timeout=1,
            output_limit_bytes=1024,
        )

    assert websocket.close_calls == 1


def test_kubernetes_executor_enforces_combined_output_limit(core_api):
    websocket = FakeExecWebSocket([("123", "45")])
    executor = KubernetesPodExecutor(
        core_api,
        stream_function=lambda *args, **kwargs: websocket,
        monotonic=lambda: 0.0,
    )

    with pytest.raises(PodExecTransportOutputTooLargeError):
        executor.execute(
            "airflow",
            "airflow-webserver-a1b2",
            "webserver",
            ("yes",),
            timeout=1,
            output_limit_bytes=4,
        )

    assert websocket.close_calls == 1


def test_openshift_events_are_json_lines_with_typed_fields():
    stream = StringIO()
    handler = logging.StreamHandler(stream)
    handler.setFormatter(StructuredJsonFormatter())
    event_logger = logging.getLogger("openshift.client.test-json")
    original_handlers = list(event_logger.handlers)
    original_propagate = event_logger.propagate
    original_level = event_logger.level
    event_logger.handlers = [handler]
    event_logger.propagate = False
    event_logger.setLevel(logging.INFO)

    try:
        log_event(
            event_logger,
            logging.INFO,
            "openshift_pod_selected",
            namespace="airflow",
            pod="airflow-webserver-a1b2",
            ready=True,
            grace_period_seconds=None,
        )
    finally:
        event_logger.handlers = original_handlers
        event_logger.propagate = original_propagate
        event_logger.setLevel(original_level)

    payload = json.loads(stream.getvalue())
    assert payload["timestamp"].endswith("+00:00")
    assert payload["level"] == "INFO"
    assert payload["logger"] == "openshift.client.test-json"
    assert payload["event"] == "openshift_pod_selected"
    assert payload["namespace"] == "airflow"
    assert payload["pod"] == "airflow-webserver-a1b2"
    assert payload["ready"] is True
    assert payload["grace_period_seconds"] is None
