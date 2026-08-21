"""``OcrProvider`` -- swappable OCR-extraction seam for KYC documents.

★ Phase 2 ships exactly one implementation of this interface --
``MockOcrProvider`` below -- a deterministic **placeholder that performs no
real OCR**. Per ``AUSTIAL_BUILD_PLAN.md`` Phase 9 ("AI/ML Layer"), a real
OCR/document-intelligence integration is future work that feeds into this
same Phase 2 KYC pipeline. That real implementation is expected to satisfy
this exact interface and be swapped in at the single call site in
``src/jobs/kyc_tasks.py`` -- ``KycService``'s state-machine/orchestration
code in ``kyc_service.py`` never needs to change.

Do not mistake ``MockOcrProvider`` for production document intelligence --
it is named, documented, and logged as a mock everywhere it's used.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class OcrProvider(ABC):
    """Extracts structured fields from a KYC document image/PDF."""

    @abstractmethod
    def extract(self, *, document_type: str, object_key: str) -> dict[str, Any]:
        """Return a JSON-serializable extraction result for the document stored at
        ``object_key`` (an S3 key -- see ``ObjectStorageService``, never raw bytes)."""
        raise NotImplementedError


class MockOcrProvider(OcrProvider):
    """PLACEHOLDER ONLY -- performs no real OCR, no network call, no ML inference.

    Always returns a fixed, clearly-labeled mock payload (``is_mock: True``) so no caller
    can mistake this for a real extraction result. See ``OcrProvider``'s module docstring
    for the Phase 9 swap-in plan.
    """

    PROVIDER_NAME = "mock-ocr-v0"

    def extract(self, *, document_type: str, object_key: str) -> dict[str, Any]:
        return {
            "provider": self.PROVIDER_NAME,
            "is_mock": True,
            "document_type": document_type,
            "object_key": object_key,
            "extracted_fields": {},
            "confidence": None,
            "note": "MOCK PROVIDER: no OCR was actually performed. Placeholder for Phase 9.",
        }
