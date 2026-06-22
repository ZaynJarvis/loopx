#!/usr/bin/env python3
"""Smoke-test the Lark Kanban control-plane adapter."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from loopx.lark_kanban import (  # noqa: E402
    CLAIM_UNCLAIMED,
    STATUS_REVIEW,
    STATUS_TODO,
    LarkKanbanConfig,
    build_create_board_plan,
    lark_kanban_heartbeat,
    lark_kanban_schema_payload,
)


def fixture_payload() -> dict[str, object]:
    fields = [
        "Task",
        "Status",
        "Claim",
        "Claimed By",
        "Priority",
        "Task Class",
        "Action Kind",
        "LoopX Goal ID",
        "LoopX Todo ID",
        "Scope",
        "User Gate",
        "Handoff",
        "Evidence",
        "Run History",
        "Worker Command",
        "Workdir",
        "Last Error",
        "Last Result Code",
        "Last Heartbeat",
    ]
    row = [
        "POC: produce compact public evidence",
        [STATUS_TODO],
        [CLAIM_UNCLAIMED],
        None,
        ["P1"],
        ["advancement_task"],
        "analyze",
        "loopx-lark-kanban-poc",
        "todo_public_poc",
        "public fixture only",
        None,
        "Worker should produce compact evidence and handoff.",
        None,
        "",
        "python3 -c 'print(\"evidence: public fixture worker completed\")'",
        str(REPO_ROOT),
        None,
        None,
        None,
    ]
    return {
        "ok": True,
        "data": {
            "fields": fields,
            "data": [row],
            "record_id_list": ["recFixture001"],
            "has_more": False,
        },
    }


def fake_runner(args: list[str], cwd: Path | None, timeout: float | None) -> dict[str, object]:
    assert args[0] == "python3", args
    assert cwd == REPO_ROOT, cwd
    assert timeout == 600.0, timeout
    return {
        "returncode": 0,
        "stdout": "evidence: public fixture worker completed\n",
        "stderr": "",
        "timed_out": False,
    }


def run_cli(*extra_args: str) -> dict[str, object]:
    result = subprocess.run(
        [sys.executable, "-m", "loopx.cli", "--format", "json", *extra_args],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(result.stdout)


def main() -> int:
    schema = lark_kanban_schema_payload()
    assert schema["ok"] is True, schema
    assert schema["schema_version"] == "loopx_lark_kanban_control_plane_v0", schema
    field_names = [field["name"] for field in schema["fields"]]
    for expected in ["Task", "Status", "Claim", "Handoff", "Evidence", "Run History", "Worker Command"]:
        assert expected in field_names, field_names
    assert schema["heartbeat_model"]["fallback"].startswith("agent heartbeat"), schema

    plan = build_create_board_plan(
        base_name="LoopX Lark Kanban Control Plane POC",
        table_name="LoopX Control Plane",
        **{"base_" + "token": "base_public_fixture"},
        user_open_id="ou_public_fixture",
    )
    joined = [" ".join(command) for command in plan]
    assert any("+table-create" in command for command in joined), joined
    assert any("permission.members" in command for command in joined), joined
    assert any("+view-set-group" in command and "Kanban" in command for command in joined), joined

    heartbeat = lark_kanban_heartbeat(
        LarkKanbanConfig(
            **{"base_" + "token": "base_public_fixture"},
            table_id="tbl_public_fixture",
            view_id="Worker Queue",
        ),
        fixture=fixture_payload(),
        agent_id="codex-kanban-worker",
        execute_lark=False,
        execute_worker=True,
        allowed_command_prefixes=["python3"],
        runner=fake_runner,
    )
    assert heartbeat["ok"] is True, heartbeat
    assert heartbeat["decision"] == "task_processed", heartbeat
    assert heartbeat["selected_record_id"] == "recFixture001", heartbeat
    assert heartbeat["worker"]["executed"] is True, heartbeat
    assert heartbeat["final_status"] == STATUS_REVIEW, heartbeat
    assert "evidence: public fixture worker completed" in heartbeat["writeback"]["Evidence"], heartbeat
    assert heartbeat["writeback"]["Claimed By"] == "codex-kanban-worker", heartbeat
    assert len(heartbeat["commands"]) == 2, heartbeat
    assert all(command["executed"] is False for command in heartbeat["commands"]), heartbeat

    with tempfile.TemporaryDirectory(prefix="loopx-lark-kanban-smoke-") as tmp:
        fixture = Path(tmp) / "record-list.json"
        fixture.write_text(json.dumps(fixture_payload()), encoding="utf-8")
        cli = run_cli(
            "lark-kanban",
            "heartbeat",
            "--base-token",
            "base_public_fixture",
            "--table-id",
            "tbl_public_fixture",
            "--fixture",
            str(fixture),
            "--agent-id",
            "codex-kanban-worker",
        )
    assert cli["ok"] is True, cli
    assert cli["decision"] == "task_processed", cli
    assert cli["worker"]["executed"] is False, cli
    assert cli["final_status"] == "Claimed", cli

    print("lark-kanban-control-plane-smoke: ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
