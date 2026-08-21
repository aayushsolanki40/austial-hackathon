"""``StorageModule`` -- Phase 1.8. Registers ``ObjectStorageService`` for DI. No entities, no
controller of its own yet -- nothing in Phase 1's domain scope (KYC submissions, disclosure
documents) exists as a module to consume it; this is the infrastructure seam Phase 2+ (``kyc``,
``issuance``) will inject ``ObjectStorageService`` into.
"""

from austial import Module

from src.storage.object_storage_service import ObjectStorageService


@Module(
    providers=[ObjectStorageService],
    exports=[ObjectStorageService],
)
class StorageModule:
    pass
