"""``KycDocument`` entity -- Phase 2.

One row per uploaded evidentiary document (passport, national ID, proof of
address, liveness selfie, ...) attached to a ``KycSubmission``. The file
bytes themselves are never stored here -- only the S3 object key
(``object_key``) a presigned URL was issued for (see
``src/storage/object_storage_service.py``); the API process never proxies
document bytes.

``ocr_result`` is the mock OCR-extraction output for this specific document
(see ``src/modules/kyc/providers/ocr_provider.py``) -- kept per-document
(unlike ``KycSubmission.screening_result``, which aggregates the
submission-level liveness/sanctions checks) since OCR is inherently a
per-document operation.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from austial.orm import Column, CreateDateColumn, Entity, EnumType, JSONType, ManyToOne, PrimaryGeneratedColumn

from src.modules.kyc.entities.kyc_submission import KycSubmission

KYC_DOCUMENT_TYPES = (
    "PASSPORT",
    "NATIONAL_ID",
    "DRIVERS_LICENSE",
    "PROOF_OF_ADDRESS",
    "SELFIE",
)


@Entity()
class KycDocument:
    id: int = PrimaryGeneratedColumn()
    submission: KycSubmission = ManyToOne(lambda: KycSubmission, inverse_side="documents", nullable=False)

    document_type: str = Column(type_=EnumType(values=KYC_DOCUMENT_TYPES))
    object_key: str = Column()

    ocr_result: dict[str, Any] = Column(type_=JSONType(), nullable=True)

    created_at: datetime = CreateDateColumn()
