"""Resolve WorkflowCredentials from env (legacy) or encrypted session store."""

from __future__ import annotations

import os

from fastapi import HTTPException, Request

from app.credentials import WorkflowCredentials, get_canvas_institution_url
from app.user_store import SESSION_COOKIE_NAME, UserStore, encryption_configured

USER_STORE = UserStore()


def session_auth_enabled() -> bool:
    """When True, API routes should use per-user tokens from a session cookie."""
    return encryption_configured()


def workflow_credentials_for_env() -> WorkflowCredentials:
    """MCP / server env path (always process environment)."""
    return WorkflowCredentials.from_env().with_notion_from_env()


def optional_session_user_id(request: Request | None) -> int | None:
    if not session_auth_enabled() or request is None:
        return None
    raw = request.cookies.get(SESSION_COOKIE_NAME)
    return USER_STORE.validate_session(raw)


def require_session_user_id(request: Request) -> int:
    uid = optional_session_user_id(request)
    if uid is None:
        raise HTTPException(
            status_code=401,
            detail="Not authenticated. Open the app and connect your Canvas and GitHub tokens under 'Your credentials'.",
        )
    return uid


def workflow_credentials_for_http(request: Request) -> WorkflowCredentials:
    """HTTP API: session store when configured, otherwise environment."""
    if not session_auth_enabled():
        return workflow_credentials_for_env()
    uid = require_session_user_id(request)
    try:
        canvas_tok, github_tok, github_user = USER_STORE.decrypt_workflow_tokens(uid)
    except Exception as exc:
        raise HTTPException(status_code=401, detail="Stored credentials could not be decrypted.") from exc
    _org = os.getenv("GITHUB_ORG", "").strip()
    github_org = _org if _org and not _org.startswith("#") else ""
    return WorkflowCredentials(
        canvas_url=get_canvas_institution_url(),
        canvas_token=canvas_tok,
        github_token=github_tok,
        github_username=github_user,
        github_org=github_org,
    ).with_notion_from_env()
