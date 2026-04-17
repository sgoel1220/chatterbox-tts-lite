"""Hatchet worker registration and startup.

Run as a separate process (recommended for production):
    python -m app.workflows.worker

This keeps the worker independently scalable from the API server.
"""

from collections.abc import AsyncGenerator

from app.db import close_db, init_db
from app.logging import configure_logging
from app.workflows import WORKFLOWS, hatchet


async def _worker_lifespan() -> AsyncGenerator[None, None]:
    """Initialize and tear down the database within Hatchet's event loop.

    Hatchet creates its own asyncio event loop in worker.start() and calls
    ``anext(lifespan())`` directly — it expects a plain async generator, not
    an ``@asynccontextmanager``-wrapped object.

    SQLAlchemy's AsyncEngine must be created on the same loop it will be used
    from, so DB init must happen here rather than before ``worker.start()``.
    """
    await init_db()
    try:
        yield
    finally:
        await close_db()


def start_worker() -> None:
    """Register all workflows and start the Hatchet worker.

    Raises:
        RuntimeError: If no workflows are registered in WORKFLOWS.
    """
    if not WORKFLOWS:
        raise RuntimeError(
            "No workflows registered. Add workflow instances to app.workflows.WORKFLOWS "
            "before starting the worker."
        )

    configure_logging(json_logs=False)

    worker = hatchet.worker(
        "creepy-brain-worker",
        workflows=WORKFLOWS,
        lifespan=_worker_lifespan,
    )
    worker.start()


if __name__ == "__main__":
    start_worker()
