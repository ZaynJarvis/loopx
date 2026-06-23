from __future__ import annotations

import json
import shlex
import subprocess
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Optional


LARK_KANBAN_SCHEMA_VERSION = "loopx_lark_kanban_control_plane_v0"
LARK_KANBAN_HEARTBEAT_VERSION = "loopx_lark_kanban_heartbeat_v0"
DEFAULT_TABLE_NAME = "LoopX Control Plane"
DEFAULT_AGENT_ID = "codex-kanban-worker"
DEFAULT_CLI_BIN = "lark-cli"
DEFAULT_STATUS_QUEUE_VIEW = "Worker Queue"
OPERATOR_CARD_FIELDS = ["Task", "Claim", "Priority", "User Gate", "Evidence", "Status"]

STATUS_TODO = "Todo"
STATUS_CLAIMED = "Claimed"
STATUS_RUNNING = "Running"
STATUS_USER_GATE = "User Gate"
STATUS_BLOCKED = "Blocked"
STATUS_REVIEW = "Review"
STATUS_DONE = "Done"
CLAIM_UNCLAIMED = "Unclaimed"
CLAIM_HUMAN = "Human"
CLAIM_AGENT = "Agent"

TEXT_LIMIT = 4000
OUTPUT_LIMIT = 1800


CommandRunner = Callable[[list[str], Optional[Path], Optional[float]], dict[str, Any]]


def _select_options(names: list[str]) -> list[dict[str, str]]:
    hues = {
        STATUS_TODO: "Gray",
        STATUS_CLAIMED: "Blue",
        STATUS_RUNNING: "Orange",
        STATUS_USER_GATE: "Purple",
        STATUS_BLOCKED: "Red",
        STATUS_REVIEW: "Wathet",
        STATUS_DONE: "Green",
        CLAIM_UNCLAIMED: "Gray",
        CLAIM_HUMAN: "Green",
        CLAIM_AGENT: "Blue",
        "P0": "Red",
        "P1": "Orange",
        "P2": "Blue",
        "P3": "Gray",
        "advancement_task": "Blue",
        "continuous_monitor": "Wathet",
        "user_gate": "Purple",
        "blocker": "Red",
    }
    return [
        {
            "name": name,
            "hue": hues.get(name, "Blue"),
            "lightness": "Light",
        }
        for name in names
    ]


def lark_kanban_field_definitions() -> list[dict[str, Any]]:
    return [
        {"name": "Task", "type": "text", "style": {"type": "plain"}},
        {
            "name": "Status",
            "type": "select",
            "multiple": False,
            "options": _select_options(
                [
                    STATUS_TODO,
                    STATUS_CLAIMED,
                    STATUS_RUNNING,
                    STATUS_USER_GATE,
                    STATUS_BLOCKED,
                    STATUS_REVIEW,
                    STATUS_DONE,
                ]
            ),
        },
        {
            "name": "Claim",
            "type": "select",
            "multiple": False,
            "options": _select_options([CLAIM_UNCLAIMED, CLAIM_HUMAN, CLAIM_AGENT]),
        },
        {"name": "Claimed By", "type": "text", "style": {"type": "plain"}},
        {
            "name": "Priority",
            "type": "select",
            "multiple": False,
            "options": _select_options(["P0", "P1", "P2", "P3"]),
        },
        {
            "name": "Task Class",
            "type": "select",
            "multiple": False,
            "options": _select_options(
                ["advancement_task", "continuous_monitor", "user_gate", "blocker"]
            ),
        },
        {"name": "Action Kind", "type": "text", "style": {"type": "plain"}},
        {"name": "LoopX Goal ID", "type": "text", "style": {"type": "plain"}},
        {"name": "LoopX Todo ID", "type": "text", "style": {"type": "plain"}},
        {"name": "Scope", "type": "text", "style": {"type": "plain"}},
        {"name": "User Gate", "type": "text", "style": {"type": "plain"}},
        {"name": "Handoff", "type": "text", "style": {"type": "plain"}},
        {"name": "Evidence", "type": "text", "style": {"type": "plain"}},
        {"name": "Run History", "type": "text", "style": {"type": "plain"}},
        {"name": "Worker Command", "type": "text", "style": {"type": "plain"}},
        {"name": "Workdir", "type": "text", "style": {"type": "plain"}},
        {"name": "Last Error", "type": "text", "style": {"type": "plain"}},
        {
            "name": "Last Result Code",
            "type": "number",
            "style": {
                "type": "plain",
                "precision": 0,
                "percentage": False,
                "thousands_separator": False,
            },
        },
        {
            "name": "Last Heartbeat",
            "type": "datetime",
            "style": {"format": "yyyy-MM-dd HH:mm"},
        },
        {
            "name": "Created At",
            "type": "created_at",
            "style": {"format": "yyyy-MM-dd HH:mm"},
        },
        {
            "name": "Updated At",
            "type": "updated_at",
            "style": {"format": "yyyy-MM-dd HH:mm"},
        },
    ]


