import asyncio
import logging

from example_prompts import example_prompts
from reboot.aio.applications import Application
from reboot.aio.auth.oauth_providers import (
    Development,
    OAuthProviderByEnvironment,
)
from servicers.todo import (
    TaskServicer,
    TodoListServicer,
    UserServicer,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)


async def main() -> None:
    application = Application(
        title="Todo Board",
        description=(
            "Create todo lists and reorder their tasks by dragging, "
            "right inside the chat."
        ),
        servicers=[UserServicer, TodoListServicer, TaskServicer],
        example_prompts=example_prompts,
        oauth=OAuthProviderByEnvironment(
            dev=Development(),
            prod=None,
        ),
    )
    await application.run()


if __name__ == "__main__":
    asyncio.run(main())
