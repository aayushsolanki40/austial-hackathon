"""``User`` entity -- Phase 1.2 of the Austial RWA build plan.

Roles are the four platform-wide roles used by ``RolesGuard``/``@Roles(...)``
(see ``src/modules/auth/decorators/roles_decorator.py``). ``COMPLIANCE_OFFICER``
is a regulatory requirement (IFSCA-mandated compliance function), not a mere
convenience role -- don't collapse it into ``ADMIN``.

``is_active`` was added in Phase 1.10 for the admin module's
``PATCH /admin/users/:id/suspend`` -- a suspended (``is_active=False``) user
is rejected at ``AuthService.login()`` (see that module), not just flagged
for display. Defaults ``True`` so every pre-existing/newly-registered user
stays usable until an admin explicitly suspends them.
"""

from __future__ import annotations

from datetime import datetime

from austial.orm import Column, CreateDateColumn, Entity, EnumType, PrimaryGeneratedColumn, UpdateDateColumn

USER_ROLES = ("INVESTOR", "ISSUER", "COMPLIANCE_OFFICER", "ADMIN")


@Entity()
class User:
    id: int = PrimaryGeneratedColumn()
    email: str = Column(unique=True)
    password_hash: str = Column()
    role: str = Column(type_=EnumType(values=USER_ROLES), default="INVESTOR")
    is_active: bool = Column(default=True)
    created_at: datetime = CreateDateColumn()
    updated_at: datetime = UpdateDateColumn()