def lark_kanban_views() -> list[dict[str, str]]:
    return [
        {"name": "All Tasks", "type": "grid"},
        {"name": DEFAULT_STATUS_QUEUE_VIEW, "type": "grid"},
        {"name": "User Gates", "type": "grid"},
        {"name": "Kanban", "type": "kanban"},
    ]


def lark_kanban_schema_payload(*, table_name: str = DEFAULT_TABLE_NAME) -> dict[str, Any]:
    return {
        "ok": True,
        "schema_version": LARK_KANBAN_SCHEMA_VERSION,
        "table_name": table_name,
        "source_of_truth": "lark_base_bitable",
        "loopx_mapping": {
            "todo": "Task row with Status=Todo and Claim=Unclaimed",
            "claim": "Claim single-selection plus Claimed By text",
            "user_gate": "Status=User Gate and concrete question in User Gate",
            "handoff": "Handoff text field",
            "evidence": "Evidence text field",
            "run_history": "Run History append-style compact text field",
            "quota": "omitted in v0 prototype; assume no quota limit",
            "scope": "Scope text field; advisory in v0 prototype",
        },
        "fields": lark_kanban_field_definitions(),
        "views": lark_kanban_views(),
        "operator_view": {
            "kanban_card_fields": OPERATOR_CARD_FIELDS,
            "reason": (
                "Keep the human-facing Kanban card small; retain the full task "
                "context in the record detail and All Tasks grid."
            ),
            "configuration_note": (
                "Lark's current shortcut CLI exposes Kanban cover settings, but "
                "not the card field visibility list. Configure card fields in "
                "the Lark UI until that API is available in lark-cli."
            ),
        },
        "heartbeat_model": {
            "direct_lark_trigger": False,
            "trigger_reason": (
                "Feishu Base workflow cannot reach this local edge worker without "
                "a reachable callback or daemon bridge in the current environment."
            ),
            "fallback": "agent heartbeat polls Worker Queue, soft-claims one task, runs worker command, writes evidence",
        },
    }


def sample_lark_kanban_task(
    *,
    goal_id: str = "loopx-lark-kanban-poc",
    worker_command: str = "",
    workdir: str = "",
) -> dict[str, Any]:
    return {
        "Task": "POC: triage a public issue and produce a reviewable handoff",
        "Status": STATUS_TODO,
        "Claim": CLAIM_UNCLAIMED,
        "Claimed By": "",
        "Priority": "P1",
        "Task Class": "advancement_task",
        "Action Kind": "analyze",
        "LoopX Goal ID": goal_id,
        "LoopX Todo ID": "todo_lark_kanban_poc",
        "Scope": "public repo read/write prototype; no credentials, no private logs",
        "User Gate": "",
        "Handoff": "Start from the Worker Command. Return compact evidence and next review step.",
        "Evidence": "",
        "Run History": "",
        "Worker Command": worker_command,
        "Workdir": workdir,
        "Last Error": "",
        "Last Result Code": None,
    }


def lark_kanban_operator_card_fields() -> list[str]:
    return list(OPERATOR_CARD_FIELDS)


def lark_kanban_ux_task(
    *,
    goal_id: str = "loopx-lark-kanban-ux",
    worker_command: str = "",
    workdir: str = "",
) -> dict[str, Any]:
    return {
        "Task": "Optimize LoopX Kanban control-plane UX",
        "Status": STATUS_USER_GATE,
        "Claim": CLAIM_HUMAN,
        "Claimed By": "",
        "Priority": "P1",
        "Task Class": "user_gate",
        "Action Kind": "decide",
        "LoopX Goal ID": goal_id,
        "LoopX Todo ID": "todo_lark_kanban_ux",
        "Scope": (
            "Use LoopX itself to reduce operator attention cost while preserving "
            "complete structured context in Lark Base."
        ),
        "User Gate": (
            "Approve the simplified Kanban card profile and heartbeat/subagent "
            "worker model for this prototype."
        ),
        "Handoff": (
            "After approval, move this row to Todo/Unclaimed and let an agent "
            "claim it, produce evidence, and leave the row in Review."
        ),
        "Evidence": "Awaiting human gate pass.",
        "Run History": "",
        "Worker Command": worker_command,
        "Workdir": workdir,
        "Last Error": "",
        "Last Result Code": None,
    }


