from io import BytesIO

import pytest

from src.s3 import (
    S3Client,
    S3ClientClosedError,
    S3Config,
    S3ConfigurationError,
    S3OperationError,
)


class FakeS3Error(Exception):
    def __init__(self, code: str, status: int):
        self.response = {
            "Error": {"Code": code},
            "ResponseMetadata": {
                "HTTPStatusCode": status,
                "RequestId": "request-42",
            },
        }


class FakeS3Service:
    def __init__(self):
        self.calls = []
        self.pages = []
        self.body = BytesIO(b"stored data")
        self.head_error = None
        self.close_calls = 0
        self.close_error = None

    def upload_file(self, **kwargs):
        self.calls.append(("upload_file", kwargs))

    def download_file(self, **kwargs):
        self.calls.append(("download_file", kwargs))

    def put_object(self, **kwargs):
        self.calls.append(("put_object", kwargs))
        return {}

    def get_object(self, **kwargs):
        self.calls.append(("get_object", kwargs))
        return {"Body": self.body}

    def delete_object(self, **kwargs):
        self.calls.append(("delete_object", kwargs))
        return {}

    def head_object(self, **kwargs):
        self.calls.append(("head_object", kwargs))
        if self.head_error:
            raise self.head_error
        return {}

    def list_objects_v2(self, **kwargs):
        self.calls.append(("list_objects_v2", kwargs))
        return self.pages.pop(0)

    def generate_presigned_url(self, **kwargs):
        self.calls.append(("generate_presigned_url", kwargs))
        return "https://example.test/signed"

    def close(self):
        self.close_calls += 1
        if self.close_error is not None:
            raise self.close_error


class FakeS3ServiceFactory:
    def __init__(self, service):
        self.service = service

    def create(self, config):
        return self.service


@pytest.fixture
def service():
    return FakeS3Service()


@pytest.fixture
def client(service):
    return S3Client(S3Config(bucket_name="qa-bucket"), service=service)


def test_config_normalizes_safe_values():
    config = S3Config(
        bucket_name=" artifacts ",
        endpoint_url="http://minio:9000/",
        addressing_style="PATH",
    )

    assert config.bucket_name == "artifacts"
    assert config.endpoint_url == "http://minio:9000"
    assert config.addressing_style == "path"


def test_config_repr_does_not_expose_credentials():
    config = S3Config(
        bucket_name="bucket",
        aws_access_key_id="access-secret",
        aws_secret_access_key="secret-secret",
        aws_session_token="token-secret",
    )

    config_repr = repr(config)

    assert "access-secret" not in config_repr
    assert "secret-secret" not in config_repr
    assert "token-secret" not in config_repr


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"bucket_name": ""}, "bucket_name"),
        (
            {"bucket_name": "bucket", "endpoint_url": "minio:9000"},
            "endpoint_url",
        ),
        (
            {"bucket_name": "bucket", "connect_timeout": float("nan")},
            "connect_timeout",
        ),
        (
            {"bucket_name": "bucket", "read_timeout": 0},
            "read_timeout",
        ),
        (
            {"bucket_name": "bucket", "max_attempts": 0},
            "max_attempts",
        ),
        (
            {"bucket_name": "bucket", "max_attempts": 1.5},
            "max_attempts",
        ),
        (
            {"bucket_name": "bucket", "addressing_style": "invalid"},
            "addressing_style",
        ),
        (
            {"bucket_name": "bucket", "aws_access_key_id": "access"},
            "must be set together",
        ),
        (
            {"bucket_name": "bucket", "aws_session_token": "token"},
            "requires",
        ),
        (
            {
                "bucket_name": "bucket",
                "aws_access_key_id": " ",
                "aws_secret_access_key": "secret",
            },
            "aws_access_key_id",
        ),
    ],
)
def test_config_rejects_invalid_values(kwargs, message):
    with pytest.raises(S3ConfigurationError, match=message):
        S3Config(**kwargs)


def test_context_manager_closes_owned_service(service):
    managed_client = S3Client(
        S3Config(bucket_name="qa-bucket"),
        service_factory=FakeS3ServiceFactory(service),
    )

    with managed_client as entered:
        assert entered is managed_client
        assert managed_client.closed is False

    assert managed_client.closed is True
    assert service.close_calls == 1

    managed_client.close()
    assert service.close_calls == 1

    with pytest.raises(S3ClientClosedError, match="qa-bucket"):
        managed_client.object_exists("object.txt")


def test_context_manager_does_not_close_injected_service(service):
    injected_client = S3Client(
        S3Config(bucket_name="qa-bucket"),
        service=service,
    )

    with injected_client:
        pass

    assert injected_client.closed is True
    assert service.close_calls == 0


