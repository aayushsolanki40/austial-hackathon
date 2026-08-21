"""``AuditLog`` entity -- Phase 1.6. APPEND-ONLY, 7-year IFSCA retention.

No ``UPDATE``/``DELETE`` code path may ever be added for this entity --
every write site in this codebase (today, only ``AuditInterceptor``) must
call ``Repository.save()`` to insert a fresh row, never
``Repository.update()``/``Repository.delete()``.

Enforcement is convention-only today: ``austial.orm`` has no
``@Entity(append_only=True)`` (or equivalent) that would reject an
``UPDATE``/``DELETE`` at the framework level. That gap is tracked in
``AUSTIAL_BUILD_PLAN.md`` (framework-gap item 3) as follow-up work for
``austial-framework-dev`` before Phase 5's ``LedgerEntry`` ships -- not
something to work around here.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from austial.orm import Column, CreateDateColumn, Entity, JSONType, PrimaryGeneratedColumn


@Entity()
class AuditLog:
    id: int = PrimaryGeneratedColumn()
    actor_user_id: int = Column(nullable=True)
    action: str = Column()
    entity_type: str = Column()
    entity_id: str = Column(nullable=True)
    before_state: dict[str, Any] = Column(type_=JSONType(), nullable=True)
    after_state: dict[str, Any] = Column(type_=JSONType(), nullable=True)
    ip_address: str = Column(nullable=True)
    occurred_at: datetime = CreateDateColumn()