def lark_kanban_feasibility_cases(
    *,
    goal_id: str = "loopx-lark-kanban-feasibility",
    workdir: str = "",
) -> list[dict[str, Any]]:
    common = {
        "Status": STATUS_REVIEW,
        "Claim": CLAIM_AGENT,
        "Claimed By": DEFAULT_AGENT_ID,
        "Priority": "P1",
        "LoopX Goal ID": goal_id,
        "Workdir": workdir,
        "Last Error": "",
        "Last Result Code": 0,
    }
    return [
        {
            **common,
            "Task": "Case: notes.zaynjarvis.com LoopX architecture decision",
            "Task Class": "advancement_task",
            "Action Kind": "publish_decision_note",
            "LoopX Todo ID": "todo_case_notes_arch_decision",
            "Scope": (
                "Publish a public-safe decision note describing LoopX axioms, "
                "control-plane shape, and Lark Kanban adapter tradeoffs."
            ),
            "User Gate": "Human approves final wording before publishing.",
            "Handoff": (
                "Draft the architecture/decision note, keep source-of-truth "
                "fields in the board, and publish only a concise public version."
            ),
            "Evidence": (
                "Feasible: the board row captures task, gate, scope, handoff, "
                "and public evidence pointer for a notes.zaynjarvis.com publish lane."
            ),
            "Run History": "case seeded: public decision note lane is representable",
            "Worker Command": "",
        },
        {
            **common,
            "Task": "Case: P1/P2 human gate timeout with default fallback",
            "Task Class": "user_gate",
            "Action Kind": "decide_with_timeout",
            "LoopX Todo ID": "todo_case_gate_timeout_fallback",
            "Scope": (
                "Model a human decision that should not block the loop forever; "
                "P1/P2 gates can fall back to a default after timeout."
            ),
            "User Gate": (
                "Choose explicit decision, or allow the default fallback to fire "
                "after the configured timeout."
            ),
            "Handoff": (
                "Record the gate question in User Gate; record fallback policy "
                "in Handoff; apply only via loop state transition."
            ),
            "Evidence": (
                "Feasible: User Gate plus Handoff can separate human choice from "
                "the structured state transition that actually changes memory."
            ),
            "Run History": "case seeded: gate timeout/fallback lane is representable",
            "Worker Command": "",
        },
        {
            **common,
            "Task": "Case: cross-session compact memory through OV",
            "Task Class": "continuous_monitor",
            "Action Kind": "memory_handoff",
            "LoopX Todo ID": "todo_case_ov_compact_memory",
            "Scope": (
                "Carry loop context across sessions through an external compact "
                "memory surface instead of relying on raw transcript recall."
            ),
            "User Gate": "Confirm which facts are durable enough to enter compact memory.",
            "Handoff": (
                "Store concise decisions and state deltas externally; keep raw "
                "session details out of the Kanban card."
            ),
            "Evidence": (
                "Feasible: the Kanban row can point to compact memory writes while "
                "remaining a simple operator control surface."
            ),
            "Run History": "case seeded: OV compact-memory lane is representable",
            "Worker Command": "",
        },
        {
            **common,
            "Task": "Case: output quality vs token and attention cost eval",
            "Task Class": "advancement_task",
            "Action Kind": "define_eval",
            "LoopX Todo ID": "todo_case_quality_cost_eval",
            "Scope": (
                "Define a loop benchmark that scores delivered output against "
                "token spend and human attention cost."
            ),
            "User Gate": "Approve the cost dimensions before using the eval as a gate.",
            "Handoff": (
                "Use Evidence for results, Run History for compact attempts, and "
                "Priority to decide whether a rerun is worth more attention."
            ),
            "Evidence": (
                "Feasible: Base fields support an eval lane that keeps quality, "
                "token cost, and attention cost visible without bloating the card."
            ),
            "Run History": "case seeded: quality/cost eval lane is representable",
            "Worker Command": "",
        },
    ]


def default_subprocess_runner(
    args: list[str],
    cwd: Path | None = None,
    timeout: float | None = None,
) -> dict[str, Any]:
    completed = subprocess.run(
        args,
        cwd=str(cwd) if cwd else None,
        timeout=timeout,
        capture_output=True,
        text=True,
    )
    return {
        "returncode": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
        "timed_out": False,
    }


def _run_command(
    args: list[str],
    *,
    execute: bool,
    runner: CommandRunner = default_subprocess_runner,
    cwd: Path | None = None,
    timeout_seconds: float | None = None,
) -> dict[str, Any]:
    command = shlex.join(args)
    if not execute:
        return {
            "command": command,
            "executed": False,
            "ok": True,
            "returncode": None,
            "stdout": "",
            "stderr": "",
            "json": None,
        }
    try:
        result = runner(args, cwd, timeout_seconds)
    except subprocess.TimeoutExpired as exc:
        return {
            "command": command,
            "executed": True,
            "ok": False,
            "returncode": None,
            "stdout": str(exc.stdout or ""),
            "stderr": str(exc.stderr or ""),
            "timed_out": True,
            "json": None,
        }
    stdout = str(result.get("stdout") or "")
    stderr = str(result.get("stderr") or "")
    parsed = _parse_json(stdout)
    ok = int(result.get("returncode") or 0) == 0 and _parsed_ok(parsed)
    return {
        "command": command,
        "executed": True,
        "ok": ok,
        "returncode": result.get("returncode"),
        "stdout": stdout,
        "stderr": stderr,
        "json": parsed,
    }


