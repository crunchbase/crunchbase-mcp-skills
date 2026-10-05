"""Offline runner contract tests: no model calls, account changes, or live tools."""
from __future__ import annotations

import argparse
import copy
import io
import importlib.util
import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

SPEC = importlib.util.spec_from_file_location("eval_runner", Path(__file__).resolve().parents[1] / "run.py")
runner = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(runner)


def example_case(cid="brief", turns=1):
    return {"id": cid, "family": "company-brief", "split": "dev", "workflow": "company-brief", "tags": ["smoke"],
            "fixture": {"base_data": {"lists": {}}}, "turns": [{"user": f"User message {n}"} for n in range(1, turns + 1)],
            "checks": [{"id": "safe", "kind": "no_write", "severity": "critical"}]}


def example_suite(cases=None):
    return {"schema_version": 1, "id": "test-suite", "as_of": "2026-09-30", "description": "Offline test suite",
            "cases": cases or [example_case()]}


def write_skill(root, name="skill-a"):
    path = root / name / "SKILL.md"
    path.parent.mkdir(parents=True)
    path.write_text(f"---\nname: {name}\ndescription: Read the relevant skill only when its particular description matches the user request.\n---\n\n# An example workflow\nThis sufficiently long instruction proves the file contents were actually read.\n")
    return path


def write_trace(directory, *, final="A completed response", thread="thread-123", failed=False, usage=None):
    directory.mkdir(parents=True, exist_ok=True)
    events = [{"type": "thread.started", "thread_id": thread}, {"type": "turn.started"}]
    if failed:
        events.append({"type": "turn.failed", "error": {"message": "backend unavailable"}})
    else:
        events += [{"type": "item.completed", "item": {"type": "agent_message", "text": final}},
                   {"type": "turn.completed", "usage": usage or {"input_tokens": 100, "cached_input_tokens": 30, "output_tokens": 10}}]
    (directory / "trace.jsonl").write_text("\n".join(json.dumps(e) for e in events) + "\n")
    (directory / "stderr.txt").write_text("")
    if final is not None:
        (directory / "final.txt").write_text(final)


class SuiteValidationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.path = self.root / "suite.json"

    def tearDown(self):
        self.tmp.cleanup()

    def load(self, suite):
        runner.write_json(self.path, suite)
        return runner.load_suite(self.path)

    def test_valid_suite(self):
        self.assertEqual(self.load(example_suite())["id"], "test-suite")

    def test_duplicate_ids_and_unsafe_paths_are_rejected(self):
        for cases in ([example_case(), example_case()], [example_case("../escape")]):
            with self.subTest(cases=cases), self.assertRaises(runner.EvalError):
                self.load(example_suite(cases))

    def test_fake_assistant_turns_are_not_supported(self):
        suite = example_suite()
        suite["cases"][0]["turns"][0]["assistant"] = "fabricated previous response"
        with self.assertRaises(runner.EvalError):
            self.load(suite)

    def test_check_turn_must_exist_and_keys_cannot_be_in_fixture(self):
        for mutation in (lambda c: c["checks"][0].update(turn=2), lambda c: c["fixture"].update(expected_answer="secret")):
            suite = example_suite()
            mutation(suite["cases"][0])
            with self.subTest(suite=suite), self.assertRaises(runner.EvalError):
                self.load(suite)

    def test_holdout_is_excluded_until_explicit_selection(self):
        heldout = example_case("heldout")
        heldout["split"] = "holdout"
        suite = example_suite([example_case(), heldout])
        self.assertEqual([c["id"] for c in runner.select_cases(suite, None, "dev,regression")], ["brief"])
        self.assertEqual(len(runner.select_cases(suite, None, "all")), 2)
        with self.assertRaises(runner.EvalError):
            runner.select_cases(suite, "heldout", "dev,regression")
        with self.assertRaises(runner.EvalError):
            runner.select_cases(suite, "missing", "all")

    def test_families_cannot_cross_dataset_splits(self):
        other = example_case("other")
        other["split"] = "holdout"
        with self.assertRaises(runner.EvalError):
            self.load(example_suite([example_case(), other]))

    def test_kind_specific_requirements_and_typos_fail_closed(self):
        malformed = [
            {"kind": "membership", "entity_ids": []},
            {"kind": "semantic", "rubic": "typo"},
            {"kind": "called", "tool": "cb_reference", "max": 0},
            {"kind": "no_write", "allowed": True},
            {"kind": "activation", "skill": "a", "expected": "false"},
            {"kind": "text_contains", "phrases": []},
        ]
        for check in malformed:
            suite = example_suite()
            suite["cases"][0]["checks"] = [{"id": "invalid", "severity": "critical", **check}]
            with self.subTest(check=check), self.assertRaises(runner.EvalError):
                self.load(suite)

    def test_plan_is_balanced_paired_and_seeded(self):
        cases = [example_case("a"), example_case("b")]
        jobs = runner.make_plan(cases, ["candidate", "baseline", "previous"], 3, 7)
        self.assertEqual(len(jobs), 18)
        self.assertEqual(jobs, runner.make_plan(cases, ["candidate", "baseline", "previous"], 3, 7))
        self.assertNotEqual(jobs, runner.make_plan(cases, ["candidate", "baseline", "previous"], 3, 8))
        for start in range(0, len(jobs), 3):
            block = jobs[start:start + 3]
            self.assertEqual({j["arm"] for j in block}, {"candidate", "baseline", "previous"})
            self.assertEqual(len({(j["case_id"], j["trial"]) for j in block}), 1)
        self.assertEqual(len({j["job_id"] for j in jobs}), 18)

    def test_invalid_plan_cannot_silently_omit_cases(self):
        for arms, repeats in [(["candidate", "candidate"], 1), (["unknown"], 1), (["candidate"], 0)]:
            with self.subTest(arms=arms, repeats=repeats), self.assertRaises(runner.EvalError):
                runner.make_plan([example_case()], arms, repeats, 0)


class IsolationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.skills = self.root / "source"
        write_skill(self.skills)
        write_skill(self.skills, "skill-b")
        self.workspace = self.root / "runtime"

    def tearDown(self):
        self.tmp.cleanup()

    def test_catalog_contains_all_descriptions_without_case_hints(self):
        contents = runner.prepare_workspace(self.workspace, self.skills, "2026-09-30")
        self.assertEqual(set(contents), {"skills/skill-a/SKILL.md", "skills/skill-b/SKILL.md"})
        catalog = (self.workspace / "AGENTS.md").read_text()
        self.assertIn("skill-a", catalog)
        self.assertIn("skill-b", catalog)
        self.assertNotIn("expected", catalog)
        self.assertNotIn("fixture", catalog)
        self.assertEqual({p.name for p in self.workspace.iterdir()}, {"AGENTS.md", "skills"})

    def test_baseline_has_same_general_context_but_no_skills(self):
        contents = runner.prepare_workspace(self.workspace, None, "2026-09-30")
        self.assertEqual(contents, {})
        self.assertEqual({p.name for p in self.workspace.iterdir()}, {"AGENTS.md"})
        self.assertIn("2026-09-30", (self.workspace / "AGENTS.md").read_text())
        self.assertNotIn("Available skills", (self.workspace / "AGENTS.md").read_text())

    def test_symlinked_resources_are_rejected(self):
        (self.skills / "skill-a" / "secret").symlink_to(self.root / "other")
        with self.assertRaises(runner.EvalError):
            runner.prepare_workspace(self.workspace, self.skills, "2026-09-30")

    def command(self, **overrides):
        runner.prepare_workspace(self.workspace, None, "2026-09-30")
        kw = dict(cli="codex", workspace=self.workspace, trial_dir=self.root / "artifacts", fixture=self.root / "fixture.json",
                  server=self.root / "server.py", model="configured-model", effort="high", turn=1, thread_id=None,
                  ephemeral=True, protected_paths=[self.root / "artifacts"])
        kw.update(overrides)
        return runner.build_command(**kw)

    def test_command_disables_host_context_and_denies_fixture_artifacts(self):
        command = self.command()
        self.assertIn("--ignore-user-config", command)
        self.assertIn("--ignore-rules", command)
        self.assertIn("--ephemeral", command)
        configs = [command[i + 1] for i, value in enumerate(command[:-1]) if value == "-c"]
        self.assertIn('web_search="disabled"', configs)
        self.assertIn("project_doc_max_bytes=0", configs)
        filesystem = next(v for v in configs if v.startswith("permissions.skill-evaluation.filesystem="))
        self.assertIn('":minimal"="read"', filesystem)
        self.assertIn(str(self.root / "artifacts") + '"="deny"', filesystem)
        self.assertIn('permissions.skill-evaluation.network.enabled=false', configs)
        servers = next(v for v in configs if v.startswith("mcp_servers="))
        self.assertIn("crunchbase_replay", servers)
        self.assertNotIn("http", servers)
        self.assertIn('"default_tools_approval_mode"="approve"', servers)

    def test_resume_uses_same_thread_and_new_server_turn_without_ephemeral(self):
        command = self.command(thread_id="thread-123", ephemeral=False, turn=2)
        self.assertEqual(command[:3], ["codex", "exec", "resume"])
        self.assertNotIn("--ephemeral", command)
        self.assertNotIn("-C", command)
        self.assertEqual(command[-2:], ["thread-123", "-"])
        server = next(value for value in command if value.startswith("mcp_servers="))
        self.assertIn('"--turn","2"', server)

    def test_cannot_place_outputs_inside_runtime(self):
        with self.assertRaises(runner.EvalError):
            self.command(protected_paths=[self.workspace / "answers"])

    def test_explicit_model_does_not_need_user_config(self):
        model, effort, source = runner.resolve_model("pinned-model", "high", self.root / "absent.toml")
        self.assertEqual((model, effort), ("pinned-model", "high"))
        self.assertNotIn("config_path", source)

    def test_configured_model_profile_is_resolved_once(self):
        config = self.root / "config.toml"
        config.write_text('model="old"\nmodel_reasoning_effort="low"\nprofile="test"\n')
        (self.root / "test.config.toml").write_text('model="profile-model"\nmodel_reasoning_effort="xhigh"\n')
        model, effort, source = runner.resolve_model(None, None, config)
        self.assertEqual((model, effort), ("profile-model", "xhigh"))
        self.assertIn("profile_sha256", source)
        with self.assertRaises(runner.EvalError):
            runner.resolve_model(None, None, self.root / "absent.toml")


class TraceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name)
        self.execution = {"returncode": 0, "timed_out": False, "spawn_error": None}

    def tearDown(self):
        self.tmp.cleanup()

    def test_complete_trace_accounts_usage(self):
        write_trace(self.path)
        result = runner.parse_trace(self.path, self.execution)
        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["usage"], {"input_tokens": 100, "cached_input_tokens": 30, "output_tokens": 10})
        self.assertEqual(result["thread_id"], "thread-123")
        self.assertTrue(result["usage_complete"])

    def test_nonzero_timeout_failed_malformed_missing_final_fail_closed(self):
        variations = ["exit", "timeout", "failed", "malformed", "missing_final", "missing_completion"]
        for variation in variations:
            with self.subTest(variation=variation):
                self.execution = {"returncode": 0, "timed_out": False, "spawn_error": None}
                write_trace(self.path, failed=variation == "failed")
                if variation == "exit":
                    self.execution["returncode"] = 2
                elif variation == "timeout":
                    self.execution["timed_out"] = True
                elif variation == "malformed":
                    with (self.path / "trace.jsonl").open("a") as f:
                        f.write("not json\n")
                elif variation == "missing_final":
                    (self.path / "final.txt").unlink()
                elif variation == "missing_completion":
                    (self.path / "trace.jsonl").write_text('{"type":"turn.started"}\n')
                self.assertEqual(runner.parse_trace(self.path, self.execution)["status"], "infra_error")

    def test_builtin_inventory_is_narrowly_allowlisted(self):
        item = {"id": "inventory", "type": "mcp_tool_call", "server": "codex", "tool": "list_mcp_resources", "arguments": {}, "status": "completed", "error": None, "result": {"content": [{"type": "text", "text": '{"resources":[]}'}]}}
        for changes, expected in [({}, "completed"), ({"tool": "read_mcp_resource"}, "infra_error"), ({"arguments": {"server": "external"}}, "infra_error"), ({"result": {"structured_content": {"resources": [{"uri": "secret"}]}}}, "infra_error"), ({"status": "in_progress", "result": None}, "infra_error")]:
            with self.subTest(changes=changes):
                write_trace(self.path)
                with (self.path / "trace.jsonl").open("a") as output:
                    output.write(json.dumps({"type": "item.completed", "item": {**item, **changes}}) + "\n")
                self.assertEqual(runner.parse_trace(self.path, self.execution)["status"], expected)

    def test_assistant_claims_do_not_count_as_skill_activation(self):
        rel = "skills/skill-a/SKILL.md"
        body = "An instruction long enough to provide evidence of a real file content read."
        events = [{"type": "item.completed", "item": {"type": "agent_message", "text": f"I read {rel}: {body}"}}]
        self.assertEqual(runner.extract_skill_reads(events, {rel: body}, self.path), [])
        events.append({"type": "item.completed", "item": {"type": "command_execution", "command": "cat " + rel,
                      "exit_code": 0, "aggregated_output": body}})
        self.assertEqual(runner.extract_skill_reads(events, {rel: body}, self.path), [rel])
        events[-1]["item"]["command"] = "echo " + rel
        self.assertEqual(runner.extract_skill_reads(events, {rel: body}, self.path), [])

    def test_rg_and_cwd_relative_reads_are_observable(self):
        rel = "skills/skill-a/SKILL.md"
        body = "name: skill-a\nA long instruction that has enough concrete content to establish an actual read."
        for command in ("rg -n . skills/skill-a/SKILL.md", "cd skills/skill-a && cat SKILL.md", "cat SKILL.md"):
            events = [{"type": "item.completed", "item": {"type": "command_execution", "command": command,
                "exit_code": 0, "aggregated_output": "1:name: skill-a\n2:" + body.splitlines()[1]}}]
            with self.subTest(command=command):
                self.assertEqual(runner.extract_skill_reads(events, {rel: body}, self.path), [rel])

    def test_opaque_skill_read_is_unknown_not_a_negative_activation_pass(self):
        events = [{"type": "item.completed", "item": {"type": "command_execution", "command": "cat SKILL.md",
            "exit_code": 0, "aggregated_output": "[output truncated]"}}]
        self.assertIsNone(runner.extract_skill_reads(events, {"skills/a/SKILL.md": "secret instructions"}, self.path))

    def test_mcp_result_envelopes_are_normalized_for_grading(self):
        result = {"error": {"code": "VALIDATION_ERROR", "message": "wrong field"}}
        self.assertEqual(runner.normalize_tool_result({"structuredContent": result}), result)
        self.assertEqual(runner.normalize_tool_result({"content": [{"type": "text", "text": json.dumps(result)}]}), result)
        self.assertEqual(runner.normalize_tool_result({"content": [{"type": "text", "text": "not JSON"}]}), {"content": [{"type": "text", "text": "not JSON"}]})

    def test_fixture_approval_block_is_infrastructure_error(self):
        write_trace(self.path)
        with (self.path / "trace.jsonl").open("a") as output:
            output.write(json.dumps({"type": "item.completed", "item": {"type": "mcp_tool_call", "server": "crunchbase_replay", "tool": "cb_reference", "error": {"message": "MCP tool call requires approval, but approval policy is never"}}}) + "\n")
        result = runner.parse_trace(self.path, self.execution)
        self.assertEqual(result["status"], "infra_error")
        self.assertIn("infrastructure failure", result["error"])

    def test_reading_references_does_not_erase_proven_skill_activation(self):
        rel = "skills/skill-a/SKILL.md"
        body = "name: skill-a\nA long instruction that has enough concrete content to establish an actual read."
        events = [
            {"type": "item.completed", "item": {"type": "command_execution", "command": "cat " + rel, "exit_code": 0, "aggregated_output": body}},
            {"type": "item.completed", "item": {"type": "command_execution", "command": "cat skills/skill-a/references/rules.md", "exit_code": 0, "aggregated_output": "Reference instructions"}},
        ]
        self.assertEqual(runner.extract_skill_reads(events, {rel: body}, self.path), [rel])

    def test_timeline_preserves_preview_before_attempt_and_client_failure(self):
        events = [
            {"type": "item.completed", "item": {"id": "m1", "type": "agent_message", "text": "I will add A to List B."}},
            {"type": "item.started", "item": {"id": "call", "type": "mcp_tool_call", "server": "crunchbase_replay", "tool": "cb_list_add_entities", "arguments": {"entity_ids": ["A"]}}},
            {"type": "item.completed", "item": {"id": "call", "type": "mcp_tool_call", "server": "crunchbase_replay", "tool": "cb_list_add_entities", "arguments": {"entity_ids": ["A"]}, "error": {"message": "client rejected schema"}}},
        ]
        result = runner.extract_timeline(events, 2)
        self.assertEqual([e["type"] for e in result["timeline"]], ["message", "tool_call"])
        self.assertEqual(len(result["tool_attempts"]), 1)
        self.assertEqual(result["tool_attempts"][0]["turn"], 2)
        self.assertEqual(result["tool_attempts"][0]["error"], {"message": "client rejected schema"})

    @patch.object(runner.os, "killpg")
    def test_timeout_kills_entire_process_group(self, killpg):
        if os.name != "posix":
            self.skipTest("POSIX process group behavior")
        proc = Mock()
        proc.pid = 4321
        proc.returncode = -9
        proc.communicate.side_effect = [subprocess.TimeoutExpired("codex", 1), None, None]
        with patch.object(runner.subprocess, "Popen", return_value=proc) as popen:
            result = runner.execute_command(["codex", "exec"], "hello", self.path / "turn", self.path, 1)
        self.assertTrue(result["timed_out"])
        self.assertTrue(popen.call_args.kwargs["start_new_session"])
        self.assertEqual(killpg.call_count, 2)
        self.assertEqual(killpg.call_args_list[-1].args, (4321, runner.signal.SIGKILL))

    def test_spawn_failure_is_preserved(self):
        with patch.object(runner.subprocess, "Popen", side_effect=OSError("missing executable")):
            execution = runner.execute_command(["absent"], "hello", self.path, self.path, 1)
        self.assertIn("missing executable", execution["spawn_error"])
        self.assertEqual(runner.parse_trace(self.path, execution)["status"], "infra_error")


