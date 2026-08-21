"""``Custodian`` entity -- Phase 3.

The IFSCA custodian registry. ★ Regulatory rule (``AUSTIAL_BUILD_PLAN.md`` Phase 3): an
``Asset`` cannot be tokenized unless its custodian row is IFSCA-verified
(``ifsca_verified is True``). Enforced in two independent places:

1. **Service layer** -- ``AssetsService.attach_custodian`` refuses to link an ``Asset`` to a
   ``Custodian`` whose ``ifsca_verified`` is ``False`` (see that method's docstring).
2. **DB-level FK constraint** -- ``austial.orm``'s ``@Entity()``/``ManyToOne`` decorators have no
   way to express a *composite* foreign key or a table-level ``CHECK`` constraint (confirmed by
   reading ``austial-orm``'s ``decorators/entity.py``/``decorators/relations.py`` -- neither
   accepts anything beyond a single-column FK derived from the relation itself; flagged for
   ``austial-framework-dev`` as a follow-up enhancement, not blocking here). The composite
   constraint is therefore hand-authored directly in the Alembic migration that creates
   ``asset`` (see ``alembic/versions/..._phase3_issuers_custodians_assets.py``), the same
   "autogenerate gets you 90% there, the rest is a deliberate manual addition" pattern this
   codebase already uses for Postgres ``ENUM`` type creation/teardown (see
   ``60429c1b1184_initial_schema.py``'s ``downgrade()``). Concretely: a
   ``UNIQUE (id, ifsca_verified)`` constraint on this table, plus a composite
   ``FOREIGN KEY (custodian_id, custodian_verified) REFERENCES custodian (id, ifsca_verified)``
   on ``asset`` -- which only admits a row pairing a given ``custodian_id`` with
   ``ifsca_verified = true`` literally matching that custodian's live value at write time,
   catching a would-be race (custodian un-verified between the service-layer check and the
   write) that the service-layer check alone cannot.

This composite-FK trick lives only in the migration, not in ``@Entity()`` metadata (the ORM has
no way to express it there yet), so it applies to the real Postgres schema but is **not**
exercised by this app's SQLite-backed (``synchronize=True``) unit/e2e tests -- those instead
prove out the service-layer half of the rule (see ``tests/unit/assets_service_spec.py``).
"""

from __future__ import annotations

from datetime import datetime

from austial.orm import Column, CreateDateColumn, Entity, PrimaryGeneratedColumn, UpdateDateColumn


@Entity()
class Custodian:
    id: int = PrimaryGeneratedColumn()

    name: str = Column()
    ifsca_registration_no: str = Column(unique=True)

    # Type inferred as `Boolean` from the `bool` annotation, mirroring `User.is_active` -- see
    # `Column()`'s own docstring on inference-by-default.
    ifsca_verified: bool = Column(default=False)
    verified_by_user_id: int = Column(nullable=True)
    verified_at: datetime = Column(nullable=True)

    created_at: datetime = CreateDateColumn()
    updated_at: datetime = UpdateDateColumn()
