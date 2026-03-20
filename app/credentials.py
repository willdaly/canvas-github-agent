"""Per-request workflow credentials (Canvas + GitHub + optional Notion from env)."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional


DEFAULT_CANVAS_INSTITUTION_URL = "https://northeastern.instructure.com"


def get_canvas_institution_url() -> str:
    """Northeastern Canvas base URL (no trailing path)."""
    return (
        os.getenv("CANVAS_INSTITUTION_URL", DEFAULT_CANVAS_INSTITUTION_URL).strip().rstrip("/")
        or DEFAULT_CANVAS_INSTITUTION_URL.rstrip("/")
    )


@dataclass(frozen=True)
class WorkflowCredentials:
    """Secrets and defaults for one workflow run (one end-user or env fallback)."""

    canvas_url: str
    canvas_token: str
    github_token: str
    github_username: str
    github_org: str = ""
    notion_token: Optional[str] = None
    notion_parent_page_id: Optional[str] = None

    @classmethod
    def from_env(cls) -> WorkflowCredentials:
        """Legacy single-tenant: read from process environment."""
        canvas_url = (os.getenv("CANVAS_API_URL") or get_canvas_institution_url()).strip().rstrip("/")
        _org = os.getenv("GITHUB_ORG", "").strip()
        github_org = _org if _org and not _org.startswith("#") else ""
        return cls(
            canvas_url=canvas_url or get_canvas_institution_url(),
            canvas_token=(os.getenv("CANVAS_API_TOKEN") or "").strip(),
            github_token=(os.getenv("GITHUB_TOKEN") or "").strip(),
            github_username=(os.getenv("GITHUB_USERNAME") or "").strip(),
            github_org=github_org,
            notion_token=(os.getenv("NOTION_TOKEN") or "").strip() or None,
            notion_parent_page_id=(os.getenv("NOTION_PARENT_PAGE_ID") or "").strip() or None,
        )

    def with_notion_from_env(self) -> WorkflowCredentials:
        """Fill Notion fields from env if missing (writing flow)."""
        if self.notion_token and self.notion_parent_page_id:
            return self
        nt = self.notion_token or (os.getenv("NOTION_TOKEN") or "").strip() or None
        np = self.notion_parent_page_id or (os.getenv("NOTION_PARENT_PAGE_ID") or "").strip() or None
        return WorkflowCredentials(
            canvas_url=self.canvas_url,
            canvas_token=self.canvas_token,
            github_token=self.github_token,
            github_username=self.github_username,
            github_org=self.github_org,
            notion_token=nt,
            notion_parent_page_id=np,
        )
