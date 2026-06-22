# Lark Kanban Control-Plane Adapter

Status: prototype adapter contract v0.

This adapter models a LoopX long-task control plane in a Feishu/Lark Base
Kanban board. It is intentionally a thin projection over the same LoopX ideas:
todos, claims, user gates, handoff, evidence, and run history. It does not
replace the executor runtime, quota guard, or future daemon lease model.

## Mapping

| LoopX concept | Lark Base field |
| --- | --- |
| Todo | One task row. `Task` is the visible title. |
| Todo status | `Status` single select: `Todo`, `Claimed`, `Running`, `User Gate`, `Blocked`, `Review`, `Done`. |
| Claim | `Claim` single select plus `Claimed By` text. |
| User gate | `Status=User Gate` plus concrete question in `User Gate`. |
| Handoff | `Handoff` text. |
| Evidence | `Evidence` text. |
| Run history | `Run History` compact append-style text. |
| Scope | `Scope` text, advisory in v0. |
| Quota | Omitted in v0; the prototype assumes no quota limit. |
| Worker launch | `Worker Command` and `Workdir`, consumed by heartbeat. |

The Kanban view groups by `Status`, so the board is the operator-facing
control surface. Agent workers use the filtered `Worker Queue` view.

## Trigger Model

Direct Base-to-local-agent triggering requires a reachable callback, local
daemon bridge, or product-side event subscription that can wake an edge worker.
The current v0 prototype therefore uses a heartbeat:

1. Worker polls `Worker Queue`.
2. Worker chooses one `Todo` row whose `Claim=Unclaimed`, or resumes its own
   existing `Claimed`/`Running` row.
3. Worker writes `Status=Claimed`, `Claim=Agent`, `Claimed By=<agent_id>`.
4. Worker optionally executes the row's `Worker Command`.
5. Worker writes compact `Evidence`, `Run History`, `Handoff`, `Last Error`,
   `Last Result Code`, and final `Status`.

This matches the cloud-to-edge bring-up shape: the cloud board is the shared
coordination plane; a managed agent wrapper or daemon remains responsible for
starting and supervising the edge executor. The prototype command is:

```bash
python3 -m loopx.cli lark-kanban heartbeat \
  --base-token <base-token> \
  --table-id <table-id> \
  --agent-id codex-kanban-worker \
  --execute-lark \
  --execute-worker \
  --allow-command-prefix "codex exec"
```

For repeatable local verification, use a deterministic worker command instead
of `codex exec`:

```bash
python3 -m loopx.cli lark-kanban heartbeat \
  --base-token <base-token> \
  --table-id <table-id> \
  --agent-id codex-kanban-worker \
  --execute-lark \
  --execute-worker \
  --allow-command-prefix "python3"
```

## CLI Surface

```bash
python3 -m loopx.cli lark-kanban schema --format json
python3 -m loopx.cli lark-kanban plan-create --base-name "LoopX Kanban POC"
python3 -m loopx.cli lark-kanban create-board --base-name "LoopX Kanban POC" --execute
python3 -m loopx.cli lark-kanban seed-task --base-token <base> --table-id <table> --execute
python3 -m loopx.cli lark-kanban heartbeat --base-token <base> --table-id <table> --execute-lark
```

`create-board`, `seed-task`, and `heartbeat` are dry-run unless their explicit
execute flags are set. Worker execution has its own gate,
`--execute-worker`, and an allowlist gate, `--allow-command-prefix`.

## Review Boundary

The prototype deliberately keeps raw agent transcripts, credentials, local
private paths, and hidden benchmark material out of Lark rows. `Evidence` and
`Run History` should contain compact public-safe summaries or artifact
pointers. If a real worker needs to store detailed logs, store them in the
worker's normal trace surface and write only a compact pointer back to Base.

## Validation

Run the fixture smoke:

```bash
python3 examples/lark-kanban-control-plane-smoke.py
```

The smoke proves the schema, board command plan, task selection, soft claim,
worker execution, evidence writeback, handoff, and CLI fixture path without
requiring live Lark credentials.
