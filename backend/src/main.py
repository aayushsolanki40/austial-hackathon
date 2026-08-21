"""Application entry point -- mirrors Nest's ``src/main.ts``.

Works two ways, just like a FastAPI app:

* ``python src/main.py``            -> runs ``bootstrap()``, Nest-style ``app.listen()``
* ``uvicorn src.main:app --reload``  -> `app` is already a real ASGI callable
* ``austial serve``                  -> also just imports ``src.main:app`` and hands it
  straight to ``uvicorn.run(...)``, i.e. ``bootstrap()`` below is *never* called in that path.

Note: building the app graph (module scanning + DI wiring) is synchronous --
only ``app.listen()`` (actually starting the ASGI server) is async, mirroring
where real async work happens in Nest too.

``DataSource.initialize()`` (see ``austial.orm``'s docs -- "the one manual step") therefore
can't live in ``bootstrap()`` alone, since the CLI's ``austial serve`` never runs it. It's
registered as a ``"startup"`` event handler on the underlying ASGI app instead (via
``get_http_adapter()``), which fires under every entry point above because they all ultimately
go through uvicorn's ASGI lifespan protocol. ``AustialApplication`` has no lifecycle-hook API of
its own yet, and the pinned Starlette dropped ``add_event_handler`` (removed upstream), so the
deprecated-but-functional ``FastAPI.on_event()`` is the only hook actually available here.
"""

import asyncio

from austial import AustialApplication, AustialFactory, ValidationPipe
from austial.common.filters import AllExceptionsFilter
from austial.orm import DataSource

from src.app_module import AppModule
from src.i18n.i18n import t


def _build() -> AustialApplication:
    app = AustialFactory.create(
        AppModule,
        title=t("app.title"),
        version=t("app.version"),
        description=t("app.description"),
    )
    app.use_global_pipes(ValidationPipe())
    app.use_global_filters(AllExceptionsFilter())
    app.enable_cors()

    @app.get_http_adapter().on_event("startup")
    async def _init_data_source() -> None:
        await app.get(DataSource).initialize()

    return app


app = _build()


async def bootstrap() -> None:
    await app.listen(8000)


if __name__ == "__main__":
    asyncio.run(bootstrap())
