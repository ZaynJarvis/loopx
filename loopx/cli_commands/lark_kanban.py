from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Callable

from ..lark_kanban import (
    DEFAULT_AGENT_ID,
    DEFAULT_CLI_BIN,
    DEFAULT_STATUS_QUEUE_VIEW,
    DEFAULT_TABLE_NAME,
    LarkKanbanConfig,
    build_create_board_plan,
    create_lark_kanban_board,
    lark_kanban_heartbeat,
    lark_kanban_schema_payload,
    render_lark_kanban_markdown,
    sample_lark_kanban_task,
    seed_lark_kanban_task,
)


PrintPayload = Callable[
    [dict[str, object], str, Callable[[dict[str, object]], str]],
    None,
]
OutputFormat = Callable[[argparse.Namespace], str]


def register_lark_kanban_commands(
    subparsers: argparse._SubParsersAction,
    add_subcommand_format: Callable[[argparse.ArgumentParser], None],
) -> None:
    parser = subparsers.add_parser(
        "lark-kanban",
        help="Use a Feishu/Lark Base Kanban board as a LoopX control-plane adapter.",
    )
    sub = parser.add_subparsers(dest="lark_kanban_command", required=True)

    schema = sub.add_parser("schema", help="Print the task-board schema and LoopX mapping.")
    add_subcommand_format(schema)
    schema.add_argument("--table-name", default=DEFAULT_TABLE_NAME)

    plan = sub.add_parser("plan-create", help="Print lark-cli commands for creating the board.")
    add_subcommand_format(plan)
    _add_create_args(plan)

    create = sub.add_parser("create-board", help="Create the Lark Base board. Dry-run unless --execute.")
    add_subcommand_format(create)
    _add_create_args(create)
    create.add_argument("--execute", action="store_true", help="Actually run lark-cli commands.")

    seed = sub.add_parser("seed-task", help="Create one sample task row. Dry-run unless --execute.")
    add_subcommand_format(seed)
    _add_lark_target_args(seed)
    seed.add_argument("--goal-id", default="loopx-lark-kanban-poc")
    seed.add_argument("--worker-command", default="")
    seed.add_argument("--workdir", default="")
    seed.add_argument("--execute", action="store_true", help="Actually upsert the sample record.")

    heartbeat = sub.add_parser(
        "heartbeat",
        help="Poll one Kanban task, claim it, optionally run a worker command, and write evidence.",
    )
    add_subcommand_format(heartbeat)
    _add_lark_target_args(heartbeat)
    heartbeat.add_argument("--agent-id", default=DEFAULT_AGENT_ID)
    heartbeat.add_argument(
        "--fixture",
        help="Optional record-list JSON fixture. When set, no list command is run.",
    )
    heartbeat.add_argument(
        "--worker-command",
        help="Override the row's Worker Command for this heartbeat.",
    )
    heartbeat.add_argument(
        "--allow-command-prefix",
        action="append",
        default=[],
        help="Allowed prefix for --execute-worker, e.g. python3 or codex exec. Repeatable.",
    )
    heartbeat.add_argument(
        "--execute-lark",
        action="store_true",
        help="Actually call lark-cli for record list/claim/writeback.",
    )
    heartbeat.add_argument(
        "--execute-worker",
        action="store_true",
        help="Actually run the worker command after claim. Requires --allow-command-prefix.",
    )
    heartbeat.add_argument(
        "--complete-on-success",
        action="store_true",
        help="Set Status=Done after successful worker execution. Default is Review.",
    )
    heartbeat.add_argument(
        "--worker-timeout-seconds",
        type=float,
        default=600.0,
        help="Timeout for the worker command.",
    )


def _add_create_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--base-name", default="LoopX Lark Kanban Control Plane POC")
    parser.add_argument("--table-name", default=DEFAULT_TABLE_NAME)
    parser.add_argument("--base-token", help="Use an existing Base token instead of creating a new Base.")
    parser.add_argument("--user-open-id", help="Grant this user full_access to a newly created/existing Base.")
    parser.add_argument("--cli-bin", default=DEFAULT_CLI_BIN)
    parser.add_argument("--as", dest="identity", default="bot", choices=["bot", "user", "auto"])


