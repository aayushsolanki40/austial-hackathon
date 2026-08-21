"""``Asset`` entity -- Phase 3.

``asset_class`` is the competitive differentiator called out in
``AUSTIAL_BUILD_PLAN.md`` Phase 3 -- full RWA-paper breadth (securities,
real estate, commodities, infrastructure, IP) vs. Zoniqx's securities-only
scope -- modelled as a real, queryable ``EnumType`` column, not free text.

``custodian`` starts ``NULL`` (an asset is submitted by its ``Issuer`` before
any custodian is involved) and is only ever set via
``AssetsService.attach_custodian``, which enforces the ★ regulatory rule --
*an asset cannot be tokenized unless its custodian row is IFSCA-verified* --
in the service layer. ``custodian_verified`` is a denormalized snapshot of
``custodian.ifsca_verified`` at the moment it was attached, kept in lockstep
by ``AssetsService`` (never touched anywhere else) purely so the DB-level
half of that same rule can be expressed as a composite foreign key --
``FOREIGN KEY (custodian_id, custodian_verified) REFERENCES
custodian (id, ifsca_verified)`` -- since a plain single-column
``ManyToOne`` FK only proves *a* custodian row exists, not that it's
verified. See ``Custodian``'s docstring for the full "why a migration-level
constraint, not `@Entity()` metadata" explanation, and the Alembic migration
itself for the exact DDL.

``tokenization_ready`` is intentionally *not* a stored column -- it's just
"is ``custodian`` set", computed at the DTO layer (see ``assets_service.py``)
so it can never drift from the ``custodian``/``custodian_verified`` pair that
is the actual source of truth.

See ``alembic/versions/43b2ddb8875c_phase3_issuers_custodians_assets.py`` for the composite
FK/CHECK DDL, and ``alembic/README.md``'s "Gotcha: hand-authored composite constraints will look
like drift to autogenerate" section before ever running ``alembic revision --autogenerate``
again against this table.
"""

from __future__ import annotations

from datetime import datetime

from austial.orm import Column, CreateDateColumn, Entity, EnumType, ManyToOne, PrimaryGeneratedColumn, UpdateDateColumn

from src.modules.custodians.entities.custodian import Custodian
from src.modules.issuers.entities.issuer import Issuer

ASSET_CLASSES = ("SECURITY", "REAL_ESTATE", "COMMODITY", "INFRASTRUCTURE", "IP")


@Entity()
class Asset:
    id: int = PrimaryGeneratedColumn()
    issuer: Issuer = ManyToOne(lambda: Issuer, inverse_side="assets", nullable=False)
    custodian: Custodian = ManyToOne(lambda: Custodian, inverse_side="assets", nullable=True, on_delete="RESTRICT")

    name: str = Column()
    asset_class: str = Column(type_=EnumType(values=ASSET_CLASSES))
    description: str = Column(nullable=True)

    # Denormalized snapshot of `custodian.ifsca_verified` at attach time -- see module docstring.
    # Always `False` while `custodian` is `NULL`.
    custodian_verified: bool = Column(default=False)

    created_at: datetime = CreateDateColumn()
    updated_at: datetime = UpdateDateColumn()
