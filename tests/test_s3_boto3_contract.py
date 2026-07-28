from io import BytesIO

import boto3
import pytest
from botocore.response import StreamingBody
from botocore.stub import Stubber

from src.s3 import S3Client, S3Config
from src.s3.boto3_factory import Boto3S3ServiceFactory


@pytest.fixture
def s3_config_for_contract():
    return S3Config(
        bucket_name="qa-bucket",
        endpoint_url="http://127.0.0.1:9000",
        region_name="us-east-1",
        aws_access_key_id="access",
        aws_secret_access_key="secret",
        addressing_style="path",
        connect_timeout=2.5,
        read_timeout=12.0,
        max_attempts=2,
    )


@pytest.fixture
def boto_service(s3_config_for_contract):
    service = Boto3S3ServiceFactory().create(s3_config_for_contract)
    yield service
    service.close()


@pytest.fixture
def boto_client(s3_config_for_contract, boto_service):
    return S3Client(s3_config_for_contract, service=boto_service)


def test_factory_passes_runtime_settings_to_botocore(
        s3_config_for_contract,
        boto_service,
):
    runtime_config = boto_service.meta.config

    assert runtime_config.connect_timeout == 2.5
    assert runtime_config.read_timeout == 12.0
    assert runtime_config.retries == {
        "mode": "standard",
        "total_max_attempts": 2,
    }
    assert runtime_config.s3 == {"addressing_style": "path"}


def test_upload_and_download_bytes_match_boto3_contract(
        boto_client,
        boto_service,
):
    with Stubber(boto_service) as stubber:
        stubber.add_response(
            "put_object",
            {},
            {
                "Bucket": "qa-bucket",
                "Key": "reports/result.json",
                "Body": b'{"ok": true}',
                "ContentType": "application/json",
                "Metadata": {"run": "42"},
            },
        )
        stubber.add_response(
            "get_object",
            {
                "Body": StreamingBody(
                    BytesIO(b'{"ok": true}'),
                    content_length=12,
                ),
            },
            {
                "Bucket": "qa-bucket",
                "Key": "reports/result.json",
            },
        )

        boto_client.upload_bytes(
            b'{"ok": true}',
            "reports/result.json",
            content_type="application/json",
            metadata={"run": "42"},
        )
        payload = boto_client.download_bytes("reports/result.json")

    assert payload == b'{"ok": true}'


def test_not_found_and_delete_match_boto3_contract(
        boto_client,
        boto_service,
):
    with Stubber(boto_service) as stubber:
        stubber.add_client_error(
            "head_object",
            service_error_code="NoSuchKey",
            service_message="Not found",
            http_status_code=404,
            expected_params={
                "Bucket": "qa-bucket",
                "Key": "missing.txt",
            },
        )
        stubber.add_response(
            "delete_object",
            {},
            {
                "Bucket": "qa-bucket",
                "Key": "old.txt",
            },
        )

        assert boto_client.object_exists("missing.txt") is False
        boto_client.delete_object("old.txt")


def test_list_keys_paginates_real_botocore_responses(
        boto_client,
        boto_service,
):
    with Stubber(boto_service) as stubber:
        stubber.add_response(
            "list_objects_v2",
            {
                "IsTruncated": True,
                "Contents": [{"Key": "runs/1"}],
                "NextContinuationToken": "next",
            },
            {
                "Bucket": "qa-bucket",
                "Prefix": "runs/",
            },
        )
        stubber.add_response(
            "list_objects_v2",
            {
                "IsTruncated": False,
                "Contents": [{"Key": "runs/2"}],
            },
            {
                "Bucket": "qa-bucket",
                "Prefix": "runs/",
                "ContinuationToken": "next",
            },
        )

        keys = boto_client.list_keys(prefix="runs/")

    assert keys == ["runs/1", "runs/2"]
