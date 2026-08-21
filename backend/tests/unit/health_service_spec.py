"""Unit test for ``HealthService`` -- mirrors a typical Nest ``*.spec.ts``
unit test: build the provider straight from the DI container (via
``austial.testing``) instead of hand-wiring mocks, then assert on its output.
"""

from __future__ import annotations

import pytest
from austial.orm import DataSource, OrmModule
from austial.testing import Test

from src.modules.health.health_module import HealthModule
from src.modules.health.health_service import HealthService


# `DatabaseHealthIndicator` (pulled in by `HealthService`) needs a real `DataSource` to ping --
# an in-memory SQLite one keeps these unit tests hermetic (no Postgres dependency), mirroring the
# "zero-config local dev/tests with SQLite" pattern from the ORM docs. Each test builds its own
# `OrmModule.for_root(...)` instance so the two tests get independent `DataSource`s.
def _sqlite_orm_module():
    return OrmModule.for_root(type_="sqlite", url="sqlite+aiosqlite:///:memory:", entities=[])


@pytest.mark.asyncio
async def test_health_service_reports_ok_status():
    module = await Test.create_testing_module(imports=[_sqlite_orm_module(), HealthModule]).compile()
    await module.get(DataSource).initialize()
    service = module.get(HealthService)

    result = await service.check()

    assert result.status == "ok"
    assert result.error == {}
    assert "memory_heap" in result.info
    assert result.info["memory_heap"]["status"] == "up"
    assert "database" in result.info
    assert result.info["database"]["status"] == "up"
    assert result.details == result.info


@pytest.mark.asyncio
async def test_health_service_is_resolved_as_singleton():
    module = await Test.create_testing_module(imports=[_sqlite_orm_module(), HealthModule]).compile()
    await module.get(DataSource).initialize()
    first = module.get(HealthService)
    second = module.get(HealthService)

    assert first is second
