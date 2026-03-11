"""
Canvas MCP Tools for interacting with Canvas LMS through the Smithery-hosted
aryankeluskar/canvas-mcp server via the Smithery CLI (stdio transport).
"""
import os
import json
import requests
from typing import Dict, List, Optional, Any
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from contextlib import asynccontextmanager


class CanvasTools:
    """Tools for interacting with Canvas LMS via the Smithery Canvas MCP server."""
    
    def __init__(self):
        self.canvas_url = os.getenv("CANVAS_API_URL", "https://canvas.instructure.com")
        self.canvas_token = os.getenv("CANVAS_API_TOKEN")
        self.use_mcp = os.getenv("CANVAS_USE_MCP", "true").strip().lower() in {
            "1", "true", "yes", "on"
        }

    def _canvas_headers(self) -> Dict[str, str]:
        if not self.canvas_token:
            raise ValueError("CANVAS_API_TOKEN is required")
        return {"Authorization": f"Bearer {self.canvas_token}"}

    def _direct_list_courses(self) -> List[Dict[str, Any]]:
        response = requests.get(
            f"{self.canvas_url.rstrip('/')}/api/v1/courses",
            headers=self._canvas_headers(),
            params={"per_page": 100, "enrollment_state": "active"},
            timeout=30,
        )
        response.raise_for_status()
        courses = response.json()
        return [{"id": c.get("id"), "name": c.get("name", "Unknown Course")} for c in courses]

    def _direct_get_course_assignments(self, course_id: int) -> List[Dict[str, Any]]:
        response = requests.get(
            f"{self.canvas_url.rstrip('/')}/api/v1/courses/{course_id}/assignments",
            headers=self._canvas_headers(),
            params={"per_page": 100},
            timeout=30,
        )
        response.raise_for_status()
        assignments = response.json()
        return [
            {
                "id": a.get("id"),
                "name": a.get("name", "Untitled Assignment"),
                "description": a.get("description", ""),
                "due_at": a.get("due_at"),
            }
            for a in assignments
        ]
        
    @asynccontextmanager
    async def get_canvas_session(self):
        """Create a Canvas MCP session via Smithery CLI (stdio)."""
        config = json.dumps({
            "canvasApiKey": self.canvas_token,
            "canvasBaseUrl": self.canvas_url,
        })
        
        server_params = StdioServerParameters(
            command="npx",
            args=[
                "-y", "@smithery/cli", "run",
                "@aryankeluskar/canvas-mcp",
                "--config", config,
            ],
        )
        
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                yield session
    
    async def list_courses(self) -> List[Dict[str, Any]]:
        """
        List all courses available to the user.
        
        Returns:
            List of course dictionaries with 'id' and 'name' keys
        """
        if not self.use_mcp:
            return self._direct_list_courses()

        try:
            async with self.get_canvas_session() as session:
                result = await session.call_tool("get_courses", arguments={})
                if hasattr(result, 'content') and len(result.content) > 0:
                    content = result.content[0]
                    if hasattr(content, 'text'):
                        data = json.loads(content.text)
                        # The Smithery canvas-mcp server returns courses as
                        # {"course_name": course_id, ...}.  Normalize to a list
                        # of dicts so the rest of the codebase can use .get().
                        if isinstance(data, dict):
                            return [
                                {"id": cid, "name": cname}
                                for cname, cid in data.items()
                            ]
                        return data
                return []
        except Exception:
            # Fallback to direct Canvas REST calls when MCP auth/connectivity fails.
            return self._direct_list_courses()
    
    async def get_course_assignments(self, course_id: int) -> List[Dict[str, Any]]:
        """
        Get all assignments for a specific course.
        
        Args:
            course_id: The Canvas course ID
            
        Returns:
            List of assignment dictionaries with 'id' and 'name' keys
        """
        if not self.use_mcp:
            return self._direct_get_course_assignments(course_id)

        try:
            async with self.get_canvas_session() as session:
                result = await session.call_tool(
                    "get_course_assignments",
                    arguments={"course_id": str(course_id)}
                )
                if hasattr(result, 'content') and len(result.content) > 0:
                    content = result.content[0]
                    if hasattr(content, 'text'):
                        data = json.loads(content.text)
                        # Normalize if server returns {"name": id, ...} dict
                        if isinstance(data, dict):
                            return [
                                {"id": aid, "name": aname}
                                for aname, aid in data.items()
                            ]
                        return data
                return []
        except Exception:
            return self._direct_get_course_assignments(course_id)
    
    async def get_assignment_details(self, course_id: int, assignment_id: int) -> Optional[Dict[str, Any]]:
        """
        Get detailed information about a specific assignment.
        
        Note: The Smithery canvas-mcp server does not have a single-assignment
        endpoint, so we fetch all assignments and filter by ID.
        
        Args:
            course_id: The Canvas course ID
            assignment_id: The assignment ID
            
        Returns:
            Assignment details dictionary
        """
        assignments = await self.get_course_assignments(course_id)
        for assignment in assignments:
            if str(assignment.get("id")) == str(assignment_id):
                return assignment
        return None
