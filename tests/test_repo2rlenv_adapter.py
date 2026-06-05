import json
from pathlib import Path

from agentrl import Project
from agentrl.adapters import Repo2RLEnvAdapter


def test_repo2rlenv_adapter_maps_harbor_task(tmp_path: Path):
    payload = {
        "tasks": [
            {
                "id": "task-1",
                "prompt": "Fix failing test",
                "verification_command": "python3 -c 'print(\"ok\")'",
                "sandbox": {"image": "python:3.12", "path": str(tmp_path)},
                "metadata": {"harbor": {"split": "train"}},
                "timeout": 30,
            }
        ]
    }
    source_path = tmp_path / "repo2rlenv.json"
    source_path.write_text(json.dumps(payload), encoding="utf-8")

    source = Repo2RLEnvAdapter.from_repo("owner/repo", pipeline="pr_runtime", output_path=str(source_path))
    taskset = source.to_taskset()

    assert taskset.provenance["adapter"] == "Repo2RLEnvAdapter"
    assert taskset.tasks[0].kind == "coding"
    assert taskset.tasks[0].reward == "pytest"
    assert taskset.tasks[0].expected["command"].startswith("python")
    assert taskset.tasks[0].metadata["sandbox"]["image"] == "python:3.12"

    project = Project.init(tmp_path / "coding-agent")
    project.harness("coding").add_tasks(taskset)
    project.compile()
    result = [r for r in project.evaluate() if r.harness == "coding"][0]
    assert result.pass_rate == 1.0
    assert result.trace_path


def test_repo2rlenv_adapter_handles_invalid_output_without_crashing(tmp_path: Path):
    source_path = tmp_path / "repo2rlenv.json"
    source_path.write_text(json.dumps({"tasks": "not-a-list"}), encoding="utf-8")

    taskset = Repo2RLEnvAdapter.from_repo("owner/repo", output_path=str(source_path)).to_taskset()

    assert len(taskset.tasks) == 0
    assert taskset.provenance["errors"][0]["reason"] == "repo2rlenv_invalid_tasks"
    assert taskset.provenance["errors"][0]["payload_type"] == "str"
