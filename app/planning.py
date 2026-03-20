"""Assignment planning helpers for pre-execution analysis."""

from __future__ import annotations

from typing import Any, Optional, Sequence

from app.agent import CanvasGitHubAgent


def _assignment_text(assignment: dict[str, Any]) -> str:
    name = assignment.get("name", "")
    description = CanvasGitHubAgent.strip_html(assignment.get("description", ""))
    return f"{name}\n{description}".lower()


def infer_assignment_domain(assignment: dict[str, Any], assignment_type: str) -> str:
    """Classify the assignment into a planning domain."""
    if assignment_type == "writing":
        return "writing"

    text = _assignment_text(assignment)
    if any(keyword in text for keyword in ["maze", "bfs", "dfs", "a*", "pathfinding"]):
        return "maze_search"
    if any(
        keyword in text
        for keyword in ["nsl-kdd", "kagglehub", "machine learning", "model", "classification"]
    ):
        return "ml_project"
    return "coding_general"


def required_artifacts_for_domain(domain: str) -> list[str]:
    """Return the expected output artifacts for the chosen domain."""
    if domain == "writing":
        return ["Notion page or report draft", "outline", "supporting notes"]
    if domain == "maze_search":
        return ["README.md", "main.py", "maze_solvers.py", "tests", "benchmark results"]
    if domain == "ml_project":
        return [
            "README.md",
            "main.py",
            "src/data_loader.py",
            "src/eda.py",
            "src/train_models.py",
            "Report.md",
            "PRESENTATION.md",
            "tests",
        ]
    return ["README.md", "main.py", "tests"]


def build_subtasks(domain: str, assignment_type: str) -> list[dict[str, Any]]:
    """Return a plan-oriented task graph for the assignment."""
    subtasks = [
        {
            "id": "retrieve_context",
            "title": "Retrieve assignment context",
            "mode": "local",
            "purpose": "Collect Canvas and course-document context relevant to the assignment.",
        },
        {
            "id": "generate_primary_artifacts",
            "title": "Generate primary artifacts",
            "mode": "local",
            "purpose": "Create the initial repo or writing artifacts using the local workflow.",
        },
    ]

    if assignment_type == "coding":
        subtasks.append(
            {
                "id": "validate_generated_project",
                "title": "Validate generated project",
                "mode": "delegation_candidate",
                "preferred_capability": "evaluation",
                "purpose": "Check alignment between generated code and assignment requirements.",
            }
        )
        subtasks.append(
            {
                "id": "execute_generated_project",
                "title": "Execute generated project",
                "mode": "delegation_candidate",
                "preferred_capability": "execution",
                "purpose": "Run tests, benchmarks, notebooks, or smoke checks in a controlled environment.",
            }
        )

    if domain in {"maze_search", "ml_project"}:
        subtasks.append(
            {
                "id": "augment_domain_context",
                "title": "Augment domain context",
                "mode": "delegation_candidate",
                "preferred_capability": "retrieval",
                "purpose": "Retrieve supplementary domain-specific knowledge or memory beyond local context.",
            }
        )

    return subtasks


def build_delegation_candidates(domain: str, assignment_type: str) -> list[dict[str, Any]]:
    """Return capability-oriented external agent categories to investigate."""
    candidates: list[dict[str, Any]] = []

    if assignment_type == "coding":
        candidates.append(
            {
                "capability": "evaluation",
                "priority": "high",
                "why": "Independent validation can catch missing artifacts and weak assignment alignment.",
                "ecosystem_signals": ["Galileo", "Comet/Opik", "Arize", "Vijil", "Traceloop"],
            }
        )
        candidates.append(
            {
                "capability": "execution",
                "priority": "high",
                "why": "Controlled execution improves confidence that generated repos actually run.",
                "ecosystem_signals": ["Dagger", "SmythOS", "Dynamiq", "AG2", "CrewAI", "VoltAgent"],
            }
        )

    if domain in {"maze_search", "ml_project"}:
        candidates.append(
            {
                "capability": "retrieval",
                "priority": "medium",
                "why": "Supplementary retrieval can improve domain grounding beyond Canvas and local Chroma.",
                "ecosystem_signals": ["LlamaIndex", "Glean", "Weaviate", "Zep"],
            }
        )

    candidates.append(
        {
            "capability": "identity_policy",
            "priority": "later",
            "why": "Policy and trust controls become important once outbound delegation is enabled.",
            "ecosystem_signals": ["Ory", "Permit", "Yokai", "Duo"],
        }
    )
    return candidates


