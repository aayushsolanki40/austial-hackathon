"""``TokenSeries`` entity -- Phase 4.

Created atomically with the ``IFSCA_APPROVED -> LAUNCHED`` transition -- see ``IssuanceService.
launch``'s docstring for why that atomicity goes through ``DataSource.transaction(...)`` rather
than two independent ``.save()``/``.update()`` calls.

``paused`` is the backend half of the plan's frontend "circuit-breaker control (Compliance
Officer pauses a contract without redeploy)" note -- flipped by ``IssuanceService.
pause_token_series``/``resume_token_series``, both ``COMPLIANCE_OFFICER``-gated. This phase is
backend-only per the workspace's backend/frontend split; the endpoints exist for
``angular-frontend-dev`` to wire the actual pause/resume control against later.

``smart_contract_deployment`` is nullable -- see ``SmartContractDeployment``'s docstring for why
launch never requires one to exist first.
"""

from __future__ import annotations

from datetime import datetime

from austial.orm import Column, CreateDateColumn, Entity, ManyToOne, Numeric, PrimaryGeneratedColumn, UpdateDateColumn

from src.modules.issuance.entities.smart_contract_deployment import SmartContractDeployment
from src.modules.issuance.entities.tokenization_proposal import TokenizationProposal


@Entity()
class TokenSeries:
    id: int = PrimaryGeneratedColumn()
    proposal: TokenizationProposal = ManyToOne(
        lambda: TokenizationProposal, inverse_side="token_series", nullable=False
    )
    smart_contract_deployment: SmartContractDeployment = ManyToOne(
        lambda: SmartContractDeployment, inverse_side="token_series", nullable=True, on_delete="SET NULL"
    )

    symbol: str = Column(unique=True)
    # Snapshot of `proposal.total_units` at launch time -- see `IssuanceService.launch`'s
    # docstring on why this is copied rather than read live through `proposal` at request time.
    total_supply: float = Column(type_=Numeric(precision=28, scale=8))
    contract_address: str = Column(nullable=True)
    paused: bool = Column(default=False)
    launched_by_user_id: int = Column(nullable=True)

    created_at: datetime = CreateDateColumn()
    updated_at: datetime = UpdateDateColumn()
