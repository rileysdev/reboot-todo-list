import asyncio
import logging

from reboot.aio.applications import Application
from servicers.todo import (
    AccountServicer,
    TaskServicer,
    TodoListServicer,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)


async def main() -> None:
    # No `oauth=` / `token_verifier=` yet: browser identity is a
    # development stand-in (a local profile), and authorizers are
    # deferred. Wire a real `token_verifier=` before serving real users.
    application = Application(
        servicers=[AccountServicer, TodoListServicer, TaskServicer],
    )
    await application.run()


if __name__ == "__main__":
    asyncio.run(main())
