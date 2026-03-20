"""Agent discovery helpers for AGNTCY-style and MCP-oriented candidate selection."""

from __future__ import annotations

import json
import math
import os
import shutil
import subprocess
from typing import Any, Optional, Sequence


SEEDED_AGENT_CATALOG: list[dict[str, Any]] = [
    {
        "agent_id": "galileo-evaluation",
        "name": "Galileo",
        "source": "seeded_agntcy_ecosystem",
        "capability_family": "evaluation",
        "capabilities": ["evaluation", "quality_scoring", "trace_analysis"],
        "protocols": ["oasf", "unknown_runtime"],
        "trust_level": "ecosystem_listed",
        "description": "Evaluation-oriented ecosystem participant suitable for scoring assignment outputs.",
        "ecosystem_signals": ["AGNTCY public ecosystem listing"],
        "invocation": {"verified": False, "connection_url": None, "notes": "Public participation visible; runtime endpoint not verified."},
    },
    {
        "agent_id": "comet-opik-evaluation",
        "name": "Comet / Opik",
        "source": "seeded_agntcy_ecosystem",
        "capability_family": "evaluation",
        "capabilities": ["evaluation", "experiment_tracking", "agent_assessment"],
        "protocols": ["oasf", "unknown_runtime"],
        "trust_level": "ecosystem_listed",
        "description": "Evaluation platform suited to assessing generated agent outputs and workflows.",
        "ecosystem_signals": ["AGNTCY public ecosystem listing"],
        "invocation": {"verified": False, "connection_url": None, "notes": "Public participation visible; runtime endpoint not verified."},
    },
    {
        "agent_id": "arize-evaluation",
        "name": "Arize",
        "source": "seeded_agntcy_ecosystem",
        "capability_family": "evaluation",
        "capabilities": ["evaluation", "monitoring", "quality_analysis"],
        "protocols": ["oasf", "unknown_runtime"],
        "trust_level": "ecosystem_listed",
        "description": "Evaluation and measurement platform relevant for assignment output quality checks.",
        "ecosystem_signals": ["AGNTCY public ecosystem listing"],
        "invocation": {"verified": False, "connection_url": None, "notes": "Public participation visible; runtime endpoint not verified."},
    },
    {
        "agent_id": "dagger-execution",
        "name": "Dagger",
        "source": "seeded_agntcy_ecosystem",
        "capability_family": "execution",
        "capabilities": ["execution", "sandboxing", "pipeline_runtime"],
        "protocols": ["oasf", "unknown_runtime"],
        "trust_level": "ecosystem_listed",
        "description": "Execution-oriented runtime suitable for running tests and controlled workflows.",
        "ecosystem_signals": ["AGNTCY public ecosystem listing"],
        "invocation": {"verified": False, "connection_url": None, "notes": "Public participation visible; runtime endpoint not verified."},
    },
    {
        "agent_id": "smythos-execution",
        "name": "SmythOS",
        "source": "seeded_agntcy_ecosystem",
        "capability_family": "execution",
        "capabilities": ["execution", "agent_runtime", "workflow_execution"],
        "protocols": ["oasf", "unknown_runtime"],
        "trust_level": "ecosystem_listed",
        "description": "Agent execution platform relevant for controlled assignment workflow execution.",
        "ecosystem_signals": ["AGNTCY public ecosystem listing"],
        "invocation": {"verified": False, "connection_url": None, "notes": "Public participation visible; runtime endpoint not verified."},
    },
    {
        "agent_id": "llamaindex-retrieval",
        "name": "LlamaIndex",
        "source": "seeded_agntcy_ecosystem",
        "capability_family": "retrieval",
        "capabilities": ["retrieval", "knowledge_management", "context_augmentation"],
        "protocols": ["oasf", "unknown_runtime"],
        "trust_level": "ecosystem_listed",
        "description": "Knowledge and parsing platform relevant for assignment context augmentation.",
        "ecosystem_signals": ["AGNTCY public ecosystem listing"],
        "invocation": {"verified": False, "connection_url": None, "notes": "Public participation visible; runtime endpoint not verified."},
    },
    {
        "agent_id": "zep-memory",
        "name": "Zep",
        "source": "seeded_agntcy_ecosystem",
        "capability_family": "retrieval",
        "capabilities": ["memory", "retrieval", "context_persistence"],
        "protocols": ["oasf", "unknown_runtime"],
        "trust_level": "ecosystem_listed",
        "description": "Memory-oriented platform relevant for persistent context across assignment runs.",
        "ecosystem_signals": ["AGNTCY public ecosystem listing"],
        "invocation": {"verified": False, "connection_url": None, "notes": "Public participation visible; runtime endpoint not verified."},
    },
    {
        "agent_id": "ory-identity-policy",
        "name": "Ory",
        "source": "seeded_agntcy_ecosystem",
        "capability_family": "identity_policy",
        "capabilities": ["identity", "authentication", "policy"],
        "protocols": ["oasf", "unknown_runtime"],
        "trust_level": "ecosystem_listed",
        "description": "Identity and authorization platform relevant for trusted outbound delegation.",
        "ecosystem_signals": ["AGNTCY public ecosystem listing"],
        "invocation": {"verified": False, "connection_url": None, "notes": "Public participation visible; runtime endpoint not verified."},
    },
]


