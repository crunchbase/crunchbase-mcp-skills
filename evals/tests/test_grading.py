import copy
import json
from pathlib import Path
import tempfile
import unittest

from evals.grade import evidence_digest, grade_case, load_run, merge_attempts, review_key
from evals.report import build_report, paired_estimate
from evals.review import calibration, export_packets, import_labels


def sample():
    case = {"id": "scope", "family": "missing_scope", "split": "dev", "workflow": "landscape", "turns": [{"user": "Map dental software with Crunchbase"}], "checks": [{"id": "read_only", "kind": "no_write", "severity": "critical"}, {"id": "ask", "kind": "semantic", "rubric": "Ask about the missing material scope."}]}
    trial = {"case_id": "scope", "arm": "candidate", "trial": 1, "status": "completed", "turns": [{"turn": 1, "final": "What geography and funding stage should I use?"}], "skill_reads": []}
    return case, trial, [], {"lists": {}}


class GradingTests(unittest.TestCase):
    def test_deterministic_pass_does_not_approve_unreviewed_result(self):
        self.assertEqual(grade_case(*sample())["status"], "needs_review")

    def test_empty_runtime_inventory_does_not_consume_task_budget(self):
        case, trial, _, state = sample()
        case["checks"] = [{"id": "budget", "kind": "max_calls", "limit": 0}]
        for arm in ("candidate", "baseline"):
            trial["arm"] = arm
            for tool, key in (("list_mcp_resources", "resources"), ("list_mcp_resource_templates", "resourceTemplates")):
                event = {"turn": 1, "tool": tool, "server": "codex", "status": "completed", "arguments": {}, "result": {key: []}}
                self.assertEqual(grade_case(case, trial, [event], state)["status"], "passed")
                for change in ({"server": "external"}, {"status": "failed"}, {"arguments": {"server": "external"}}, {"result": {key: [{"uri": "data"}]}}, {"error": "failure"}, {"tool": "cb_reference", "result": {}}, {"tool": "read_mcp_resource", "result": {}}):
                    with self.subTest(arm=arm, change=change):
                        self.assertEqual(grade_case(case, trial, [{**event, **change}], state)["status"], "failed")

    def test_runtime_inventory_remains_in_evidence_and_explicit_tool_checks(self):
        case, trial, _, state = sample()
        event = {"turn": 1, "tool": "list_mcp_resources", "server": "codex", "status": "completed", "arguments": {}, "result": {"resources": []}}
        case["checks"] = [{"id": "explicit", "kind": "not_called", "tools": ["list_mcp_resources"]}]
        self.assertEqual(grade_case(case, trial, [event], state)["status"], "failed")
        self.assertNotEqual(evidence_digest(case, trial, [event], state), evidence_digest(case, trial, [], state))

    def test_attempted_failed_write_is_still_violation(self):
        case, trial, _, state = sample()
        events = [{"turn": 1, "tool": "mcp__fixture__cb_list_create", "result": {"error": {"code": "AUTH_ERROR"}}}]
        score = grade_case(case, trial, events, state)
        self.assertEqual(score["checks"][0]["status"], "failed")
        self.assertEqual(score["status"], "failed")

    def test_turn_scoped_gate_accepts_later_authorized_write(self):
        case, trial, _, state = sample()
        case["checks"] = [{"id": "before_permission", "kind": "no_write", "turn": 1}]
        events = [{"turn": 2, "tool": "cb_list_create", "result": {}}]
        self.assertEqual(grade_case(case, trial, events, state)["status"], "passed")

    def test_persisted_state_overrides_success_claim(self):
        case, trial, _, state = sample()
        case["checks"] = [{"id": "saved", "kind": "membership", "list_id": "l1", "entity_ids": ["org-a", "org-b"], "mode": "exact"}]
        trial["turns"][0]["final"] = "Successfully saved both companies."
        state["lists"]["l1"] = {"name": "Research", "entity_ids": ["org-a"]}
        self.assertEqual(grade_case(case, trial, [], state)["status"], "failed")
        state["lists"]["l1"]["entity_ids"].append("org-b")
        self.assertEqual(grade_case(case, trial, [], state)["status"], "passed")

    def test_turn_membership_uses_its_snapshot_not_later_state(self):
        case, trial, _, state = sample()
        before = {"lists": {"l1": {"name": "Research", "entity_ids": ["a"]}}}
        after = {"lists": {"l1": {"name": "Research", "entity_ids": ["a", "b"]}}}
        trial["turns"] = [{"turn": 1, "state_after": before},
                          {"turn": 2, "state_after": after},
                          {"turn": 3, "state_after": after}]
        events = [{"turn": 2, "tool": "cb_list_add_entities", "state_after": after}]
        for turn, expected in ((1, ["a"]), (2, ["a", "b"]), (3, ["a", "b"])):
            case["checks"] = [{"id": "members", "kind": "membership", "turn": turn,
                               "list_id": "l1", "entity_ids": expected}]
            self.assertEqual(grade_case(case, trial, events, after)["status"], "passed")
        case["checks"][0].update(turn=1, entity_ids=["a", "b"])
        self.assertEqual(grade_case(case, trial, events, after)["status"], "failed")
        changed = copy.deepcopy(trial)
        changed["turns"][0]["state_after"] = after
        self.assertNotEqual(evidence_digest(case, trial, events, after), evidence_digest(case, changed, events, after))

    def test_legacy_turn_state_is_unknown_without_a_snapshot(self):
        case, trial, _, state = sample()
        state = {"lists": {"l1": {"name": "Research", "entity_ids": ["a"]}}}
        for kind in ("membership", "list_created"):
            check = {"id": "state", "kind": kind, "turn": 1, "entity_ids": ["a"]}
            check.update({"list_id": "l1"} if kind == "membership" else {"name": "Research"})
            case["checks"] = [check]
            self.assertEqual(grade_case(case, trial, [], state)["status"], "needs_review")
        case["checks"] = [{"id": "members", "kind": "membership", "turn": 1, "list_id": "l1", "entity_ids": ["a"]}]
        events = [{"turn": 1, "state_after": state}]
        self.assertEqual(grade_case(case, trial, events, state)["status"], "passed")

    def test_human_label_requires_matching_evidence(self):
        case, trial, events, state = sample()
        key = review_key(trial, case["checks"][1])
        label = {"pass": True, "source": "human", "reviewer": "Reviewer A", "evidence": "Turn 1 asks about geography and stage.", "evidence_digest": evidence_digest(case, trial, events, state)}
        self.assertEqual(grade_case(case, trial, events, state, {key: label})["status"], "passed")
        trial["turns"][0]["final"] = "I assumed US seed."
        self.assertEqual(grade_case(case, trial, events, state, {key: label})["status"], "needs_review")

    def test_model_label_cannot_approve_semantic_check(self):
        case, trial, events, state = sample()
        key = review_key(trial, case["checks"][1])
        label = {"pass": True, "source": "model", "reviewer": "judge", "evidence": "Looks good", "evidence_digest": evidence_digest(case, trial, events, state)}
        self.assertEqual(grade_case(case, trial, events, state, {key: label})["status"], "needs_review")

    def test_changed_rubric_invalidates_previous_review(self):
        case, trial, events, state = sample()
        before = evidence_digest(case, trial, events, state)
        case["checks"][1]["rubric"] = "A materially different criterion."
        self.assertNotEqual(before, evidence_digest(case, trial, events, state))

    def test_client_attempt_is_counted_without_doubling_server_call(self):
        attempt = {"turn": 1, "tool": "cb_list_create", "arguments": {"name": "test"}}
        self.assertEqual(len(merge_attempts([], [attempt])), 1)
        self.assertEqual(len(merge_attempts([attempt], [attempt])), 1)
        self.assertEqual(len(merge_attempts([attempt], [attempt, attempt])), 2)
        case, trial, _, state = sample()
        self.assertEqual(grade_case(case, trial, merge_attempts([], [attempt]), state)["status"], "failed")

    def test_failed_client_attempt_not_swallowed_by_successful_identical_retry(self):
        success = {"turn": 1, "tool": "cb_list_create", "arguments": {"name": "test"}, "result": {"list_id": "a"}}
        failure = {**success, "result": {"error": {"code": "TRANSPORT_ERROR"}}}
        merged = merge_attempts([success], [failure, success])
        self.assertEqual(len(merged), 2)
        self.assertTrue(any(e.get("result", {}).get("error", {}).get("code") == "TRANSPORT_ERROR" for e in merged))

    def test_reference_markdown_content_is_not_an_mcp_content_envelope(self):
        event = {"turn": 1, "tool": "cb_reference", "arguments": {"path": "index"}, "result": {"path": "index", "content": "# Schema reference"}}
        self.assertEqual(merge_attempts([event], [event]), [event])

    def test_failed_tool_status_with_structured_provider_error_is_not_doubled(self):
        server = {"turn": 1, "tool": "cb_entity_get", "arguments": {"entity_id": "a"}, "result": {"error": {"code": "AUTHENTICATION_REQUIRED", "message": "Login required"}}}
        attempt = {**server, "status": "failed"}
        self.assertEqual(merge_attempts([server], [attempt]), [server])

    def test_embedded_profile_error_is_reported_and_respects_allowed_codes(self):
        case, trial, _, state = sample()
        case["checks"] = [{"id": "errors", "kind": "tool_errors", "max": 0}]
        events = [{"turn": 1, "tool": "mcp__fixture__cb_expert_resolve_entity", "result": {"disambiguation": {"result_type": "match"}, "entity": {"error": {"code": "AUTHENTICATION_REQUIRED"}}}}]
        score = grade_case(case, trial, events, state)
        self.assertEqual(score["observed_tool_errors"], [{"turn": 1, "tool": "cb_expert_resolve_entity", "path": "entity.error", "code": "AUTHENTICATION_REQUIRED"}])
        self.assertEqual(score["status"], "failed")
        case["checks"][0]["allowed_codes"] = ["AUTHENTICATION_REQUIRED"]
        self.assertEqual(grade_case(case, trial, events, state)["status"], "passed")

    def test_embedded_error_diagnostic_does_not_itself_fail_outcome(self):
        case, trial, _, state = sample()
        events = [{"turn": 1, "tool": "cb_expert_resolve_entity", "result": {"entity": {"error": {"code": "AUTHENTICATION_REQUIRED"}}}}]
        score = grade_case(case, trial, events, state)
        self.assertEqual(score["status"], "needs_review")
        self.assertEqual(score["checks"][0]["status"], "passed")
        self.assertEqual(len(score["observed_tool_errors"]), 1)

    def test_record_error_fields_are_not_provider_errors(self):
        case, trial, _, state = sample()
        for tool, result in [("cb_entity_get", {"properties": [{"field_id": "error", "value": {"code": "NOT_A_PROVIDER_ERROR"}}]}),
                             ("cb_entity_get", {"entity": {"error": {"code": "NOT_A_RESOLVER_ERROR"}}}),
                             ("cb_expert_resolve_entity", {"entity": {"properties": [{"field_id": "error", "value": "Record content"}]}})]:
            with self.subTest(tool=tool, result=result):
                self.assertEqual(grade_case(case, trial, [{"tool": tool, "result": result}], state)["observed_tool_errors"], [])

    def test_failed_client_embedded_error_is_not_swallowed_by_success(self):
        success = {"turn": 1, "tool": "cb_expert_resolve_entity", "arguments": {"name": "Example"}, "result": {"entity": {"properties": []}}}
        failure = {**success, "result": {"entity": {"error": {"code": "AUTHENTICATION_REQUIRED"}}}}
        self.assertEqual(merge_attempts([success], [failure, success]), [success, {**failure, "source": "client_attempt"}])

    def test_failed_status_with_embedded_provider_error_is_not_doubled(self):
        server = {"turn": 1, "tool": "cb_expert_resolve_entity", "arguments": {"name": "Example"}, "result": {"entity": {"error": {"code": "AUTHENTICATION_REQUIRED"}}}}
        attempt = {**server, "status": "failed"}
        self.assertEqual(merge_attempts([server], [attempt]), [server])

    def test_baseline_is_not_penalized_for_absent_skill(self):
        case, trial, events, state = sample()
        case["checks"] = [{"id": "routing", "kind": "activation", "skill": "company-brief", "expected": True}, {"id": "no_write", "kind": "no_write"}]
        trial["arm"] = "baseline"
        result = grade_case(case, trial, events, state)
        self.assertEqual(result["checks"][0]["status"], "skipped")
        self.assertEqual(result["outcome_status"], "passed")

    def test_missing_activation_instrumentation_is_not_negative_evidence(self):
        case, trial, events, state = sample()
        case["checks"] = [{"id": "routing", "kind": "activation", "skill": "brief", "expected": False}]
        del trial["skill_reads"]
        self.assertEqual(grade_case(case, trial, events, state)["status"], "needs_review")

    def test_allowed_service_error_is_distinct_from_unexpected_invalid_query(self):
        case, trial, _, state = sample()
        case["checks"] = [{"id": "error_contract", "kind": "tool_errors", "max": 0, "allowed_codes": ["AUTH_ERROR"]}]
        events = [{"result": {"error": {"code": "AUTH_ERROR"}}}]
        self.assertEqual(grade_case(case, trial, events, state)["status"], "passed")
        events[0]["result"]["error"]["code"] = "VALIDATION_ERROR"
        self.assertEqual(grade_case(case, trial, events, state)["status"], "failed")

    def test_unknown_check_fails_closed(self):
        case, trial, events, state = sample()
        case["checks"] = [{"id": "typo", "kind": "allow_everything"}]
        self.assertEqual(grade_case(case, trial, events, state)["status"], "failed")


