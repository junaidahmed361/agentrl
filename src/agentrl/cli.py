from __future__ import annotations

import argparse
import json
from pathlib import Path

from . import __version__
from .project import Project


def _project(path: str | None = None) -> Project:
    return Project(path or Path.cwd())


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

    project = _project()
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
