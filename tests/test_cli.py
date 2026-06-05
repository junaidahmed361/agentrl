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
