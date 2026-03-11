"""Compatibility wrapper for the organized app entrypoint."""
import asyncio

from app.agent import CanvasGitHubAgent, list_course_assignments, list_courses, main

__all__ = [
    "CanvasGitHubAgent",
    "list_courses",
    "list_course_assignments",
    "main",
]


if __name__ == "__main__":
    asyncio.run(main())