CAPABILITY_QUERY_TERMS = {
    "evaluation": "evaluation",
    "execution": "execution",
    "retrieval": "retrieval",
    "identity_policy": "identity",
}


class AgentRegistry:
    """Discover candidate agents from seeded catalog data and optional live Smithery search."""

    def __init__(
        self,
        *,
        seed_catalog: Optional[Sequence[dict[str, Any]]] = None,
        smithery_command: Optional[str] = None,
    ):
        self.seed_catalog = list(seed_catalog or SEEDED_AGENT_CATALOG)
        self.smithery_command = smithery_command or shutil.which("smithery")

    @staticmethod
    def _normalize_agent_id(value: str) -> str:
        return value.strip().lower().replace("/", "-").replace(" ", "-")

    @staticmethod
    def _capability_fit_score(candidate_family: str, requested_family: Optional[str]) -> float:
        if not requested_family:
            return 0.6
        return 1.0 if candidate_family == requested_family else 0.35

    @staticmethod
    def _use_count_score(use_count: int | None) -> float:
        if not use_count:
            return 0.0
        return min(math.log10(use_count + 1) / 4.0, 1.0)

    def _rank_candidate(
        self,
        candidate: dict[str, Any],
        *,
        requested_family: Optional[str],
        source_bonus: float,
        use_count: int | None = None,
    ) -> dict[str, Any]:
        capability_fit = self._capability_fit_score(candidate.get("capability_family", ""), requested_family)
        popularity = self._use_count_score(use_count)
        score = round(capability_fit * 0.65 + source_bonus + popularity * 0.15, 3)
        candidate["ranking"] = {
            "capability_fit": round(capability_fit, 3),
            "source_bonus": round(source_bonus, 3),
            "popularity": round(popularity, 3),
            "score": score,
        }
        return candidate

    def _filter_seed_catalog(
        self,
        *,
        capability_family: Optional[str],
        query: Optional[str],
        limit: int,
    ) -> list[dict[str, Any]]:
        query_text = (query or "").strip().lower()
        results: list[dict[str, Any]] = []

        for entry in self.seed_catalog:
            if capability_family and entry.get("capability_family") != capability_family:
                continue
            if query_text:
                haystack = " ".join(
                    [
                        entry.get("name", ""),
                        entry.get("description", ""),
                        " ".join(entry.get("capabilities", [])),
                    ]
                ).lower()
                if query_text not in haystack:
                    continue

            ranked = self._rank_candidate(dict(entry), requested_family=capability_family, source_bonus=0.35)
            results.append(ranked)

        results.sort(key=lambda item: item["ranking"]["score"], reverse=True)
        return results[:limit]

    def _smithery_query(self, capability_family: Optional[str], query: Optional[str]) -> str:
        if query:
            return query
        if capability_family:
            return CAPABILITY_QUERY_TERMS.get(capability_family, capability_family)
        return "agent"

    def _discover_via_smithery(
        self,
        *,
        capability_family: Optional[str],
        query: Optional[str],
        limit: int,
        verified_only: bool,
    ) -> list[dict[str, Any]]:
        if not self.smithery_command:
            return []

        command = [
            self.smithery_command,
            "mcp",
            "search",
            self._smithery_query(capability_family, query),
            "--limit",
            str(limit),
            "--json",
        ]
        if verified_only:
            command.append("--verified")

        result = subprocess.run(command, capture_output=True, text=True, check=False)
        if result.returncode != 0 or not result.stdout.strip():
            return []

        payload = json.loads(result.stdout)
        candidates: list[dict[str, Any]] = []

        for item in payload.get("servers", []):
            candidate = {
                "agent_id": self._normalize_agent_id(item.get("qualifiedName") or item.get("name") or "unknown"),
                "name": item.get("name") or item.get("qualifiedName") or "Unknown Agent",
                "source": "smithery_search",
                "capability_family": capability_family or "general",
                "capabilities": [capability_family] if capability_family else [],
                "protocols": ["mcp"],
                "trust_level": "unverified",
                "description": item.get("description", ""),
                "ecosystem_signals": ["Smithery MCP search result"],
                "invocation": {
                    "verified": False,
                    "connection_url": item.get("connectionUrl"),
                    "qualified_name": item.get("qualifiedName"),
                    "notes": payload.get("hint"),
                },
            }
            candidates.append(
                self._rank_candidate(
                    candidate,
                    requested_family=capability_family,
                    source_bonus=0.2,
                    use_count=item.get("useCount"),
                )
            )

        candidates.sort(key=lambda item: item["ranking"]["score"], reverse=True)
        return candidates[:limit]

    def discover_agents(
        self,
        *,
        capability_family: Optional[str] = None,
        query: Optional[str] = None,
        limit: int = 5,
        include_live_results: bool = False,
        verified_only: bool = False,
    ) -> list[dict[str, Any]]:
        """Return ranked candidate agents for the requested capability or query."""
        normalized_limit = max(1, min(limit, 20))
        candidates = self._filter_seed_catalog(
            capability_family=capability_family,
            query=query,
            limit=normalized_limit,
        )

        should_use_live = include_live_results or os.getenv("AGENT_DISCOVERY_ENABLE_SMITHERY", "false").lower() == "true"
        if should_use_live:
            live_candidates = self._discover_via_smithery(
                capability_family=capability_family,
                query=query,
                limit=normalized_limit,
                verified_only=verified_only,
            )
            candidates.extend(live_candidates)

        candidates.sort(key=lambda item: item["ranking"]["score"], reverse=True)
        return candidates[:normalized_limit]

    def enrich_capability_groups(
        self,
        groups: Sequence[dict[str, Any]],
        *,
        limit_per_group: int = 3,
        include_live_results: bool = False,
        verified_only: bool = False,
    ) -> list[dict[str, Any]]:
        """Attach concrete candidate agents to planning-level capability groups."""
        enriched: list[dict[str, Any]] = []
        for group in groups:
            capability = group.get("capability") or group.get("preferred_capability")
            enriched_group = dict(group)
            enriched_group["candidates"] = self.discover_agents(
                capability_family=capability,
                query=None,
                limit=limit_per_group,
                include_live_results=include_live_results,
                verified_only=verified_only,
            )
            enriched.append(enriched_group)
        return enriched