def _parse_json(text: str) -> Any:
    stripped = text.strip()
    if not stripped:
        return None
    try:
        return json.loads(stripped)
    except json.JSONDecodeError:
        return None


def _parsed_ok(parsed: Any) -> bool:
    if parsed is None:
        return True
    if not isinstance(parsed, dict):
        return True
    if parsed.get("ok") is False:
        return False
    if parsed.get("code") not in (None, 0):
        return False
    return True


def _command_error(command_result: dict[str, Any]) -> str:
    parsed = command_result.get("json")
    if isinstance(parsed, dict):
        error = parsed.get("error")
        if isinstance(error, dict):
            return str(error.get("message") or error)
        if error:
            return str(error)
        if parsed.get("msg") and parsed.get("code") not in (None, 0):
            return str(parsed.get("msg"))
    stderr = " ".join(str(command_result.get("stderr") or "").split())
    if stderr:
        return stderr[:OUTPUT_LIMIT]
    stdout = " ".join(str(command_result.get("stdout") or "").split())
    return stdout[:OUTPUT_LIMIT]


def _compact_text(value: Any, *, limit: int = TEXT_LIMIT) -> str:
    text = " ".join(str(value or "").split())
    if len(text) <= limit:
        return text
    return text[: max(0, limit - 1)].rstrip() + "..."


def now_lark_datetime(now: datetime | None = None) -> str:
    return (now or datetime.now()).strftime("%Y-%m-%d %H:%M:%S")


def append_history(existing: Any, entry: str, *, limit: int = TEXT_LIMIT) -> str:
    prior = str(existing or "").strip()
    combined = f"{prior}\n{entry}".strip() if prior else entry
    if len(combined) <= limit:
        return combined
    return combined[-limit:]


def lark_record_rows(payload: dict[str, Any]) -> list[dict[str, Any]]:
    data = payload.get("data") if isinstance(payload.get("data"), dict) else payload
    fields = data.get("fields") if isinstance(data, dict) else None
    rows = data.get("data") if isinstance(data, dict) else None
    record_ids = data.get("record_id_list") if isinstance(data, dict) else None
    if not isinstance(fields, list) or not isinstance(rows, list):
        return []
    records: list[dict[str, Any]] = []
    for index, values in enumerate(rows):
        if not isinstance(values, list):
            continue
        record = {str(field): values[pos] if pos < len(values) else None for pos, field in enumerate(fields)}
        if isinstance(record_ids, list) and index < len(record_ids):
            record["_record_id"] = record_ids[index]
        records.append(record)
    return records


def normalize_select_value(value: Any) -> str:
    if isinstance(value, list) and value:
        return str(value[0] or "")
    return str(value or "")


def choose_heartbeat_task(
    records: list[dict[str, Any]],
    *,
    agent_id: str,
) -> dict[str, Any] | None:
    own_claim: dict[str, Any] | None = None
    unclaimed: dict[str, Any] | None = None
    for record in records:
        status = normalize_select_value(record.get("Status"))
        claim = normalize_select_value(record.get("Claim"))
        claimed_by = str(record.get("Claimed By") or "").strip()
        if status in {STATUS_DONE, STATUS_BLOCKED, STATUS_REVIEW, STATUS_USER_GATE}:
            continue
        if claimed_by == agent_id and status in {STATUS_CLAIMED, STATUS_RUNNING, STATUS_TODO}:
            own_claim = own_claim or record
            continue
        if status == STATUS_TODO and claim in {"", CLAIM_UNCLAIMED} and not claimed_by:
            unclaimed = unclaimed or record
    return own_claim or unclaimed


def allowed_worker_command(command: str, prefixes: list[str]) -> bool:
    stripped = command.strip()
    if not stripped:
        return False
    if not prefixes:
        return False
    return any(stripped == prefix or stripped.startswith(prefix + " ") for prefix in prefixes)


def _record_json_args(values: dict[str, Any]) -> str:
    return json.dumps(values, ensure_ascii=False, separators=(",", ":"))


@dataclass(frozen=True)
class LarkKanbanConfig:
    base_token: str
    table_id: str
    view_id: str | None = DEFAULT_STATUS_QUEUE_VIEW
    cli_bin: str = DEFAULT_CLI_BIN
    identity: str = "bot"


