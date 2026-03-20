"""Lightweight outbound delegation policy checks for remote agents."""

from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any, Optional


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _split_env_list(name: str) -> set[str]:
    raw_value = os.getenv(name, "")
    return {item.strip().lower() for item in raw_value.split(",") if item.strip()}


def delegation_policy_enabled() -> bool:
    """Return whether outbound delegation allowlist checks are enabled."""
    return os.getenv("DELEGATION_REQUIRE_ALLOWLIST", "true").lower() == "true"


TRUST_LEVEL_ORDER = {
    "unknown": 0,
    "unverified": 1,
    "explicit_request": 2,
    "ecosystem_listed": 3,
    "test": 4,
    "verified_profile": 5,
    "verified": 6,
}


def _normalized_trust_level(value: str | None) -> str:
    return str(value or "unknown").strip().lower() or "unknown"


def _trust_level_rank(value: str | None) -> int:
    return TRUST_LEVEL_ORDER.get(_normalized_trust_level(value), 0)


def _minimum_trust_level() -> str:
    return _normalized_trust_level(os.getenv("DELEGATION_MIN_TRUST_LEVEL", "unknown"))


def _scorecard_thresholds() -> tuple[bool, float, int]:
    enforce = os.getenv("DELEGATION_ENFORCE_SCORECARD_THRESHOLDS", "false").lower() == "true"
    min_success_rate = float(os.getenv("DELEGATION_MIN_SCORECARD_SUCCESS_RATE", "0.0") or 0.0)
    min_total_count = int(os.getenv("DELEGATION_MIN_SCORECARD_TOTAL_COUNT", "0") or 0)
    return enforce, min_success_rate, min_total_count


def evaluate_delegation_policy(
    *,
    capability_family: str,
    candidate: dict[str, Any],
    connection_id: Optional[str] = None,
    connection_url: Optional[str] = None,
    explicit_request: bool = False,
    scorecard: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """Return the delegation policy decision for a remote subtask."""
    candidate_agent_id = str(candidate.get("agent_id") or "").strip().lower()
    candidate_connection_url = str(
        connection_url or candidate.get("invocation", {}).get("connection_url") or ""
    ).strip().lower()
    candidate_connection_id = str(connection_id or "").strip().lower()
    allow_explicit_requests = os.getenv("DELEGATION_ALLOW_EXPLICIT_REQUESTS", "true").lower() == "true"

    matched_rules: list[str] = []
    allowed = False
    basis = "blocked"

    if not delegation_policy_enabled():
        allowed = True
        basis = "policy_disabled"
        matched_rules.append("DELEGATION_REQUIRE_ALLOWLIST=false")
    elif explicit_request and allow_explicit_requests:
        allowed = True
        basis = "explicit_request"
        matched_rules.append("DELEGATION_ALLOW_EXPLICIT_REQUESTS=true")
    else:
        allowed_agent_ids = _split_env_list("DELEGATION_ALLOWED_AGENT_IDS")
        allowed_connection_ids = _split_env_list("DELEGATION_ALLOWED_CONNECTION_IDS")
        allowed_connection_urls = _split_env_list("DELEGATION_ALLOWED_CONNECTION_URLS")

        if candidate_agent_id and candidate_agent_id in allowed_agent_ids:
            allowed = True
            basis = "agent_allowlist"
            matched_rules.append("DELEGATION_ALLOWED_AGENT_IDS")
        elif candidate_connection_id and candidate_connection_id in allowed_connection_ids:
            allowed = True
            basis = "connection_allowlist"
            matched_rules.append("DELEGATION_ALLOWED_CONNECTION_IDS")
        elif candidate_connection_url and candidate_connection_url in allowed_connection_urls:
            allowed = True
            basis = "url_allowlist"
            matched_rules.append("DELEGATION_ALLOWED_CONNECTION_URLS")

    trust_level = _normalized_trust_level(candidate.get("trust_level"))
    min_trust_level = _minimum_trust_level()
    trust_allowed = _trust_level_rank(trust_level) >= _trust_level_rank(min_trust_level)

    enforce_scorecards, min_success_rate, min_total_count = _scorecard_thresholds()
    scorecard_allowed = True
    if enforce_scorecards:
        total_count = int((scorecard or {}).get("total_count") or 0)
        success_rate = float((scorecard or {}).get("success_rate") or 0.0)
        scorecard_allowed = total_count >= min_total_count and success_rate >= min_success_rate

    if allowed and not trust_allowed:
        allowed = False
        basis = "trust_threshold"
    if allowed and not scorecard_allowed:
        allowed = False
        basis = "scorecard_threshold"

    return {
        "allowed": allowed,
        "basis": basis,
        "capability_family": capability_family,
        "explicit_request": explicit_request,
        "candidate_agent_id": candidate.get("agent_id"),
        "candidate_name": candidate.get("name"),
        "trust_level": trust_level,
        "minimum_trust_level": min_trust_level,
        "scorecard": scorecard,
        "scorecard_thresholds": {
            "enforced": enforce_scorecards,
            "minimum_success_rate": min_success_rate,
            "minimum_total_count": min_total_count,
            "allowed": scorecard_allowed,
        },
        "connection_id": connection_id,
        "connection_url": connection_url or candidate.get("invocation", {}).get("connection_url"),
        "matched_rules": matched_rules,
        "checked_at": _utcnow_iso(),
    }