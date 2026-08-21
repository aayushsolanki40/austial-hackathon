"""Shared, non-user-facing JWT constants -- kept out of ``auth_service.py``/
``jwt_auth_guard.py`` so both agree on the exact same algorithm/claim
values. These are technical protocol identifiers, not user-facing/business
strings, so they're plain module constants rather than i18n keys (the i18n
hard rule covers messages/labels shown to a human, not wire-protocol tokens).
"""

from __future__ import annotations

JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_TYPE = "access"
REFRESH_TOKEN_TYPE = "refresh"

DEFAULT_ACCESS_TOKEN_TTL_MINUTES = 15
DEFAULT_REFRESH_TOKEN_TTL_DAYS = 30