def _add_lark_target_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--base-token", required=True)
    parser.add_argument("--table-id", required=True)
    parser.add_argument("--view-id", default=DEFAULT_STATUS_QUEUE_VIEW)
    parser.add_argument("--cli-bin", default=DEFAULT_CLI_BIN)
    parser.add_argument("--as", dest="identity", default="bot", choices=["bot", "user", "auto"])


def _target_config(args: argparse.Namespace) -> LarkKanbanConfig:
    return LarkKanbanConfig(
        **{"base_" + "token": args.base_token},
        table_id=args.table_id,
        view_id=args.view_id,
        cli_bin=args.cli_bin,
        identity=args.identity,
    )


def handle_lark_kanban_command(
    args: argparse.Namespace,
    *,
    print_payload: PrintPayload,
    output_format: OutputFormat,
) -> int | None:
    if args.command != "lark-kanban":
        return None
    fmt = output_format(args)
    try:
        if args.lark_kanban_command == "schema":
            payload = lark_kanban_schema_payload(table_name=args.table_name)
        elif args.lark_kanban_command == "plan-create":
            commands = build_create_board_plan(
                base_name=args.base_name,
                table_name=args.table_name,
                cli_bin=args.cli_bin,
                identity=args.identity,
                **{"base_" + "token": args.base_token},
                user_open_id=args.user_open_id,
            )
            payload = {
                "ok": True,
                "schema_version": "loopx_lark_kanban_create_plan_v0",
                "execute": False,
                "commands": [
                    {
                        "command": " ".join(_shell_quote(part) for part in command),
                        "executed": False,
                        "ok": True,
                    }
                    for command in commands
                ],
            }
        elif args.lark_kanban_command == "create-board":
            payload = create_lark_kanban_board(
                base_name=args.base_name,
                table_name=args.table_name,
                cli_bin=args.cli_bin,
                identity=args.identity,
                **{"base_" + "token": args.base_token},
                user_open_id=args.user_open_id,
                execute=bool(args.execute),
            )
            payload["execute"] = bool(args.execute)
        elif args.lark_kanban_command == "seed-task":
            task = sample_lark_kanban_task(
                goal_id=args.goal_id,
                worker_command=args.worker_command,
                workdir=args.workdir,
            )
            payload = seed_lark_kanban_task(
                _target_config(args),
                task=task,
                execute=bool(args.execute),
            )
            payload["execute"] = bool(args.execute)
        elif args.lark_kanban_command == "heartbeat":
            fixture = _load_fixture(args.fixture) if args.fixture else None
            payload = lark_kanban_heartbeat(
                _target_config(args),
                agent_id=args.agent_id,
                fixture=fixture,
                worker_command=args.worker_command,
                execute_lark=bool(args.execute_lark),
                execute_worker=bool(args.execute_worker),
                complete_on_success=bool(args.complete_on_success),
                allowed_command_prefixes=args.allow_command_prefix,
                worker_timeout_seconds=args.worker_timeout_seconds,
            )
        else:
            raise ValueError(f"unknown lark-kanban command: {args.lark_kanban_command}")
    except Exception as exc:
        payload = {
            "ok": False,
            "schema_version": "loopx_lark_kanban_error_v0",
            "error": str(exc),
        }
    print_payload(payload, fmt, render_lark_kanban_markdown)
    return 0 if payload.get("ok") else 1


def _load_fixture(path: str) -> dict[str, object]:
    raw = Path(path).expanduser().read_text(encoding="utf-8")
    payload = json.loads(raw)
    if not isinstance(payload, dict):
        raise ValueError("fixture must be a JSON object")
    return payload


def _shell_quote(value: str) -> str:
    import shlex

    return shlex.quote(value)
