from agentrl import Project


def test_project_reinforce_records_retro_feedback_and_evolves_targeted_harness(tmp_path):
    project = Project.init(tmp_path / "agent")
    project.create_agent_harness(
        agent_name="Market Researcher",
        role="market_researcher",
        objective="Research local demand with RAG evidence",
        components=["rag", "trace", "evaluation"],
    )

    result = project.reinforce(
        {
            "source": "campaign_retrospective",
            "target": "Market Researcher",
            "instruction": "Require competitor price citations before recommendations.",
            "reinforcement_targets": ["evaluation", "memory", "prompts"],
        }
    )

    assert result["status"] == "reinforced"
    assert result["target"] == "Market Researcher"
    assert result["candidate"]["strategy"] == "retrospective"
    assert (project.root / ".agentrl" / "reinforcements").exists()
    assert "competitor price citations" in result["feedback"]["instruction"]
