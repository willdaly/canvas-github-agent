"""
Agent Reasoning Layer

This module interprets user queries, selects the appropriate Canvas tool,
and returns a readable response.
"""

from canvas_tools import CanvasTools

# initialize canvas tools
canvas_tools = CanvasTools()


def detect_intent(query: str):
    """
    Detect user intent from a natural language query.
    """

    query = query.lower()

    if "course" in query:
        return "list_courses"

    if "assignment" in query:
        return "list_assignments"

    if "detail" in query:
        return "assignment_details"

    return "unknown"


def select_tool(intent: str):
    """
    Select which Canvas tool should be called.
    """

    if intent == "list_courses":
        return "list_courses"

    if intent == "list_assignments":
        return "get_course_assignments"

    if intent == "assignment_details":
        return "get_assignment_details"

    return None


async def execute_tool(tool, course_id=None, assignment_id=None):
    """
    Execute the selected Canvas tool.
    """

    if tool == "list_courses":
        return await canvas_tools.list_courses()

    if tool == "get_course_assignments":
        return await canvas_tools.get_course_assignments(course_id)

    if tool == "get_assignment_details":
        return await canvas_tools.get_assignment_details(course_id, assignment_id)

    return None


def generate_response(data):
    """
    Convert tool output into readable text.
    """

    if not data:
        return "No data found."

    if isinstance(data, list):

        response = "Here are the results:\n"

        for item in data:
            response += f"- {item.get('name')} (ID: {item.get('id')})\n"

        return response

    if isinstance(data, dict):
        return f"{data.get('name')} (ID: {data.get('id')})"

    return str(data)


async def handle_user_query(query, course_id=None, assignment_id=None):
    """
    Main reasoning pipeline.
    """

    intent = detect_intent(query)

    tool = select_tool(intent)

    data = await execute_tool(tool, course_id, assignment_id)

    response = generate_response(data)

    return response
