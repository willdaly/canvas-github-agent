"""Compatibility wrapper for the organized example script."""
import asyncio

from examples.example import example_workflow, quick_create_example

__all__ = ["example_workflow", "quick_create_example"]


if __name__ == "__main__":
    asyncio.run(example_workflow())
