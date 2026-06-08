from agentrl import Project, TargetedAgentHarness


def test_targeted_market_researcher_harness_infers_rag_and_review_components(tmp_path):
    targeted = TargetedAgentHarness.create(
        agent_name="Market Researcher",
        role="market_researcher",
        objective="Research a campaign market and produce evidence-backed recommendations",
    )

    names = {component.name for component in targeted.components}
    assert {"rag", "trace", "decision_log", "evaluation"}.issubset(names)
    assert targeted.harness.metadata["accountability"] == "ultimate_human_review"
    assert targeted.harness.name == "market-researcher-harness"


def test_project_create_agent_harness_registers_version(tmp_path):
    project = Project.init(tmp_path / "agentrl-targeted")

    result = project.create_agent_harness(
        "Market Researcher",
        "market_researcher",
        "Support a marketing campaign with RAG-grounded market analysis",
    )

    assert result["status"] == "created"
    assert "market-researcher-harness" in project.harnesses
    assert result["version"]["entity"] == "targeted_agent:Market Researcher"
