"""Ready-to-send chat scenarios the root-page wizard offers users.

Each walks an end-to-end flow and ends on a turn that renders one of
the two embedded UIs (the board or the overview).
"""

from reboot.application import ExamplePrompt

example_prompts = [
    ExamplePrompt(
        title="Plan a product launch",
        prompts=[
            "Create a todo list called 'Product Launch'.",
            "Add these tasks: 'Finalize pricing' (high priority), "
            "'Write the launch blog post' (medium), 'Line up press' "
            "(medium), and 'Celebrate' (low).",
            "Open the board so I can drag things into the order I want "
            "to tackle them.",
        ],
    ),
    ExamplePrompt(
        title="Set up my week",
        prompts=[
            "Create a list called 'This Week' with tasks 'Gym', "
            "'Grocery run', 'Call the dentist', and 'Finish the report' "
            "as high priority.",
            "I already went to the gym and did the grocery run — mark "
            "those done.",
            "Show me all my lists so I can see how the week is shaping up.",
        ],
    ),
    ExamplePrompt(
        title="Grocery run",
        prompts=[
            "Start a 'Groceries' list and add coffee, oat milk, "
            "sourdough, eggs, and dark chocolate.",
            "Open the groceries board so I can reorder it to match the "
            "store layout.",
        ],
    ),
]
