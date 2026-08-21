"""``LivenessProvider`` -- swappable liveness-check / face-match seam.

See ``ocr_provider.py``'s module docstring for the general "mock now, real
implementation drops in behind this same interface in Phase 9" contract --
identical shape here, just for the liveness-capture + selfie-vs-ID
face-match check instead of document OCR.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class LivenessProvider(ABC):
    """Verifies a live selfie capture is (a) a real person, not a photo/video replay, and
    (b) matches the face on the submitted identity document."""

    @abstractmethod
    def verify(self, *, submission_id: int, selfie_object_key: str, id_document_object_key: str) -> dict[str, Any]:
        """Return a JSON-serializable liveness/face-match result."""
        raise NotImplementedError


class MockLivenessProvider(LivenessProvider):
    """PLACEHOLDER ONLY -- performs no real liveness detection or face-matching biometrics.

    Deterministic always-pass behavior (``live: True``, ``face_match: True``) so the KYC
    pipeline has something real to advance the state machine on during Phase 2-8 -- clearly
    labeled ``is_mock: True`` so it can never be mistaken for a real biometric check. See
    ``ocr_provider.py``'s module docstring for the Phase 9 swap-in plan.
    """

    PROVIDER_NAME = "mock-liveness-v0"

    def verify(self, *, submission_id: int, selfie_object_key: str, id_document_object_key: str) -> dict[str, Any]:
        return {
            "provider": self.PROVIDER_NAME,
            "is_mock": True,
            "submission_id": submission_id,
            "live": True,
            "face_match": True,
            "match_score": None,
            "note": "MOCK PROVIDER: no liveness/face-match biometrics were actually performed. Placeholder"
            " for Phase 9.",
        }
