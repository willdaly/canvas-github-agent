"""
Canvas MCP Tools for interacting with Canvas LMS through the Smithery-hosted
aryankeluskar/canvas-mcp server via the Smithery CLI (stdio transport).
"""
import os
import json
import re
import requests
from typing import Dict, List, Optional, Any
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from contextlib import asynccontextmanager

from scaffolding.templates import html_to_markdown


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

    def _normalize_assignment(self, assignment: Dict[str, Any]) -> Dict[str, Any]:
        submission = assignment.get("submission") or {}
        submitted_at = submission.get("submitted_at")
        workflow_state = submission.get("workflow_state") or assignment.get("workflow_state")
        is_completed = bool(
            assignment.get("has_submitted_submissions")
            or submitted_at
            or workflow_state in {"submitted", "graded", "pending_review"}
        )

        return {
            "id": assignment.get("id"),
            "name": assignment.get("name", "Untitled Assignment"),
            "description": assignment.get("description", ""),
            "due_at": assignment.get("due_at"),
            "has_submitted_submissions": bool(assignment.get("has_submitted_submissions")),
            "submission": submission or None,
            "submitted_at": submitted_at,
            "workflow_state": workflow_state,
            "is_completed": is_completed,
        }

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
            params={"per_page": 100, "include[]": "submission"},
            timeout=30,
        )
        response.raise_for_status()
        assignments = response.json()
        return [self._normalize_assignment(assignment) for assignment in assignments]

    def _normalize_module_item(self, item: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "id": item.get("id"),
            "title": item.get("title") or item.get("page_url") or item.get("type", "Module Item"),
            "type": item.get("type", "Unknown"),
            "content_id": item.get("content_id"),
            "page_url": item.get("page_url"),
            "html_url": item.get("html_url"),
            "url": item.get("url"),
            "external_url": item.get("external_url"),
        }

    def _normalize_module(self, module: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "id": module.get("id"),
            "name": module.get("name") or f"Module {module.get('id', '')}".strip(),
            "position": module.get("position"),
            "items": [self._normalize_module_item(item) for item in module.get("items", [])],
        }

    def _direct_get_course_modules(self, course_id: int) -> List[Dict[str, Any]]:
        response = requests.get(
            f"{self.canvas_url.rstrip('/')}/api/v1/courses/{course_id}/modules",
            headers=self._canvas_headers(),
            params=[("per_page", 100), ("include[]", "items")],
            timeout=30,
        )
        response.raise_for_status()
        modules = response.json()
        return [self._normalize_module(module) for module in modules]

    def _direct_get_assignment(self, course_id: int, assignment_id: int) -> Dict[str, Any]:
        response = requests.get(
            f"{self.canvas_url.rstrip('/')}/api/v1/courses/{course_id}/assignments/{assignment_id}",
            headers=self._canvas_headers(),
            timeout=30,
        )
        response.raise_for_status()
        return self._normalize_assignment(response.json())

    def _direct_get_page(self, course_id: int, page_url: str) -> Dict[str, Any]:
        response = requests.get(
            f"{self.canvas_url.rstrip('/')}/api/v1/courses/{course_id}/pages/{page_url}",
            headers=self._canvas_headers(),
            timeout=30,
        )
        response.raise_for_status()
        return response.json()

    def _direct_get_discussion_topic(self, course_id: int, topic_id: int) -> Dict[str, Any]:
        response = requests.get(
            f"{self.canvas_url.rstrip('/')}/api/v1/courses/{course_id}/discussion_topics/{topic_id}",
            headers=self._canvas_headers(),
            timeout=30,
        )
        response.raise_for_status()
        return response.json()

    @staticmethod
    def _query_terms(query: str) -> list[str]:
        stopwords = {
            "about", "after", "again", "assignment", "before", "being", "from", "have",
            "into", "just", "more", "that", "than", "their", "them", "then", "there",
            "these", "this", "through", "using", "with", "write", "your",
        }
        terms = [term for term in re.findall(r"[a-z0-9]{3,}", query.lower()) if term not in stopwords]
        return list(dict.fromkeys(terms))

    def _build_module_context_entry(
        self,
        *,
        course_id: int,
        module: Dict[str, Any],
        item: Dict[str, Any],
        text: str,
    ) -> Dict[str, Any]:
        section_title = item.get("title") or item.get("page_url") or item.get("type", "Module Item")
        document_name = f"Canvas Module: {module.get('name', 'Course Module')}"
        return {
            "id": f"module:{course_id}:{module.get('id')}:{item.get('id')}",
            "course_id": course_id,
            "document_id": f"module-{module.get('id')}",
            "document_name": document_name,
            "module_id": module.get("id"),
            "module_name": module.get("name"),
            "item_id": item.get("id"),
            "item_type": item.get("type"),
            "section_title": section_title,
            "source_kind": "canvas_module",
            "source_path": item.get("html_url") or item.get("external_url") or item.get("url"),
            "text": text.strip(),
        }

    def _module_item_to_context(
        self,
        course_id: int,
        module: Dict[str, Any],
        item: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        title = item.get("title") or item.get("page_url") or item.get("type", "Module Item")
        item_type = item.get("type", "Unknown")
        text_parts = [
            f"Module: {module.get('name', 'Course Module')}",
            f"Item: {title}",
            f"Type: {item_type}",
        ]

        if item_type == "Page" and item.get("page_url"):
            page = self._direct_get_page(course_id, item["page_url"])
            title = page.get("title") or title
            body = html_to_markdown(page.get("body", ""))
            if body:
                text_parts.append(body)
        elif item_type == "Assignment" and item.get("content_id"):
            assignment = self._direct_get_assignment(course_id, int(item["content_id"]))
            title = assignment.get("name") or title
            description = html_to_markdown(assignment.get("description", ""))
            if description:
                text_parts.append(description)
            if assignment.get("due_at"):
                text_parts.append(f"Due: {assignment['due_at']}")
        elif item_type == "Discussion" and item.get("content_id"):
            discussion = self._direct_get_discussion_topic(course_id, int(item["content_id"]))
            title = discussion.get("title") or title
            message = html_to_markdown(discussion.get("message", ""))
            if message:
                text_parts.append(message)
        elif item_type == "ExternalUrl" and item.get("external_url"):
            text_parts.append(f"External URL: {item['external_url']}")
        elif item_type == "File":
            file_url = item.get("html_url") or item.get("url")
            if file_url:
                text_parts.append(f"File URL: {file_url}")

        item_with_title = dict(item)
        item_with_title["title"] = title
        text = "\n\n".join(part.strip() for part in text_parts if part and part.strip())
        if not text.strip():
            return None
        return self._build_module_context_entry(course_id=course_id, module=module, item=item_with_title, text=text)

    def _score_module_context(self, query_terms: list[str], entry: Dict[str, Any]) -> int:
        haystack = " ".join(
            [
                entry.get("document_name", ""),
                entry.get("section_title", ""),
                entry.get("text", ""),
            ]
        ).lower()
        return sum(1 for term in query_terms if term in haystack)

    def _direct_search_course_module_context(
        self,
        course_id: int,
        query: str,
        limit: int = 5,
    ) -> List[Dict[str, Any]]:
        query_terms = self._query_terms(query)
        if not query_terms:
            return []

        modules = self._direct_get_course_modules(course_id)
        scored: list[tuple[int, Dict[str, Any]]] = []

        for module in modules:
            for item in module.get("items", []):
                try:
                    entry = self._module_item_to_context(course_id, module, item)
                except requests.RequestException:
                    entry = self._build_module_context_entry(
                        course_id=course_id,
                        module=module,
                        item=item,
                        text="\n\n".join(
                            part for part in [
                                f"Module: {module.get('name', 'Course Module')}",
                                f"Item: {item.get('title') or item.get('type', 'Module Item')}",
                                f"Type: {item.get('type', 'Unknown')}",
                            ]
                            if part
                        ),
                    )

                if not entry:
                    continue

                score = self._score_module_context(query_terms, entry)
                if score <= 0:
                    continue

                entry["distance"] = round(1 / score, 4)
                scored.append((score, entry))

        scored.sort(key=lambda pair: (-pair[0], pair[1].get("document_name", ""), pair[1].get("section_title", "")))
        return [entry for _, entry in scored[: max(limit, 1)]]
        
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
                        return [self._normalize_assignment(assignment) for assignment in data]
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

    async def get_course_modules(self, course_id: int) -> List[Dict[str, Any]]:
        """Return Canvas modules and normalized module items for a course."""
        return self._direct_get_course_modules(course_id)

    async def search_course_module_context(
        self,
        course_id: int,
        query: str,
        limit: int = 5,
    ) -> List[Dict[str, Any]]:
        """Search Canvas course module content for assignment-relevant context."""
        return self._direct_search_course_module_context(course_id, query, limit)