def test_context_manager_preserves_test_error_if_close_fails(service):
    service.close_error = RuntimeError("close failed")
    managed_client = S3Client(
        S3Config(bucket_name="qa-bucket"),
        service_factory=FakeS3ServiceFactory(service),
    )

    with pytest.raises(ValueError, match="test failed"):
        with managed_client:
            raise ValueError("test failed")

    assert managed_client.closed is True


def test_upload_bytes_builds_boto3_request(client, service):
    client.upload_bytes(
        data=b"payload",
        object_key="reports/result.json",
        content_type="application/json",
        metadata={"run": "42"},
    )

    assert service.calls == [(
        "put_object",
        {
            "Bucket": "qa-bucket",
            "Key": "reports/result.json",
            "Body": b"payload",
            "ContentType": "application/json",
            "Metadata": {"run": "42"},
        },
    )]


def test_upload_file_validates_source(client, tmp_path):
    with pytest.raises(FileNotFoundError):
        client.upload_file(
            source_path=tmp_path / "missing.txt",
            object_key="missing.txt",
        )


def test_download_bytes_closes_stream(client, service):
    assert client.download_bytes("stored.txt") == b"stored data"
    assert service.body.closed


def test_download_bytes_preserves_read_error_if_body_close_also_fails(
        client,
        service,
):
    class BrokenBody:
        def read(self):
            raise ValueError("read failed")

        def close(self):
            raise RuntimeError("close failed")

    service.body = BrokenBody()

    with pytest.raises(S3OperationError) as error:
        client.download_bytes("stored.txt")

    assert error.value.operation == "get_object"
    assert isinstance(error.value.__cause__, ValueError)


def test_download_file_creates_parent_directory(client, service, tmp_path):
    destination = tmp_path / "nested" / "object.bin"

    result = client.download_file(
        object_key="object.bin",
        destination_path=destination,
    )

    assert result == destination
    assert destination.parent.is_dir()
    assert service.calls[-1] == (
        "download_file",
        {
            "Bucket": "qa-bucket",
            "Key": "object.bin",
            "Filename": str(destination),
        },
    )


def test_object_exists_returns_false_only_for_not_found(client, service):
    service.head_error = FakeS3Error("NoSuchKey", 404)

    assert client.object_exists("missing.txt") is False


def test_object_exists_wraps_other_sdk_errors(client, service):
    service.head_error = FakeS3Error("AccessDenied", 403)

    with pytest.raises(S3OperationError) as error:
        client.object_exists("private.txt")

    assert error.value.operation == "head_object"
    assert error.value.object_key == "private.txt"
    assert error.value.error_code == "AccessDenied"
    assert error.value.http_status == 403
    assert error.value.request_id == "request-42"
    assert "error_code='AccessDenied'" in str(error.value)
    assert isinstance(error.value.__cause__, FakeS3Error)


def test_object_exists_does_not_hide_missing_bucket(client, service):
    service.head_error = FakeS3Error("NoSuchBucket", 404)

    with pytest.raises(S3OperationError) as error:
        client.object_exists("object.txt")

    assert error.value.error_code == "NoSuchBucket"


def test_list_keys_handles_pagination_and_limit(client, service):
    service.pages = [
        {
            "Contents": [{"Key": "logs/1"}, {"Key": "logs/2"}],
            "IsTruncated": True,
            "NextContinuationToken": "next",
        },
        {
            "Contents": [{"Key": "logs/3"}, {"Key": "logs/4"}],
            "IsTruncated": False,
        },
    ]

    assert client.list_keys(prefix="logs/", limit=3) == [
        "logs/1",
        "logs/2",
        "logs/3",
    ]
    assert service.calls[1][1]["ContinuationToken"] == "next"
    assert service.calls[1][1]["MaxKeys"] == 1


def test_list_keys_rejects_repeated_continuation_token(client, service):
    service.pages = [
        {
            "Contents": [{"Key": "logs/1"}],
            "IsTruncated": True,
            "NextContinuationToken": "same",
        },
        {
            "Contents": [{"Key": "logs/2"}],
            "IsTruncated": True,
            "NextContinuationToken": "same",
        },
    ]

    with pytest.raises(S3OperationError) as error:
        client.list_keys(prefix="logs/")

    assert error.value.operation == "list_objects_v2"


@pytest.mark.parametrize("limit", [0, -1, 1.5, True])
def test_list_keys_rejects_invalid_limit(client, limit):
    with pytest.raises(ValueError, match="limit"):
        client.list_keys(limit=limit)


def test_object_operations_reject_empty_key(client):
    with pytest.raises(ValueError, match="must not be empty"):
        client.object_exists("")


def test_generate_presigned_url(client, service):
    url = client.generate_presigned_url(
        "report.txt",
        operation="put_object",
        expires_in=60,
    )

    assert url == "https://example.test/signed"
    assert service.calls[-1] == (
        "generate_presigned_url",
        {
            "ClientMethod": "put_object",
            "Params": {"Bucket": "qa-bucket", "Key": "report.txt"},
            "ExpiresIn": 60,
        },
    )
