"""``SmartContractDeployment`` entity -- Phase 4.

Records an on-chain execution-layer deployment for a ``TokenSeries`` -- bytecode hash, a
human-readable version tag, and a reference to an off-platform audit report. Per this workspace's
confirmed stance (off-chain ledger is authoritative, on-chain is execution-only and *optional*,
not mandatory for MVP -- see ``AUSTIAL_BUILD_PLAN.md``'s risk register: "DLT recognized as market
infrastructure -> Low impact -> off-chain ledger stays authoritative, on-chain is execution-only")
and the plan's own conditional wording ("required *before* launch **if** a DLT execution layer is
used"), this entity is deliberately **not** wired into ``IssuanceService.launch``'s gate at all --
``TokenSeries.smart_contract_deployment`` is a nullable relation, recordable independently via
``IssuanceService.record_smart_contract_deployment`` either before or after a series is launched,
and launch never checks for one. A future phase that actually mandates on-chain execution for a
given asset class can add that conditional check without touching this entity's shape.
"""

from __future__ import annotations

from datetime import datetime

from austial.orm import Column, CreateDateColumn, DateTime, Entity, PrimaryGeneratedColumn


@Entity()
class SmartContractDeployment:
    id: int = PrimaryGeneratedColumn()

    bytecode_hash: str = Column()
    version: str = Column()
    # Off-platform reference (e.g. a URL/document id for a Slither/Mythril or manual audit report)
    # -- Phase 9's "smart contract risk scoring" AI layer is the eventual producer of this, not
    # this phase; nullable since a deployment may be recorded before an audit report exists.
    audit_report_ref: str = Column(nullable=True)
    deployed_at: datetime = Column(type_=DateTime(), nullable=True)

    created_at: datetime = CreateDateColumn()
