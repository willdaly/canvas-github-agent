"""Compatibility wrapper for the organized reasoning module."""
from app.agent_reasoning import (
    canvas_tools,
    detect_intent,
    execute_tool,
    generate_response,
    handle_user_query,
    select_tool,
)

__all__ = [
    "canvas_tools",
    "detect_intent",
    "select_tool",
    "execute_tool",
    "generate_response",
    "handle_user_query",
]