def build_record_upsert_command(
    config: LarkKanbanConfig,
    *,
    record_id: str | None,
    values: dict[str, Any],
) -> list[str]:
    args = [
        config.cli_bin,
        "base",
        "+record-upsert",
        "--as",
        config.identity,
        "--base-token",
        config.base_token,
        "--table-id",
        config.table_id,
    ]
    if record_id:
        args.extend(["--record-id", record_id])
    args.extend(["--json", _record_json_args(values)])
    return args


def build_record_list_command(config: LarkKanbanConfig) -> list[str]:
    args = [
        config.cli_bin,
        "base",
        "+record-list",
        "--as",
        config.identity,
        "--base-token",
        config.base_token,
        "--table-id",
        config.table_id,
        "--offset",
        "0",
        "--limit",
        "200",
    ]
    if config.view_id:
        args.extend(["--view-id", config.view_id])
    return args


def build_create_board_plan(
    *,
    base_name: str,
    table_name: str,
    cli_bin: str = DEFAULT_CLI_BIN,
    identity: str = "bot",
    base_token: str | None = None,
    user_open_id: str | None = None,
) -> list[list[str]]:
    commands: list[list[str]] = []
    if not base_token:
        commands.append(
            [cli_bin, "base", "+base-create", "--as", identity, "--name", base_name]
        )
    token = base_token or "<base-token-from-create>"
    table_ref = "<table-id-from-create>"
    commands.append(
        [
            cli_bin,
            "base",
            "+table-create",
            "--as",
            identity,
            "--base-token",
            token,
            "--name",
            table_name,
            "--fields",
            json.dumps(lark_kanban_field_definitions(), ensure_ascii=False),
            "--view",
            json.dumps(lark_kanban_views(), ensure_ascii=False),
        ]
    )
    if user_open_id:
        commands.append(
            [
                cli_bin,
                "drive",
                "permission.members",
                "create",
                "--as",
                "bot",
                "--params",
                json.dumps(
                    {
                        "token": token,
                        "type": "bitable",
                        "need_notification": False,
                    },
                    ensure_ascii=False,
                ),
                "--data",
                json.dumps(
                    {
                        "member_id": user_open_id,
                        "member_type": "openid",
                        "perm": "full_access",
                        "perm_type": "container",
                        "type": "user",
                    },
                    ensure_ascii=False,
                ),
            ]
        )
    commands.extend(
        [
            [
                cli_bin,
                "base",
                "+view-set-filter",
                "--as",
                identity,
                "--base-token",
                token,
                "--table-id",
                table_ref,
                "--view-id",
                DEFAULT_STATUS_QUEUE_VIEW,
                "--json",
                json.dumps(
                    {
                        "logic": "and",
                        "conditions": [
                            ["Status", "intersects", [STATUS_TODO, STATUS_CLAIMED]]
                        ],
                    },
                    ensure_ascii=False,
                ),
            ],
            [
                cli_bin,
                "base",
                "+view-set-filter",
                "--as",
                identity,
                "--base-token",
                token,
                "--table-id",
                table_ref,
                "--view-id",
                "User Gates",
                "--json",
                json.dumps(
                    {
                        "logic": "and",
                        "conditions": [["Status", "intersects", [STATUS_USER_GATE]]],
                    },
                    ensure_ascii=False,
                ),
            ],
            [
                cli_bin,
                "base",
                "+view-set-group",
                "--as",
                identity,
                "--base-token",
                token,
                "--table-id",
                table_ref,
                "--view-id",
                "Kanban",
                "--json",
                json.dumps([{"field": "Status", "desc": False}], ensure_ascii=False),
            ],
        ]
    )
    return commands