def build_validation_steps(domain: str, assignment_type: str) -> list[str]:
    """Return recommended validation steps for the plan."""
    steps = ["Confirm assignment type and destination routing."]
    if assignment_type == "coding":
        steps.extend(
            [
                "Run generated tests or smoke checks.",
                "Validate artifact completeness against the assignment brief.",
            ]
        )
    if domain == "maze_search":
        steps.append("Verify maze solver outputs and benchmark execution.")
    if domain == "ml_project":
        steps.append("Verify data-loading, EDA, and model-training scripts execute without template errors.")
    if assignment_type == "writing":
        steps.append("Review outline structure and source-note completeness before publishing.")
    return steps


def build_recommendations(domain: str, assignment_type: str, course_context: Sequence[dict[str, Any]]) -> list[str]:
    """Return human-readable plan recommendations."""
    recommendations = [
        "Keep the local workflow as the default execution path until external delegation is verified.",
    ]
    if assignment_type == "coding":
        recommendations.append("Prioritize an external evaluation agent before adding generative delegation.")
    if domain == "ml_project":
        recommendations.append("Use an external execution or sandbox agent to run smoke checks on training and EDA scripts.")
    if domain == "maze_search":
        recommendations.append("Use an external execution agent to run benchmarks and solver validation on generated maze artifacts.")
    if not course_context:
        recommendations.append("Ingest more course documents or enrich module context before attempting remote delegation.")
    return recommendations


def compute_confidence(domain: str, assignment_type: str, course_context: Sequence[dict[str, Any]]) -> float:
    """Return a lightweight confidence score for the generated plan."""
    score = 0.55
    if assignment_type == "coding":
        score += 0.1
    if domain in {"maze_search", "ml_project"}:
        score += 0.1
    if course_context:
        score += min(0.15, len(course_context) * 0.03)
    return round(min(score, 0.95), 2)


async def generate_assignment_plan(
    *,
    course_id: int,
    assignment_id: Optional[int],
    language: str,
    assignment_type: Optional[str],
    notion_content_mode: Optional[str],
    agent_factory: type[CanvasGitHubAgent] = CanvasGitHubAgent,
) -> dict[str, Any]:
    """Build a structured execution plan for the selected assignment."""
    agent = agent_factory()
    assignment = await agent.fetch_assignment(course_id, assignment_id)
    course_context = await agent.fetch_course_context(course_id, assignment)
    resolved_assignment_type = assignment_type or agent.infer_assignment_type(assignment)
    domain = infer_assignment_domain(assignment, resolved_assignment_type)

    return {
        "assignment": {
            "id": assignment.get("id"),
            "name": assignment.get("name"),
            "due_at": assignment.get("due_at"),
            "workflow_state": assignment.get("workflow_state"),
            "is_completed": assignment.get("is_completed"),
        },
        "plan": {
            "domain": domain,
            "assignment_type": resolved_assignment_type,
            "language": language if resolved_assignment_type == "coding" else None,
            "destination": "github" if resolved_assignment_type == "coding" else "notion",
            "notion_content_mode": notion_content_mode if resolved_assignment_type == "writing" else None,
            "required_artifacts": required_artifacts_for_domain(domain),
            "subtasks": build_subtasks(domain, resolved_assignment_type),
            "delegation_candidates": build_delegation_candidates(domain, resolved_assignment_type),
            "validation_steps": build_validation_steps(domain, resolved_assignment_type),
            "context_summary": {
                "match_count": len(course_context),
                "top_sections": [
                    item.get("section_title") or item.get("document_name") or "Course reference"
                    for item in list(course_context)[:3]
                ],
            },
        },
        "recommendations": build_recommendations(domain, resolved_assignment_type, course_context),
        "confidence": compute_confidence(domain, resolved_assignment_type, course_context),
    }