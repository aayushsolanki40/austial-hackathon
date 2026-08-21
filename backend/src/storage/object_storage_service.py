"""``ObjectStorageService`` -- Phase 1.8. KYC documents and disclosure PDFs are stored in S3, not
a DB blob column, and the API process never proxies file bytes: callers get a short-lived
presigned URL and upload/download directly against S3.

NOTE (data residency, tracked risk -- see ``AUSTIAL_BUILD_PLAN.md``'s risk register): real IFSCA
rules require GIFT IFSC-resident storage for these documents. The S3 bucket this service talks to
lives in AWS `us-east-1` (see ``austial-hackathon/infra/terraform/README.md``'s cost-capped demo
deployment) purely as a demo-environment stand-in -- it is **not** a compliant storage location
for production KYC/disclosure data, and this class makes no attempt to pretend otherwise. Solving
GIFT IFSC-resident hosting is out of scope here; don't read this as "production-ready."

Bucket is a **new, separate, private** bucket -- distinct from the existing public
frontend-static-website bucket (``infra/terraform/main.tf``'s ``aws_s3_bucket.frontend``). This
service assumes that bucket already exists (config-only, provisions nothing) -- creating it is
infra follow-up work (Terraform), not something this class does.
"""

from __future__ import annotations

import boto3
from austial import Injectable
from austial.config import ConfigService

_DEFAULT_PRESIGNED_URL_TTL_SECONDS = 900  # 15 minutes


@Injectable()
class ObjectStorageService:
    def __init__(self, config: ConfigService):
        self._bucket = config.get_or_throw("DOCUMENTS_S3_BUCKET")
        self._client = boto3.client("s3", region_name=config.get_or_throw("AWS_REGION"))

    def generate_upload_url(
        self, object_key: str, *, content_type: str, expires_in: int = _DEFAULT_PRESIGNED_URL_TTL_SECONDS
    ) -> str:
        """A presigned ``PUT`` URL -- the caller uploads the file bytes directly to S3 with this
        URL (e.g. ``httpx.put(url, content=file_bytes, headers={"Content-Type": content_type})``),
        never through this API process."""
        return self._client.generate_presigned_url(
            "put_object",
            Params={"Bucket": self._bucket, "Key": object_key, "ContentType": content_type},
            ExpiresIn=expires_in,
        )

    def generate_download_url(self, object_key: str, *, expires_in: int = _DEFAULT_PRESIGNED_URL_TTL_SECONDS) -> str:
        """A presigned ``GET`` URL -- same "never proxy bytes through the API" rule as uploads."""
        return self._client.generate_presigned_url(
            "get_object",
            Params={"Bucket": self._bucket, "Key": object_key},
            ExpiresIn=expires_in,
        )