def create_lark_kanban_board(
    *,
    base_name: str,
    table_name: str = DEFAULT_TABLE_NAME,
    cli_bin: str = DEFAULT_CLI_BIN,
    identity: str = "bot",
    base_token: str | None = None,
    user_open_id: str | None = None,
    execute: bool = False,
    runner: CommandRunner = default_subprocess_runner,
) -> dict[str, Any]:
    commands: list[dict[str, Any]] = []
    effective_base_token = base_token
    table_id: str | None = None
    if not effective_base_token:
        create = _run_command(
            [cli_bin, "base", "+base-create", "--as", identity, "--name", base_name],
            execute=execute,
            runner=runner,
        )
        commands.append(create)
        if create.get("executed"):
            if not create.get("ok"):
                return _board_payload(False, commands, effective_base_token, table_id)
            effective_base_token = _extract_base_token(create.get("json"))
            if not effective_base_token:
                commands.append(
                    {
                        "command": "extract Base token from base-create result",
                        "executed": True,
                        "ok": False,
                        "returncode": None,
                        "stdout": "",
                        "stderr": "base-create did not return a usable Base token",
                        "json": None,
                    }
                )
                return _board_payload(False, commands, effective_base_token, table_id)
    token = effective_base_token or "<base-token-from-create>"
    table_create = _run_command(
        [
            cli_bin,
            "base",
            "+table-create",
            "--as",
            identity,
            "--base-token",
            token,
            "--name",
            table_name,
            "--fields",
            json.dumps(lark_kanban_field_definitions(), ensure_ascii=False),
            "--view",
            json.dumps(lark_kanban_views(), ensure_ascii=False),
        ],
        execute=execute,
        runner=runner,
    )
    commands.append(table_create)
    if table_create.get("executed"):
        if not table_create.get("ok"):
            return _board_payload(False, commands, effective_base_token, table_id)
        table_id = _extract_table_id(table_create.get("json")) or table_name
    table_ref = table_id or table_name
    if user_open_id:
        grant = _run_command(
            [
                cli_bin,
                "drive",
                "permission.members",
                "create",
                "--as",
                "bot",
                "--params",
                json.dumps(
                    {
                        "token": token,
                        "type": "bitable",
                        "need_notification": False,
                    },
                    ensure_ascii=False,
                ),
                "--data",
                json.dumps(
                    {
                        "member_id": user_open_id,
                        "member_type": "openid",
                        "perm": "full_access",
                        "perm_type": "container",
                        "type": "user",
                    },
                    ensure_ascii=False,
                ),
            ],
            execute=execute,
            runner=runner,
        )
        commands.append(grant)
        if grant.get("executed") and not grant.get("ok"):
            return _board_payload(False, commands, effective_base_token, table_id)
    for command in (
        [
            cli_bin,
            "base",
            "+view-set-filter",
            "--as",
            identity,
            "--base-token",
            token,
            "--table-id",
            table_ref,
            "--view-id",
            DEFAULT_STATUS_QUEUE_VIEW,
            "--json",
            json.dumps(
                {
                    "logic": "and",
                    "conditions": [["Status", "intersects", [STATUS_TODO, STATUS_CLAIMED]]],
                },
                ensure_ascii=False,
            ),
        ],
        [
            cli_bin,
            "base",
            "+view-set-filter",
            "--as",
            identity,
            "--base-token",
            token,
            "--table-id",
            table_ref,
            "--view-id",
            "User Gates",
            "--json",
            json.dumps(
                {
                    "logic": "and",
                    "conditions": [["Status", "intersects", [STATUS_USER_GATE]]],
                },
                ensure_ascii=False,
            ),
        ],
        [
            cli_bin,
            "base",
            "+view-set-group",
            "--as",
            identity,
            "--base-token",
            token,
            "--table-id",
            table_ref,
            "--view-id",
            "Kanban",
            "--json",
            json.dumps([{"field": "Status", "desc": False}], ensure_ascii=False),
        ],
    ):
        result = _run_command(command, execute=execute, runner=runner)
        commands.append(result)
        if result.get("executed") and not result.get("ok"):
            return _board_payload(False, commands, effective_base_token, table_id)
    return _board_payload(True, commands, effective_base_token, table_id)


def _board_payload(
    ok: bool,
    commands: list[dict[str, Any]],
    base_token: str | None,
    table_id: str | None,
) -> dict[str, Any]:
    return {
        "ok": ok,
        "schema_version": LARK_KANBAN_SCHEMA_VERSION,
        "base_token": base_token,
        "table_id": table_id,
        "commands": commands,
        "error": None if ok else next((_command_error(item) for item in commands if not item.get("ok")), "unknown"),
    }


def _extract_base_token(parsed: Any) -> str | None:
    if not isinstance(parsed, dict):
        return None
    base = parsed.get("data", {}).get("base") if isinstance(parsed.get("data"), dict) else None
    if isinstance(base, dict):
        return str(base.get("base_token") or base.get("app_token") or "") or None
    return None


def _extract_table_id(parsed: Any) -> str | None:
    if not isinstance(parsed, dict):
        return None
    data = parsed.get("data") if isinstance(parsed.get("data"), dict) else {}
    table = data.get("table") if isinstance(data, dict) else None
    if isinstance(table, dict):
        return str(table.get("id") or table.get("table_id") or "") or None
    return None


def seed_lark_kanban_task(
    config: LarkKanbanConfig,
    *,
    task: dict[str, Any],
    execute: bool = False,
    runner: CommandRunner = default_subprocess_runner,
) -> dict[str, Any]:
    result = _run_command(
        build_record_upsert_command(config, record_id=None, values=task),
        execute=execute,
        runner=runner,
    )
    record_id = _extract_created_record_id(result.get("json"))
    return {
        "ok": bool(result.get("ok")),
        "schema_version": LARK_KANBAN_SCHEMA_VERSION,
        "record_id": record_id,
        "command": result,
        "task": task,
    }


