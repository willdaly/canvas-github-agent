from app.delegation_policy import evaluate_delegation_policy


def test_policy_blocks_when_trust_level_below_minimum(monkeypatch):
    monkeypatch.setenv("DELEGATION_MIN_TRUST_LEVEL", "verified_profile")

    result = evaluate_delegation_policy(
        capability_family="execution",
        candidate={
            "agent_id": "stub-execution-agent",
            "name": "Stub Execution Agent",
            "trust_level": "test",
            "invocation": {"connection_url": "https://example.com/mcp"},
        },
        connection_id="stub-execution-agent",
        explicit_request=True,
    )

    assert result["allowed"] is False
    assert result["basis"] == "trust_threshold"


def test_policy_blocks_when_scorecard_thresholds_fail(monkeypatch):
    monkeypatch.setenv("DELEGATION_ENFORCE_SCORECARD_THRESHOLDS", "true")
    monkeypatch.setenv("DELEGATION_MIN_SCORECARD_SUCCESS_RATE", "0.7")
    monkeypatch.setenv("DELEGATION_MIN_SCORECARD_TOTAL_COUNT", "3")

    result = evaluate_delegation_policy(
        capability_family="evaluation",
        candidate={
            "agent_id": "stub-evaluation-agent",
            "name": "Stub Evaluation Agent",
            "trust_level": "verified",
            "invocation": {"connection_url": "https://example.com/mcp"},
        },
        connection_id="stub-evaluation-agent",
        explicit_request=True,
        scorecard={
            "agent_id": "stub-evaluation-agent",
            "capability_family": "evaluation",
            "success_rate": 0.5,
            "total_count": 2,
        },
    )

    assert result["allowed"] is False
    assert result["basis"] == "scorecard_threshold"
    assert result["scorecard_thresholds"]["allowed"] is False