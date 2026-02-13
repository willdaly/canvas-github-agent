"""
Canvas MCP Tools for interacting with Canvas LMS through MCP server.
"""
import os
import json
from typing import Dict, List, Optional, Any
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from contextlib import asynccontextmanager


class CanvasTools:
    """Tools for interacting with Canvas LMS via MCP."""
    
    def __init__(self):
        self.canvas_url = os.getenv("CANVAS_API_URL", "https://canvas.instructure.com")
        self.canvas_token = os.getenv("CANVAS_API_TOKEN")
        self.mcp_server_url = os.getenv("CANVAS_MCP_SERVER_URL", "npx")
        self.mcp_server_args = os.getenv("CANVAS_MCP_SERVER_ARGS", "-y,@illinihunt/canvas-mcp").split(",")
        
    @asynccontextmanager
    async def get_canvas_session(self):
        """Create a Canvas MCP session."""
        server_params = StdioServerParameters(
            command=self.mcp_server_url,
            args=self.mcp_server_args,
            env={
                "CANVAS_API_URL": self.canvas_url,
                "CANVAS_API_TOKEN": self.canvas_token,
            }
        )
        
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                yield session
    
    async def list_courses(self) -> List[Dict[str, Any]]:
        """
        List all courses available to the user.
        
        Returns:
            List of course dictionaries with id, name, and other details
        """
        async with self.get_canvas_session() as session:
            result = await session.call_tool("canvas_list_courses", arguments={})
            if hasattr(result, 'content') and len(result.content) > 0:
                content = result.content[0]
                if hasattr(content, 'text'):
                    return json.loads(content.text)
            return []
    
    async def get_course_assignments(self, course_id: int) -> List[Dict[str, Any]]:
        """
        Get all assignments for a specific course.
        
        Args:
            course_id: The Canvas course ID
            
        Returns:
            List of assignment dictionaries
        """
        async with self.get_canvas_session() as session:
            result = await session.call_tool(
                "canvas_get_assignments",
                arguments={"course_id": course_id}
            )
            if hasattr(result, 'content') and len(result.content) > 0:
                content = result.content[0]
                if hasattr(content, 'text'):
                    return json.loads(content.text)
            return []
    
    async def get_assignment_details(self, course_id: int, assignment_id: int) -> Optional[Dict[str, Any]]:
        """
        Get detailed information about a specific assignment.
        
        Args:
            course_id: The Canvas course ID
            assignment_id: The assignment ID
            
        Returns:
            Assignment details dictionary
        """
        async with self.get_canvas_session() as session:
            result = await session.call_tool(
                "canvas_get_assignment",
                arguments={
                    "course_id": course_id,
                    "assignment_id": assignment_id
                }
            )
            if hasattr(result, 'content') and len(result.content) > 0:
                content = result.content[0]
                if hasattr(content, 'text'):
                    return json.loads(content.text)
            return None
