#!/usr/bin/env python3
"""Validate the public department self-iteration rollout fixtures."""

from __future__ import annotations

import json
import re
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_PATH = REPO_ROOT / "examples/fixtures/department-self-iteration-rollout.public.json"
LIVE_FIXTURE_GLOB = "department-live-generated-rollout-seed*.public.json"

PRIVATE_PATTERNS = [
    re.compile(r"/Users/[A-Za-z0-9._-]+/"),
    re.compile(r"/home/[A-Za-z0-9._-]+/"),
    re.compile(r"/private/"),
    re.compile(r"[A-Za-z]:\\\\Users\\\\"),
    re.compile(r"\bBearer\s+[A-Za-z0-9._-]+"),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
]

REQUIRED_BOUNDARY_FALSE = {
    "raw_task_text_recorded",
    "raw_logs_recorded",
    "raw_trajectory_recorded",
    "raw_session_transcript_recorded",
    "credential_values_recorded",
    "absolute_paths_recorded",
}

ALLOWED_CONFIDENCE = {
    "observed",
    "inferred_high",
    "inferred_medium",
    "synthetic_bridge",
}


def assert_public_safe(text: str) -> None:
    for pattern in PRIVATE_PATTERNS:
        if pattern.search(text):
            raise AssertionError(f"fixture matched private pattern {pattern.pattern!r}")


def assert_boundary(payload: dict, label: str) -> None:
    boundary = payload.get("boundary")
    assert isinstance(boundary, dict), (label, boundary)
    for key in REQUIRED_BOUNDARY_FALSE:
        assert boundary.get(key) is False, (label, key, boundary)