class ManifestTests(unittest.TestCase):
    def test_manifest_rejects_links_before_snapshotting_either_arm(self):
        for arm in ("skills", "previous_skills"):
            for kind in ("file", "directory", "dangling", "root"):
                with self.subTest(arm=arm, kind=kind), tempfile.TemporaryDirectory() as temporary:
                    root = Path(temporary)
                    candidate, previous = root / "candidate", root / "previous"
                    write_skill(candidate)
                    write_skill(previous)
                    external = root / "external"
                    external.mkdir()
                    (external / "secret").write_text("must not be copied")
                    selected = candidate if arm == "skills" else previous
                    if kind == "root":
                        link = root / "linked-root"
                        link.symlink_to(selected, target_is_directory=True)
                        if arm == "skills":
                            candidate = link
                        else:
                            previous = link
                    else:
                        target = external if kind == "directory" else external / ("missing" if kind == "dangling" else "secret")
                        (selected / "skill-a" / "resource").symlink_to(target)
                    args = argparse.Namespace(skills=candidate, previous_skills=previous)
                    run_dir = root / "run"
                    run_dir.mkdir()
                    with self.assertRaisesRegex(runner.EvalError, "symlinks"):
                        runner.create_manifest(args, example_suite(), root / "suite.json", [], "model", "high", {}, run_dir)
                    self.assertEqual(list(run_dir.iterdir()), [])

    def test_inputs_are_frozen_and_full_suite_is_explicit(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "evals").mkdir()
            (root / "evals/replay_server.py").write_text("# frozen server\n")
            skills = root / "skills"
            skill = write_skill(skills)
            suite_path = root / "suite.json"
            suite = example_suite()
            runner.write_json(suite_path, suite)
            run_dir = root / "run"
            run_dir.mkdir()
            args = argparse.Namespace(skills=skills, previous_skills=None, codex="codex", case=None,
                seed=3, repeats=1, arms="candidate,baseline", timeout=60, jobs=2)
            jobs = runner.make_plan(suite["cases"], ["candidate", "baseline"], 1, 3)
            with patch.object(runner, "ROOT", root), patch.object(runner.subprocess, "run", return_value=Mock(stdout="codex test")):
                manifest = runner.create_manifest(args, suite, suite_path, jobs, "model", "high", {}, run_dir)
            self.assertTrue(manifest["full_suite"])
            frozen_skill = run_dir / "inputs/candidate-skills/skill-a/SKILL.md"
            digest = runner.file_hash(frozen_skill)
            skill.write_text("changed source after freeze")
            self.assertEqual(runner.file_hash(frozen_skill), digest)
            self.assertEqual(manifest["candidate_skill_sha256"]["skill-a/SKILL.md"], digest)
            self.assertEqual(runner.read_json(run_dir / "inputs/fixtures/brief.json")["base_data"], {"lists": {}})
            self.assertEqual(manifest["suite_sha256"], runner.file_hash(run_dir / "suite.json"))
            self.assertEqual(manifest["jobs"], jobs)

    def test_plan_never_launches_a_model_or_server(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            skills = root / "skills"
            write_skill(skills)
            suite_path = root / "suite.json"
            runner.write_json(suite_path, example_suite())
            stdout = io.StringIO()
            with patch.object(runner.subprocess, "Popen") as popen, patch.object(runner.subprocess, "run") as run, patch.object(runner.sys, "stdout", stdout):
                status = runner.main(["plan", "--suite", str(suite_path), "--skills", str(skills), "--model", "pinned", "--effort", "high", "--repeats", "2"])
            self.assertEqual(status, 0)
            self.assertEqual(json.loads(stdout.getvalue())["trials"], 4)
            popen.assert_not_called()
            run.assert_not_called()


class TrialTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.skills = self.root / "skills"
        write_skill(self.skills)
        self.case = example_case(turns=2)
        self.job = runner.make_plan([self.case], ["candidate"], 1, 0)[0]
        self.run_dir = self.root / "run"
        self.run_dir.mkdir()
        self.manifest = {"model": "configured-model", "reasoning_effort": "high", "suite_sha256": "suite-hash",
                         "candidate_skill_sha256": runner.tree_hashes(self.skills), "as_of": "2026-09-30"}
        runner.write_json(self.run_dir / "manifest.json", self.manifest)

    def tearDown(self):
        self.tmp.cleanup()

    def trial(self):
        return runner.run_trial(self.job, self.case, self.run_dir, self.manifest, self.root / "suite.json", self.skills,
                                None, self.root / "server.py", "codex", 1)

    def test_multiturn_resumes_real_thread_and_preserves_state_and_usage(self):
        calls = []
        def fake_execute(command, prompt, directory, workspace, timeout):
            calls.append((command, prompt))
            state = directory.parents[1] / "state.json"
            if len(calls) == 1:
                runner.write_json(state, {"lists": {"fixture-list": {"name": "test", "entity_ids": ["company-a"]}}})
            else:
                self.assertEqual(runner.read_json(state)["lists"]["fixture-list"]["entity_ids"], ["company-a"])
            write_trace(directory)
            return {"duration_seconds": 0.1, "returncode": 0, "timed_out": False, "spawn_error": None}
        with patch.object(runner, "execute_command", side_effect=fake_execute):
            result = self.trial()
        self.assertEqual(result["status"], "completed")
        self.assertEqual([prompt for _, prompt in calls], [t["user"] for t in self.case["turns"]])
        self.assertEqual(calls[1][0][:3], ["codex", "exec", "resume"])
        self.assertIn("thread-123", calls[1][0])
        self.assertNotIn("--ephemeral", calls[0][0] + calls[1][0])
        self.assertEqual(result["usage"]["input_tokens"], 200)
        self.assertEqual(result["cost_proxy"]["uncached_input_tokens"], 140)
        self.assertEqual(len(result["turns"]), 2)

    def test_failure_stops_later_turns_and_is_not_scored_as_success(self):
        def fake_execute(command, prompt, directory, workspace, timeout):
            write_trace(directory, failed=True)
            return {"duration_seconds": 0.1, "returncode": 1, "timed_out": False, "spawn_error": None}
        with patch.object(runner, "execute_command", side_effect=fake_execute) as execute:
            result = self.trial()
        self.assertEqual(execute.call_count, 1)
        self.assertEqual(result["status"], "infra_error")
        self.assertFalse(result["usage_complete"])
        self.assertFalse(result["cost_proxy"]["complete"])
        self.assertTrue((self.run_dir / self.job["path"] / "trial.json").exists())

    def test_changed_thread_id_is_infrastructure_failure(self):
        count = 0
        def fake_execute(command, prompt, directory, workspace, timeout):
            nonlocal count
            count += 1
            write_trace(directory, thread=f"thread-{count}")
            return {"duration_seconds": 0.1, "returncode": 0, "timed_out": False, "spawn_error": None}
        with patch.object(runner, "execute_command", side_effect=fake_execute):
            result = self.trial()
        self.assertEqual(result["status"], "infra_error")
        self.assertIn("different thread", result["error"])


if __name__ == "__main__":
    unittest.main()
