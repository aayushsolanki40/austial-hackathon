"""``SanctionsScreeningProvider`` -- swappable FATF/OFAC-style sanctions/watchlist screening
seam, used both by the one-time auto-screening pipeline (``KycService.submit()``) and the
periodic re-screening task shape (``src/jobs/kyc_tasks.py``'s
``periodic_resanction_screening_task``).

See ``ocr_provider.py``'s module docstring for the general "mock now, real implementation
drops in behind this same interface in Phase 9" contract.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class SanctionsScreeningProvider(ABC):
    """Screens a declared identity against sanctions/watchlists (FATF, OFAC SDN, etc.)."""

    @abstractmethod
    def screen(self, *, legal_name: str, nationality: str) -> dict[str, Any]:
        """Return a JSON-serializable screening result -- ``hit: bool`` plus whatever
        supporting detail the concrete provider can offer."""
        raise NotImplementedError


class MockSanctionsScreeningProvider(SanctionsScreeningProvider):
    """PLACEHOLDER ONLY -- calls no real FATF/OFAC/sanctions-list API.

    Deterministic behavior, not a hardcoded always-pass: matches ``legal_name`` (case/
    whitespace-insensitive) against a tiny, fixed, in-memory test watchlist so callers and
    tests can exercise both the "clear" and "hit" branches of the KYC pipeline without any
    real sanctions data or network access. Every real name not on this toy list clears --
    this is **not** real sanctions coverage of any kind. See ``ocr_provider.py``'s module
    docstring for the Phase 9 swap-in plan (a real FATF/OFAC list integration).
    """

    PROVIDER_NAME = "mock-sanctions-v0"

    # Deliberately obvious/synthetic names -- exists purely so this mock has *some*
    # deterministic "hit" path to exercise, not a real denylist.
    _MOCK_WATCHLIST = frozenset({"SANCTIONED TEST ENTITY", "MOCK WATCHLIST MATCH"})

    def screen(self, *, legal_name: str, nationality: str) -> dict[str, Any]:
        normalized = " ".join(legal_name.split()).upper()
        hit = normalized in self._MOCK_WATCHLIST
        return {
            "provider": self.PROVIDER_NAME,
            "is_mock": True,
            "hit": hit,
            "matched_lists": ["MOCK_TEST_WATCHLIST"] if hit else [],
            "note": "MOCK PROVIDER: not a real FATF/OFAC/sanctions-list check. Placeholder for Phase 9.",
        }
