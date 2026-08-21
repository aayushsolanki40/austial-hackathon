"""``RefreshToken`` entity -- Phase 1.2. Not append-only (unlike ``AuditLog``/
``LedgerEntry``): rotated/revoked tokens are updated in place via
``Repository.save()`` on the loaded row (a full-column UPDATE, since its
primary key is already set), never deleted.
"""

from __future__ import annotations

from datetime import datetime

from austial.orm import Column, CreateDateColumn, Entity, ManyToOne, PrimaryGeneratedColumn

from src.modules.auth.entities.user import User


@Entity()
class RefreshToken:
    id: int = PrimaryGeneratedColumn()
    # ★ kwarg is `inverse_side=`, not `inverse=` -- see AUSTIAL_BUILD_PLAN.md's framework-notes.
    user: User = ManyToOne(lambda: User, inverse_side="refresh_tokens")
    token_hash: str = Column(unique=True)
    expires_at: datetime = Column()
    revoked: bool = Column(default=False)
    created_at: datetime = CreateDateColumn()