def seed_lark_kanban_records(
    config: LarkKanbanConfig,
    *,
    records: list[dict[str, Any]],
    execute: bool = False,
    runner: CommandRunner = default_subprocess_runner,
) -> dict[str, Any]:
    results: list[dict[str, Any]] = []
    ok = True
    for record in records:
        result = seed_lark_kanban_task(
            config,
            task=record,
            execute=execute,
            runner=runner,
        )
        results.append(result)
        ok = ok and bool(result.get("ok"))
        if execute and not result.get("ok"):
            break
    return {
        "ok": ok,
        "schema_version": LARK_KANBAN_SCHEMA_VERSION,
        "record_count": len(records),
        "created_record_ids": [item.get("record_id") for item in results],
        "records": results,
    }


def _extract_created_record_id(parsed: Any) -> str | None:
    if not isinstance(parsed, dict):
        return None
    record = parsed.get("data", {}).get("record") if isinstance(parsed.get("data"), dict) else None
    if not isinstance(record, dict):
        return None
    ids = record.get("record_id_list")
    if isinstance(ids, list) and ids:
        return str(ids[0])
    return str(record.get("record_id") or record.get("id") or "") or None


def lark_kanban_heartbeat(
    config: LarkKanbanConfig,
    *,
    agent_id: str = DEFAULT_AGENT_ID,
    fixture: dict[str, Any] | None = None,
    worker_command: str | None = None,
    execute_lark: bool = False,
    execute_worker: bool = False,
    complete_on_success: bool = False,
    allowed_command_prefixes: list[str] | None = None,
    runner: CommandRunner = default_subprocess_runner,
    now: datetime | None = None,
    worker_timeout_seconds: float = 600.0,
) -> dict[str, Any]:
    commands: list[dict[str, Any]] = []
    if fixture is None:
        list_result = _run_command(
            build_record_list_command(config),
            execute=execute_lark,
            runner=runner,
        )
        commands.append(list_result)
        if execute_lark and not list_result.get("ok"):
            return _heartbeat_payload(
                ok=False,
                decision="record_list_failed",
                agent_id=agent_id,
                commands=commands,
                records=[],
            )
        parsed = list_result.get("json") if execute_lark else {"data": {"fields": [], "data": []}}
    else:
        parsed = fixture
    records = lark_record_rows(parsed if isinstance(parsed, dict) else {})
    task = choose_heartbeat_task(records, agent_id=agent_id)
    if task is None:
        return _heartbeat_payload(
            ok=True,
            decision="no_claimable_task",
            agent_id=agent_id,
            commands=commands,
            records=records,
        )
    record_id = str(task.get("_record_id") or "").strip()
    if not record_id:
        return _heartbeat_payload(
            ok=False,
            decision="selected_task_missing_record_id",
            agent_id=agent_id,
            commands=commands,
            records=records,
            selected_task=task,
        )
    timestamp = now_lark_datetime(now)
    claim_values = {
        "Status": STATUS_CLAIMED,
        "Claim": CLAIM_AGENT,
        "Claimed By": agent_id,
        "Last Heartbeat": timestamp,
        "Run History": append_history(task.get("Run History"), f"{timestamp} {agent_id}: claimed"),
    }
    claim_result = _run_command(
        build_record_upsert_command(config, record_id=record_id, values=claim_values),
        execute=execute_lark,
        runner=runner,
    )
    commands.append(claim_result)
    if execute_lark and not claim_result.get("ok"):
        return _heartbeat_payload(
            ok=False,
            decision="claim_failed",
            agent_id=agent_id,
            commands=commands,
            records=records,
            selected_task=task,
        )
    command = (worker_command if worker_command is not None else str(task.get("Worker Command") or "")).strip()
    if not command:
        worker = {
            "attempted": False,
            "executed": False,
            "ok": False,
            "reason": "worker_command_missing",
            "command": "",
        }
        final_status = STATUS_USER_GATE
        evidence = "worker command missing; user must provide Worker Command or heartbeat --worker-command"
        result_code = None
    elif not execute_worker:
        worker = {
            "attempted": True,
            "executed": False,
            "ok": True,
            "reason": "execute_worker_not_set",
            "command": command,
        }
        final_status = STATUS_CLAIMED
        evidence = f"dry-run worker command: {command}"
        result_code = None
    elif not allowed_worker_command(command, allowed_command_prefixes or []):
        worker = {
            "attempted": True,
            "executed": False,
            "ok": False,
            "reason": "worker_command_prefix_not_allowed",
            "command": command,
            "allowed_prefixes": allowed_command_prefixes or [],
        }
        final_status = STATUS_BLOCKED
        evidence = "worker command blocked by prefix allowlist"
        result_code = None
    else:
        workdir = Path(str(task.get("Workdir") or ".")).expanduser()
        worker_args = shlex.split(command)
        worker_result = _run_command(
            worker_args,
            execute=True,
            runner=runner,
            cwd=workdir,
            timeout_seconds=worker_timeout_seconds,
        )
        worker = {
            "attempted": True,
            "executed": True,
            "ok": bool(worker_result.get("ok")),
            "reason": "completed" if worker_result.get("ok") else "failed",
            "command": command,
            "returncode": worker_result.get("returncode"),
            "stdout": _compact_text(worker_result.get("stdout"), limit=OUTPUT_LIMIT),
            "stderr": _compact_text(worker_result.get("stderr"), limit=OUTPUT_LIMIT),
        }
        final_status = STATUS_DONE if worker_result.get("ok") and complete_on_success else STATUS_REVIEW
        if not worker_result.get("ok"):
            final_status = STATUS_BLOCKED
        evidence = _compact_text(
            worker.get("stdout") or worker.get("stderr") or worker.get("reason"),
            limit=OUTPUT_LIMIT,
        )
        result_code = worker_result.get("returncode")
    finish_values = {
        "Status": final_status,
        "Claim": CLAIM_AGENT,
        "Claimed By": agent_id,
        "Last Heartbeat": timestamp,
        "Evidence": evidence,
        "Last Result Code": result_code,
        "Last Error": "" if worker.get("ok") else _compact_text(worker.get("stderr") or worker.get("reason")),
        "Run History": append_history(
            claim_values["Run History"],
            f"{timestamp} {agent_id}: worker {worker.get('reason')} -> {final_status}",
        ),
        "Handoff": _handoff_for_status(final_status, agent_id=agent_id),
    }
    finish_result = _run_command(
        build_record_upsert_command(config, record_id=record_id, values=finish_values),
        execute=execute_lark,
        runner=runner,
    )
    commands.append(finish_result)
    ok = bool(worker.get("ok")) and (not execute_lark or finish_result.get("ok"))
    return _heartbeat_payload(
        ok=ok,
        decision="task_processed",
        agent_id=agent_id,
        commands=commands,
        records=records,
        selected_task=task,
        worker=worker,
        final_status=final_status,
        writeback=finish_values,
    )


