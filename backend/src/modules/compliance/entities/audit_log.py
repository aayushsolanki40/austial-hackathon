"""``AuditLog`` entity -- Phase 1.6. APPEND-ONLY, 7-year IFSCA retention.

No ``UPDATE``/``DELETE`` code path may ever be added for this entity --
every write site in this codebase (today, only ``AuditInterceptor``) must
call ``Repository.save()`` to insert a fresh row, never
``Repository.update()``/``Repository.delete()``.

Enforced at the framework level via ``@Entity(append_only=True)`` --
``EntityManager`` raises ``AppendOnlyViolationError`` on any UPDATE-shaped
``save()``, ``Repository.update()``, ``Repository.remove()``, or
``Repository.delete()`` against this entity. INSERT (a fresh row via
``save()`` with no PK set) is unaffected -- that's the only legitimate write
path here. See ``austial-py-doc/content/techniques/database.mdx``'s
"Append-only entities" section for the full contract (this is an
application-level `EntityManager` guard, not a DB-level trigger/permission --
raw SQL run outside the ORM is not covered).
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from austial.orm import Column, CreateDateColumn, Entity, JSONType, PrimaryGeneratedColumn


@Entity(append_only=True)
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