def main() -> int:
    fixture_text = FIXTURE_PATH.read_text(encoding="utf-8")
    assert_public_safe(fixture_text)
    payload = json.loads(fixture_text)

    assert payload["schema_version"] == "department_animation_fixture_v0", payload
    assert payload["goal_id"] == "loopx-meta", payload
    assert payload["truth_contract"]["event_ledger_is_source_of_truth"] is True, payload
    assert payload["truth_contract"]["fixture_is_writable"] is False, payload
    assert payload["truth_contract"]["projection_is_writable"] is False, payload
    assert payload["truth_contract"]["write_authority"] == "none", payload

    public_boundary = payload["public_boundary"]
    for key in REQUIRED_BOUNDARY_FALSE:
        assert public_boundary.get(key) is False, (key, public_boundary)
    assert public_boundary.get("private_material_body_recorded") is False, public_boundary

    lanes = {lane["lane_id"]: lane for lane in payload["lanes"]}
    assert {"main_control", "side_bypass", "product_capability"} <= set(lanes), lanes
    assert lanes["side_bypass"]["agent_id"] == "codex-side-bypass", lanes

    rollout_events = payload["rollout_events"]
    assert len(rollout_events) >= 6, rollout_events
    event_ids = [event["event_id"] for event in rollout_events]
    assert len(event_ids) == len(set(event_ids)), event_ids
    event_lanes = {event.get("lane", {}).get("lane_id") for event in rollout_events}
    assert {"side_bypass", "product_capability"} <= event_lanes, event_lanes

    saw_gate = False
    saw_handoff = False
    saw_validation = False
    saw_pr_ref = False
    saw_deferred_resume = False

    for event in rollout_events:
        assert event["schema_version"] == "loopx_rollout_event_v0", event
        assert event["goal_id"] == "loopx-meta", event
        assert_boundary(event, event["event_id"])
        assert event.get("summary"), event
        assert not any(str(ref).startswith("/") for ref in event.get("artifact_refs", [])), event
        causality = event.get("causality", {})
        if causality.get("gate_id") == "gate_minimal_rollout_fixture":
            saw_gate = True
        if event.get("handoff", {}).get("to_agent_id") == "codex-side-bypass":
            saw_handoff = True
        if event["event_kind"] == "validation":
            saw_validation = True
        if event.get("code_refs", {}).get("pr_ref"):
            saw_pr_ref = True
        transition = event.get("state_transition", {})
        if transition.get("from_state", "").startswith("deferred"):
            saw_deferred_resume = True

    assert saw_gate, "human/fixture gate missing"
    assert saw_handoff, "side-bypass handoff missing"
    assert saw_validation, "validation event missing"
    assert saw_pr_ref, "PR evidence missing"
    assert saw_deferred_resume, "deferred-to-ready transition missing"

    animation_events = payload["animation_events"]
    assert len(animation_events) >= 5, animation_events
    animation_ids = [event["animation_event_id"] for event in animation_events]
    assert len(animation_ids) == len(set(animation_ids)), animation_ids
    assert any(event["kind"] == "human_gate" for event in animation_events), animation_events
    assert any(event["display_hint"] == "dashed_edge" for event in animation_events), animation_events
    assert any(event["confidence"] == "synthetic_bridge" for event in animation_events), animation_events
    for event in animation_events:
        assert event["confidence"] in ALLOWED_CONFIDENCE, event
        assert event["lane_id"] in lanes, event
        assert event.get("source_event_ids"), event

    must_render = set(payload["frontend_acceptance"]["must_render"])
    assert "three agent lanes" in must_render, must_render
    assert "one human gate node" in must_render, must_render
    assert "one dashed inferred bridge" in must_render, must_render

    live_fixture_paths = sorted((REPO_ROOT / "examples/fixtures").glob(LIVE_FIXTURE_GLOB))
    assert len(live_fixture_paths) >= 2, live_fixture_paths
    live_run_counts: list[tuple[str, int]] = []
    for live_fixture_path in live_fixture_paths:
        live_fixture_text = live_fixture_path.read_text(encoding="utf-8")
        assert_public_safe(live_fixture_text)
        live_payload = json.loads(live_fixture_text)
        assert live_payload["schema_version"] == "department_live_generated_fixture_seed_v0", live_payload
        assert live_payload["goal_id"] == "loopx-meta", live_payload
        for key in REQUIRED_BOUNDARY_FALSE:
            assert live_payload["public_boundary"].get(key) is False, (
                key,
                live_payload["public_boundary"],
            )
        assert live_payload["public_boundary"].get("private_material_body_recorded") is False, live_payload
        assert live_payload["capture_contract"]["source"] == "live_loopx_cli_capture", live_payload
        assert live_payload["capture_contract"]["raw_payloads_committed"] is False, live_payload

        commands = live_payload["capture_contract"]["commands"]
        command_ids = {command["command_id"] for command in commands}
        assert {
            "quota_should_run_product_capability",
            "global_status",
            "history_recent",
        } <= command_ids, command_ids
        assert all(command["payload_bytes_observed"] > 1000 for command in commands), commands

        quota = live_payload["observed_control_plane"]["quota_should_run"]
        assert quota["decision"] == "run", quota
        assert quota["interaction_contract"]["schema_version"] == "loopx_interaction_contract_v0", quota
        assert quota["interaction_contract"]["user_channel"]["action_required"] is False, quota
        assert quota["interaction_contract"]["agent_channel"]["must_attempt"] is True, quota
        assert quota["interaction_contract"]["cli_channel"]["spend_after_validation"] is True, quota
        assert quota["capability_gate"]["runnable_count"] >= 1, quota
        assert quota["agent_todo_summary"]["open_count"] >= len(
            quota["agent_todo_summary"]["first_executable_items"]
        ), quota

        status = live_payload["observed_control_plane"]["status"]
        assert status["goal_count"] >= 1, status
        assert status["run_count"] >= status["usage_summary"]["runs_24h"], status
        assert status["todo_index"]["schema_version"] == "todo_index_v0", status
        assert status["event_ledger_summary"]["source"] == "run_history", status
        live_run_counts.append((live_payload["generated_at"], status["run_count"]))

        warnings = {warning["warning_kind"] for warning in live_payload["observed_warnings"]}
        assert "stale_latest_run_projection" in warnings, warnings
        assert "completed_agent_todo_archive_required" in warnings, warnings
        assert "promotion_readiness_stale" in warnings, warnings

        noise_cases = {case["case_id"] for case in live_payload["frontend_noise_cases"]}
        assert "large_status_payload" in noise_cases, noise_cases
        assert "warnings_are_first_class" in noise_cases, noise_cases
        assert live_payload["fixture_pairing"]["curated_story_fixture"] == (
            "examples/fixtures/department-self-iteration-rollout.public.json"
        ), live_payload

    ordered_live_run_counts = [run_count for _, run_count in sorted(live_run_counts)]
    assert ordered_live_run_counts == sorted(ordered_live_run_counts), live_run_counts

    print("department-self-iteration-rollout-fixtures-smoke ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