def _handoff_for_status(status: str, *, agent_id: str) -> str:
    if status == STATUS_DONE:
        return f"{agent_id} completed the task; review evidence and close any external issue/PR bookkeeping."
    if status == STATUS_REVIEW:
        return f"{agent_id} produced evidence; human/controller review should decide merge or next todo."
    if status == STATUS_USER_GATE:
        return "User input is required before this task can proceed."
    if status == STATUS_BLOCKED:
        return f"{agent_id} hit a blocker; inspect Last Error and decide repair/retry/reassign."
    return f"{agent_id} claimed the task; heartbeat can continue."


def _heartbeat_payload(
    *,
    ok: bool,
    decision: str,
    agent_id: str,
    commands: list[dict[str, Any]],
    records: list[dict[str, Any]],
    selected_task: dict[str, Any] | None = None,
    worker: dict[str, Any] | None = None,
    final_status: str | None = None,
    writeback: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "ok": ok,
        "schema_version": LARK_KANBAN_HEARTBEAT_VERSION,
        "agent_id": agent_id,
        "decision": decision,
        "record_count": len(records),
        "selected_record_id": selected_task.get("_record_id") if selected_task else None,
        "selected_task": selected_task,
        "worker": worker,
        "final_status": final_status,
        "writeback": writeback,
        "commands": commands,
    }


def render_lark_kanban_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# LoopX Lark Kanban",
        "",
        f"- ok: `{payload.get('ok')}`",
        f"- schema_version: `{payload.get('schema_version')}`",
    ]
    for key in ("base_token", "table_id", "agent_id", "decision", "selected_record_id", "final_status"):
        if payload.get(key) is not None:
            lines.append(f"- {key}: `{payload.get(key)}`")
    if payload.get("error"):
        lines.append(f"- error: {payload.get('error')}")
    if isinstance(payload.get("commands"), list):
        lines.append("")
        lines.append("## Commands")
        for item in payload["commands"]:
            if isinstance(item, dict):
                marker = "ran" if item.get("executed") else "dry-run"
                lines.append(f"- `{marker}` `{item.get('command')}`")
    if isinstance(payload.get("writeback"), dict):
        lines.append("")
        lines.append("## Writeback")
        for key, value in payload["writeback"].items():
            lines.append(f"- {key}: `{_compact_text(value, limit=220)}`")
    return "\n".join(lines)
