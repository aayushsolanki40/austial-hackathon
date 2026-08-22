"""Unit tests for ``ObjectStorageService`` -- Phase 1.8. Uses ``moto``'s
``mock_aws`` to fake S3 rather than hitting real AWS, mirroring the rest of
this suite's "hermetic, no live external dependency" convention.
"""

from __future__ import annotations

import boto3
import pytest
from austial.config import ConfigService
from moto import mock_aws

from src.storage.object_storage_service import ObjectStorageService

_BUCKET = "austial-documents-test"
_REGION = "us-east-1"


def _config_service() -> ConfigService:
    return ConfigService({"DOCUMENTS_S3_BUCKET": _BUCKET, "AWS_REGION": _REGION})


@pytest.fixture
def moto_s3():
    with mock_aws():
        client = boto3.client("s3", region_name=_REGION)
        client.create_bucket(Bucket=_BUCKET)
        yield client


def test_constructor_reads_bucket_and_region_from_config(moto_s3):
    service = ObjectStorageService(_config_service())

    assert service._bucket == _BUCKET  # noqa: SLF001 - internal attribute, checked directly for this test


def test_constructor_raises_if_bucket_env_var_missing(moto_s3):
    with pytest.raises(Exception):  # noqa: B017 - `ConfigService.get_or_throw` raises its own exception type
        ObjectStorageService(ConfigService({"AWS_REGION": _REGION}))


def test_generate_upload_url_returns_presigned_put_url_for_configured_bucket(moto_s3):
    service = ObjectStorageService(_config_service())

    url = service.generate_upload_url("kyc/user-1/passport.pdf", content_type="application/pdf")

    assert url.startswith("https://")
    assert _BUCKET in url
    assert "kyc/user-1/passport.pdf" in url


def test_generate_download_url_returns_presigned_get_url_for_configured_bucket(moto_s3):
    service = ObjectStorageService(_config_service())

    url = service.generate_download_url("kyc/user-1/passport.pdf")

    assert url.startswith("https://")
    assert _BUCKET in url
    assert "kyc/user-1/passport.pdf" in url


def test_generate_upload_url_respects_custom_expiry(moto_s3):
    service = ObjectStorageService(_config_service())

    short_lived = service.generate_upload_url("x.pdf", content_type="application/pdf", expires_in=60)
    long_lived = service.generate_upload_url("x.pdf", content_type="application/pdf", expires_in=3600)

    # Exact query-param shape (`Expires=<unix ts>` vs SigV4's `X-Amz-Expires=<seconds>`) depends on
    # the signature version boto3/moto negotiate, so assert on the *effect* (different `expires_in`
    # -> different signed URL) rather than a specific param name.
    assert short_lived != long_lived
