from app.registry import AgentRegistry


def test_registry_returns_seeded_candidates_for_capability_family():
    registry = AgentRegistry(smithery_command=None)

    candidates = registry.discover_agents(capability_family="evaluation", limit=3)

    assert candidates
    assert all(candidate["capability_family"] == "evaluation" for candidate in candidates)
    assert candidates[0]["ranking"]["score"] >= candidates[-1]["ranking"]["score"]


def test_registry_enriches_capability_groups():
    registry = AgentRegistry(smithery_command=None)

    enriched = registry.enrich_capability_groups(
        [
            {"capability": "execution", "priority": "high"},
            {"capability": "retrieval", "priority": "medium"},
        ],
        limit_per_group=2,
    )

    assert enriched[0]["candidates"]
    assert enriched[1]["candidates"]
    assert enriched[0]["candidates"][0]["capability_family"] == "execution"