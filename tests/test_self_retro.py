from agentrl import Project


def test_agentrl_self_traverses_trace_feedback_to_root_cause_and_reinforces(tmp_path):
    project = Project.init(tmp_path / "agent")
    project.create_agent_harness(
        agent_name="Market Researcher",
        role="market_researcher",
        objective="Research local demand with RAG evidence",
        components=["rag", "trace", "evaluation"],
    )

    result = project.self_retro(
        {
            "final_review": "Final review found weak competitor pricing evidence.",
            "trace_paths": ["traces/market-researcher.jsonl", "traces/analytics-agent.jsonl"],
            "signals": ["Market Researcher omitted competitor pricing citations"],
        }
    )

    assert result["status"] == "reinforced"
    assert result["root_cause"]["target"] == "Market Researcher"
    assert result["root_cause"]["trace_paths"] == ["traces/market-researcher.jsonl", "traces/analytics-agent.jsonl"]
    assert "competitor pricing" in result["feedback"]["instruction"]
