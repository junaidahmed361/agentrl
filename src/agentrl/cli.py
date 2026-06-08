from __future__ import annotations

import argparse
import json
from pathlib import Path

from . import __version__
from .project import Project


def _project(path: str | None = None) -> Project:
    return Project(path or Path.cwd())


def _quick_launch_local_agent_os(path: str | Path, goal: str | None = None) -> dict[str, object]:
    from .local_agent_os import LocalAgentOS

    project_path = Path(path)
    if (project_path / "agentrl.yaml").exists():
        project = Project(project_path)
        initialized = False
    else:
        project = Project.init(project_path, template="local-agent-os")
        initialized = True

    compiled = project.compile()
    local_os = LocalAgentOS(project)
    goal_result = local_os.run_goal(goal or "Inspect the local AgentRL harness stack")
    evaluation = [r.to_dict() for r in project.evaluate()]
    evolution = project.auto_harness(mode="adaptive")
    deployment = project.deploy(strategy="local")

    return {
        "status": "ready",
        "initialized": initialized,
        "path": str(project.root),
        "template": "local-agent-os",
        "agents": [agent["name"] for agent in local_os.overview()["agents"]],
        "harnesses": list(project.harnesses),
        "compiled": compiled,
        "goal_result": goal_result,
        "evaluation": evaluation,
        "auto_harness": evolution,
        "deployment": deployment,
        "next_commands": [
            f"cd {project.root}",
            "agentrl agent-os",
            "agentrl agent-os --memory",
            "agentrl evaluate",
            "agentrl version list",
        ],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="agentrl", description="Local-first Harness Operating System for agents")
    parser.add_argument("--version", action="version", version=f"agentrl {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    p_init = sub.add_parser("init")
    p_init.add_argument("path")
    p_init.add_argument("--template", default="default")

    sub.add_parser("compile")

    p_train = sub.add_parser("train")
    p_train.add_argument("--strategy", default="verification", choices=["verification", "preference", "optimization", "simulation"])

    sub.add_parser("evaluate")

    p_evolve = sub.add_parser("evolve")
    p_evolve.add_argument("--targets", default="prompts,skills,memory")

    p_auto = sub.add_parser("auto-harness")
    p_auto.add_argument("--mode", default="static", choices=["static", "adaptive"])

    p_goal = sub.add_parser("run-goal")
    p_goal.add_argument("goal")

    p_create_agent = sub.add_parser("create-agent-harness", help="Create a targeted agent harness with inferred components")
    p_create_agent.add_argument("--agent", required=True, help="Targeted agent name, e.g. 'Market Researcher'")
    p_create_agent.add_argument("--role", required=True, help="Targeted role, e.g. market_researcher")
    p_create_agent.add_argument("--objective", required=True, help="Agent objective")
    p_create_agent.add_argument("--components", help="Comma-separated component override. Defaults are inferred from role/objective.")

    p_agent_os = sub.add_parser("agent-os", help="Launch a Hermes-style local agent harness shell")
    p_agent_os.add_argument("--goal", help="Run one goal non-interactively and exit")
    p_agent_os.add_argument("--overview", action="store_true", help="Print the local agent OS topology and exit")
    p_agent_os.add_argument("--memory", action="store_true", help="Print recent local agent OS memory and exit")
    p_agent_os.add_argument("--project", help="Project path to run instead of the current directory")

    p_demo = sub.add_parser("demo", help="Quick-launch bundled demos with minimal setup")
    demo_sub = p_demo.add_subparsers(dest="demo_command", required=True)
    p_demo_agent_os = demo_sub.add_parser("local-agent-os", help="Initialize, evaluate, evolve, deploy, and run the local Agent OS demo")
    p_demo_agent_os.add_argument("--path", default="local-agent-os", help="Demo project path to create or reuse")
    p_demo_agent_os.add_argument("--goal", help="Goal to route through the local Agent OS during launch")
    p_demo_agent_os.add_argument("--shell", action="store_true", help="Open the interactive agent-os shell after bootstrap")

    p_deploy = sub.add_parser("deploy")
    p_deploy.add_argument("--strategy", default="local")

    p_version = sub.add_parser("version")
    vsub = p_version.add_subparsers(dest="version_command", required=True)
    vlist = vsub.add_parser("list")
    vlist.add_argument("--entity")
    vdiff = vsub.add_parser("diff")
    vdiff.add_argument("left")
    vdiff.add_argument("right")
    vrollback = vsub.add_parser("rollback")
    vrollback.add_argument("version_id")
    vrollback.add_argument("--target")

    args = parser.parse_args(argv)
    if args.command == "init":
        project = Project.init(args.path, template=args.template)
        print(json.dumps({"status": "initialized", "path": str(project.root)}, indent=2))
        return 0
    if args.command == "demo":
        if args.demo_command == "local-agent-os":
            summary = _quick_launch_local_agent_os(args.path, goal=args.goal)
            print(json.dumps(summary, indent=2))
            if args.shell:
                from .local_agent_os import run_repl

                return run_repl(Project(str(summary["path"])))
        return 0

    project = _project(getattr(args, "project", None))
    if args.command == "compile":
        print(json.dumps(project.compile(), indent=2))
    elif args.command == "train":
        print(json.dumps(project.train(strategy=args.strategy), indent=2))
    elif args.command == "evaluate":
        print(json.dumps([r.to_dict() for r in project.evaluate()], indent=2))
    elif args.command == "evolve":
        print(json.dumps(project.evolve(targets=[t.strip() for t in args.targets.split(",") if t.strip()]), indent=2))
    elif args.command == "auto-harness":
        print(json.dumps(project.auto_harness(mode=args.mode), indent=2))
    elif args.command == "run-goal":
        print(json.dumps(project.run_goal(args.goal), indent=2))
    elif args.command == "create-agent-harness":
        components = [item.strip() for item in args.components.split(",") if item.strip()] if args.components else None
        print(json.dumps(project.create_agent_harness(args.agent, args.role, args.objective, components=components), indent=2))
    elif args.command == "agent-os":
        from .local_agent_os import LocalAgentOS, run_repl

        local_os = LocalAgentOS(project)
        if args.overview:
            print(json.dumps(local_os.overview(), indent=2))
        elif args.memory:
            print(json.dumps(local_os.memory(), indent=2))
        elif args.goal:
            print(json.dumps(local_os.run_goal(args.goal), indent=2))
        else:
            return run_repl(project)
    elif args.command == "deploy":
        print(json.dumps(project.deploy(strategy=args.strategy), indent=2))
    elif args.command == "version":
        if args.version_command == "list":
            print(json.dumps(project.registry.list(entity=args.entity), indent=2))
        elif args.version_command == "diff":
            print(project.registry.diff(args.left, args.right))
        elif args.version_command == "rollback":
            target = Path(args.target) if args.target else None
            print(project.registry.rollback(args.version_id, target=target))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
