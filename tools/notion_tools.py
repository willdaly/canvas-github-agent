"""
Notion integration tools for creating assignment pages.
"""
import os
from typing import Dict, Optional, Any
import asyncio
import requests


class NotionTools:
    """Tools for interacting with Notion API."""

    def __init__(self):
        self.notion_token = os.getenv("NOTION_TOKEN")
        self.parent_page_id = os.getenv("NOTION_PARENT_PAGE_ID")
        self.api_version = "2022-06-28"

    def _create_assignment_page_sync(
        self,
        title: str,
        description: str,
        due_date: str,
    ) -> Optional[Dict[str, Any]]:
        """Synchronous helper to create a Notion page."""
        if not self.notion_token or not self.parent_page_id:
            return None

        url = "https://api.notion.com/v1/pages"
        headers = {
            "Authorization": f"Bearer {self.notion_token}",
            "Notion-Version": self.api_version,
            "Content-Type": "application/json",
        }

        payload = {
            "parent": {"page_id": self.parent_page_id},
            "properties": {
                "title": {
                    "title": [
                        {
                            "type": "text",
                            "text": {"content": title[:2000]},
                        }
                    ]
                }
            },
            "children": [
                {
                    "object": "block",
                    "type": "heading_2",
                    "heading_2": {
                        "rich_text": [
                            {
                                "type": "text",
                                "text": {"content": "Assignment Overview"},
                            }
                        ]
                    },
                },
                {
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": [
                            {
                                "type": "text",
                                "text": {"content": f"Due date: {due_date}"},
                            }
                        ]
                    },
                },
                {
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": [
                            {
                                "type": "text",
                                "text": {"content": description[:2000] or "No description provided."},
                            }
                        ]
                    },
                },
            ],
        }

        try:
            response = requests.post(url, headers=headers, json=payload, timeout=30)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Error creating Notion page '{title}': {e}")
            return None

    async def create_assignment_page(
        self,
        title: str,
        description: str,
        due_date: str,
    ) -> Optional[Dict[str, Any]]:
        """Create a Notion page for an assignment."""
        return await asyncio.to_thread(
            self._create_assignment_page_sync,
            title,
            description,
            due_date,
        )
