import json
from pathlib import Path

from agentrl import Project
from agentrl.adapters import OpenHarnessAdapter


def test_openharness_adapter_imports_runtime_traces(tmp_path: Path):
    trace_path = tmp_path / "openharness-traces.jsonl"
    trace_path.write_text(
        "\n".join(
            [
                json.dumps({"trace_id": "t1", "goal": "Fix failing test", "harness": "coding", "success": True}),
                json.dumps({"trace_id": "t2", "goal": "Answer from docs", "harness": "rag", "evaluation": {"success": True}}),
            ]
        ),
        encoding="utf-8",
    )

    adapter = OpenHarnessAdapter.from_trace_file(trace_path)
    taskset = adapter.to_taskset()

    assert taskset.provenance["adapter"] == "OpenHarnessAdapter"
    assert "OpenHarness provides runtime trajectories" in taskset.provenance["boundary"]
    assert [task.id for task in taskset.tasks] == ["t1", "t2"]
    assert taskset.tasks[0].kind == "coding"
    assert taskset.tasks[0].expected["success"] is True
    assert "agent_loop" in taskset.tasks[0].metadata["runtime"]["does_not_implement"]


def test_project_attach_openharness_runtime_registers_boundary(tmp_path: Path):
    project = Project.init(tmp_path / "agent-system")
    runtime = OpenHarnessAdapter.from_endpoint("http://localhost:8000")

    result = project.attach_runtime(runtime)

    assert result["status"] == "attached"
    assert result["runtime"]["adapter"] == "OpenHarnessAdapter"
    assert "executes goals" in result["runtime"]["boundary"]
    record_path = Path(result["path"])
    assert record_path.exists()
    versions = project.registry.list(entity="runtime:openharness")
    assert versions
