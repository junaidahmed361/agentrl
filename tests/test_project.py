from pathlib import Path

from agentrl import Project
from agentrl.harness import Harness
from agentrl.models import Task, TaskSet


def test_project_compile_evaluate_deploy(tmp_path: Path):
    project = Project.init(tmp_path / "my-agent-system")
    records = project.compile()
    assert {"coding", "rag", "tool_use"} == set(project.harnesses)
    assert len(records) == 3

    results = project.evaluate()
    assert all(r.task_count >= 1 for r in results)
    assert all(r.pass_rate == 1.0 for r in results)

    evolved = project.auto_harness()
    assert evolved["promoted"] is True
    assert evolved["mode"] == "static"

    deployment = project.deploy()
    assert deployment["status"] == "deployed"
    assert (project.root / ".agentrl" / "deployments" / "local" / "deployment.json").exists()


def test_goal_workflow_and_approval_gate(tmp_path: Path):
    project = Project.init(tmp_path / "goal-project")
    result = project.run_goal("Fix the failing login test.")
    assert result["harness"] == "coding"
    assert "evaluate result" in result["plan"]
    assert result["evaluation"]["failures"][-1]["result"]["error"] == "unverifiable_task"

    blocked = project.promote({"id": "candidate-1"}, require_approval=True)
    assert blocked["status"] == "blocked"

    promoted = project.promote({"id": "candidate-1", "approved": True}, require_approval=True)
    assert promoted["status"] == "promoted"


def test_registry_diff_and_default_rollback_restore_source_path(tmp_path: Path):
    project = Project.init(tmp_path / "registry-project")
    first = project.compile()[0]
    project.harness("coding").prompts["system"] += "\nChanged prompt."
    second = project.compile()[0]

    diff = project.registry.diff(first["id"], second["id"])
    assert "Changed prompt" in diff

    compiled_path = project.root / first["metadata"]["source_path"]
    compiled_path.write_text("{}", encoding="utf-8")
    restored = project.registry.rollback(first["id"])

    assert restored == compiled_path
    assert "Changed prompt" not in restored.read_text(encoding="utf-8")


def test_evaluation_records_failure_trace_for_missing_sandbox(tmp_path: Path):
    harness = Harness(name="custom", kind="coding", goal="missing sandbox")
    harness.add_tasks(TaskSet(
        name="missing_sandbox",
        tasks=[Task(
            id="missing-sandbox",
            description="Should not crash when cwd is missing",
            kind="coding",
            expected={"command": "python3 -c 'print(1)'"},
            metadata={"sandbox": {"path": str(tmp_path / "missing")}},
            reward="pytest",
        )],
    ))

    result = harness.evaluate(tmp_path, tmp_path / "traces")

    assert result.pass_rate == 0.0
    assert result.failures[0]["result"]["error"] == "FileNotFoundError"
    assert result.trace_path and Path(result.trace_path).exists()


def test_unverifiable_tasks_do_not_default_pass(tmp_path: Path):
    harness = Harness(name="custom", kind="coding", goal="reject unverifiable")
    harness.add_tasks(TaskSet(name="bad", tasks=[Task(id="bad", description="No reward criteria", kind="coding")]))

    result = harness.evaluate(tmp_path, tmp_path / "traces")

    assert result.pass_rate == 0.0
    assert result.failures[0]["result"]["error"] == "unverifiable_task"


def test_deploy_blocks_when_evaluation_fails(tmp_path: Path):
    project = Project.init(tmp_path / "blocked-deploy")
    project.harness("coding").add_tasks(TaskSet(name="bad", tasks=[Task(id="bad", description="No reward criteria", kind="coding")]))

    deployment = project.deploy()

    assert deployment["status"] == "blocked"
    assert deployment["reason"] == "evaluation_failed"