class RunIntegrityTests(unittest.TestCase):
    def make_run(self, root):
        case, trial, events, state = sample()
        (root / "suite.json").write_text(json.dumps({"cases": [case]}))
        manifest = {"jobs": [{"case_id": case["id"], "arm": "candidate", "trial": 1, "path": "trials/job1"}]}
        (root / "manifest.json").write_text(json.dumps(manifest))
        return case, trial, events, state

    def test_missing_planned_job_is_infrastructure_error(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            self.make_run(root)
            _, entries = load_run(root)
            self.assertEqual(len(entries), 1)
            self.assertEqual(grade_case(*entries[0])["status"], "infra_error")

    def test_wrong_shaped_trial_retains_planned_job_in_report(self):
        for value in ([], [1], None, "invalid", 7, True):
            with self.subTest(value=value), tempfile.TemporaryDirectory() as d:
                root = Path(d)
                self.make_run(root)
                directory = root / "trials/job1"
                directory.mkdir(parents=True)
                (directory / "trial.json").write_text(json.dumps(value))
                manifest, entries = load_run(root)
                self.assertEqual(len(entries), 1)
                self.assertIn("JSON object", entries[0][1]["error"])
                score = grade_case(*entries[0])
                self.assertEqual(score["status"], "infra_error")
                report, summary = build_report([score], manifest)
                self.assertEqual(summary["release_gate"], "not_ready")

    def test_duplicate_plan_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            self.make_run(root)
            manifest = json.loads((root / "manifest.json").read_text())
            manifest["jobs"] *= 2
            (root / "manifest.json").write_text(json.dumps(manifest))
            with self.assertRaises(ValueError):
                load_run(root)

    def test_frozen_suite_tampering_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            self.make_run(root)
            manifest = json.loads((root / "manifest.json").read_text())
            manifest["suite_sha256"] = "invalid"
            (root / "manifest.json").write_text(json.dumps(manifest))
            with self.assertRaisesRegex(ValueError, "hash mismatch"):
                load_run(root)

    def test_blind_export_and_human_import(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            case, trial, events, state = self.make_run(root)
            directory = root / "trials/job1"
            directory.mkdir(parents=True)
            (directory / "trial.json").write_text(json.dumps(trial))
            (directory / "tools.jsonl").write_text("")
            (directory / "state.json").write_text(json.dumps(state))
            output = root / "review"
            self.assertEqual(export_packets(root, output), 1)
            packets = json.loads((output / "packets.json").read_text())
            self.assertNotIn("arm", packets[0])
            self.assertNotIn("case_id", packets[0])
            packets[0]["judgments"][0].update({"pass": True, "evidence": "Turn 1 asks about geography and stage."})
            (output / "packets.json").write_text(json.dumps(packets))
            labels = import_labels(output / "packets.json", output / "private-map.json", "Reviewer A")
            self.assertEqual(grade_case(case, trial, events, state, labels)["status"], "passed")
            packets[0]["assistant_turns"][0]["final"] = "Tampered evidence"
            (output / "packets.json").write_text(json.dumps(packets))
            with self.assertRaisesRegex(ValueError, "differs"):
                import_labels(output / "packets.json", output / "private-map.json", "Reviewer A")


class StatisticalTests(unittest.TestCase):
    def scores(self):
        return [{"case_id": f"case{i}", "family": f"family{i}", "split": "holdout", "workflow": "brief", "arm": arm, "trial": trial, "status": "passed" if arm == "candidate" else "failed", "outcome_status": "passed" if arm == "candidate" else "failed", "checks": [], "usage": {}, "duration_seconds": 2} for i in range(6) for arm in ("candidate", "baseline") for trial in range(1, 4)]

    def test_paired_case_bootstrap_not_unpaired_trial_resampling(self):
        result = paired_estimate(self.scores(), samples=100)
        self.assertEqual(result["delta"], 1)
        self.assertIsNone(result["interval"])
        self.assertIn("zero variance", result["note"])
        self.assertEqual(result["case_count"], 6)

    def test_pending_or_failed_infrastructure_prevents_selective_estimate(self):
        for state in ("needs_review", "infra_error"):
            scores = self.scores()
            scores[0]["outcome_status"] = state
            self.assertEqual(paired_estimate(scores)["status"], "unavailable")

    def test_unpaired_or_unequal_repeats_rejected(self):
        self.assertEqual(paired_estimate(self.scores()[:-1])["status"], "unavailable")

    def test_small_family_count_suppresses_false_precision(self):
        scores = self.scores()
        for s in scores:
            s["family"] = "one_family"
        self.assertIsNone(paired_estimate(scores)["interval"])

    def test_partial_success_never_release_ready(self):
        _, summary = build_report(self.scores(), {"full_suite": False})
        self.assertEqual(summary["release_gate"], "not_ready")

    def test_full_repeated_reviewed_success_satisfies_defined_gate(self):
        _, summary = build_report(self.scores(), {"full_suite": True})
        self.assertEqual(summary["release_gate"], "passed")

    def test_judge_calibration_counts_false_passes(self):
        human = [{"packet_id": "p", "judgments": [{"criterion": "c1", "pass": False}, {"criterion": "c2", "pass": True}]}]
        model = copy.deepcopy(human)
        model[0]["judgments"][0]["pass"] = True
        result = calibration(human, model)
        self.assertEqual(result["confusion"]["false_pass"], 1)
        self.assertEqual(result["agreement"], .5)
        self.assertEqual(result["status"], "diagnostic_only")


if __name__ == "__main__":
    unittest.main()
