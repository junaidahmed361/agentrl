import json
import subprocess
import sys
from pathlib import Path


def run_cli(cwd: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run([sys.executable, "-m", "agentrl.cli", *args], cwd=cwd, text=True, capture_output=True, check=True)


def test_cli_acceptance_flow(tmp_path: Path):
    run_cli(tmp_path, "init", "my-project")
    project_dir = tmp_path / "my-project"
    assert (project_dir / "agentrl.yaml").exists()

    compiled = json.loads(run_cli(project_dir, "compile").stdout)
    assert len(compiled) == 3

    train = json.loads(run_cli(project_dir, "train", "--strategy", "verification").stdout)
    assert train["promoted"] is True

    evaluated = json.loads(run_cli(project_dir, "evaluate").stdout)
    assert {r["harness"] for r in evaluated} == {"coding", "rag", "tool_use"}

    deployment = json.loads(run_cli(project_dir, "deploy").stdout)
    assert deployment["status"] == "deployed"

    versions = json.loads(run_cli(project_dir, "version", "list").stdout)
    assert any(v["entity"].startswith("harness:") for v in versions)


def test_local_agent_os_template_and_goal(tmp_path: Path):
    run_cli(tmp_path, "init", "local-agent-os", "--template", "local-agent-os")
    project_dir = tmp_path / "local-agent-os"

    config = (project_dir / "agentrl.yaml").read_text()
    assert "router_agent" in config
    assert (project_dir / "LOCAL_AGENT_OS.md").exists()

    overview = json.loads(run_cli(project_dir, "agent-os", "--overview").stdout)
    assert overview["system"] == "local-agent-os"
    assert "router_agent" in {agent["name"] for agent in overview["agents"]}

    result = json.loads(run_cli(project_dir, "agent-os", "--goal", "Fix a failing pytest in this repo").stdout)
    assert result["selected_harness"] == "coding"
    assert result["evaluation"]["pass_rate"] == 1.0
    assert Path(result["evaluation"]["trace_path"]).exists()
    assert (project_dir / ".agentrl" / "agent_os" / "memory.jsonl").exists()

    memory = json.loads(run_cli(tmp_path, "agent-os", "--project", str(project_dir), "--memory").stdout)
    assert memory[-1]["harness"] == "coding"


def test_local_agent_os_quick_launch_demo(tmp_path: Path):
    project_dir = tmp_path / "quick-local-agent-os"
    summary = json.loads(run_cli(
        tmp_path,
        "demo",
        "local-agent-os",
        "--path",
        str(project_dir),
        "--goal",
        "Answer from docs with citations",
    ).stdout)

    assert summary["status"] == "ready"
    assert summary["initialized"] is True
    assert summary["template"] == "local-agent-os"
    assert summary["goal_result"]["selected_harness"] == "rag"
    assert summary["deployment"]["status"] == "deployed"
    assert (project_dir / "agentrl.yaml").exists()
    assert (project_dir / ".agentrl" / "deployments" / "local" / "deployment.json").exists()
