"""Independent evidence-integrity tests; no agent/provider calls."""
import copy
import json
import tempfile
import unittest
from pathlib import Path
from evals import artifacts_io as artifacts, run, grade


class EvidenceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.work = self.root / 'work'
        self.work.mkdir()
        self.out = self.root / 'captured'

    def tearDown(self):
        self.tmp.cleanup()

    def test_intel_ambiguity_has_equally_named_distinct_companies(self):
        from evals.replay_server import Replay
        path = Path(__file__).parents[1] / 'suites/gtm/suite.json'
        case = next(c for c in run.load_suite(path)['cases'] if c['id'] == 'intel-ambiguous-name')
        replay = Replay(run.materialize_fixture(case, path))
        result = replay.expert_resolve_entity('Lumenquill', cb_entity_get=None)
        candidates = result['disambiguation']['candidates']
        self.assertEqual(len(candidates), 2)
        self.assertEqual({r['identifier']['value'] for r in candidates}, {'Lumenquill'})
        self.assertEqual(len({r['identifier']['uuid'] for r in candidates}), 2)
        self.assertEqual(len({r['url'] for r in candidates}), 2)
        self.assertIn('Austin', candidates[0]['short_description'])
        self.assertIn('Boston', candidates[1]['short_description'])
        self.assertNotIn('accounts.csv', [a['path'] for a in case['attachments']])

    def test_pulse_pagination_retains_reviewable_output_chain(self):
        path = Path(__file__).parents[1] / 'suites/gtm/suite.json'
        case = next(c for c in run.load_suite(path)['cases'] if c['id'] == 'pulse-301-page')
        expected = {'pulse-result.json', 'events.json', 'coverage.json', 'accounts.json'}
        self.assertEqual({a['path'] for a in case['artifacts']}, expected)
        self.assertEqual({c['path'] for c in case['checks'] if c['kind'] == 'artifact_json'}, expected - {'events.json'})
        self.assertIn('pulse-artifact-contract.md', case['turns'][0]['user'])
        contract = next(a['content'] for a in case['attachments'] if a['path'] == 'pulse-artifact-contract.md')
        self.assertIn('No numeric rank or score is required', contract)

    def test_clock_advance_replaces_stale_date_and_notifies_resume(self):
        (self.work / 'AGENTS.md').write_text('Current controlled evaluation date: 2026-11-05. Initial clock.\nOther instructions\n')
        notice = run.advance_clock(self.work, '2026-11-06')
        text = (self.work / 'AGENTS.md').read_text()
        self.assertNotIn('2026-11-05', text)
        self.assertEqual(text.count('Current controlled evaluation date:'), 1)
        self.assertIn('2026-11-06', notice)
        self.assertIn('supersedes', notice)
        self.assertIn('Other instructions', text)
        suite = run.load_suite(Path(__file__).parents[1] / 'suites/gtm/suite.json')
        self.assertNotIn('Use November 5', suite['context'])
        case = next(c for c in suite['cases'] if c['id'] == 'pulse-new-observation')
        self.assertEqual(case['fixture_updates'][0]['as_of'], '2026-11-06')
        self.assertTrue(any(c.get('expected', {}).get('as_of') == '2026-11-06' for c in case['checks'] if isinstance(c.get('expected'), dict)))

    def test_arm_scoped_procedure_is_not_a_baseline_outcome_failure(self):
        check = {'id': 'procedure', 'kind': 'not_called', 'severity': 'critical', 'tools': ['cb_search_query'], 'arms': ['candidate']}
        run.validate_check(check, 'a')
        case = {'id': 'a', 'family': 'a', 'split': 'dev', 'workflow': 'a', 'checks': [check, {'id': 'safe', 'kind': 'no_write', 'severity': 'critical'}]}
        trial = {'arm': 'baseline', 'trial': 1, 'status': 'completed', 'turns': []}
        events = [{'tool': 'cb_search_query'}]
        result = grade.grade_case(case, trial, events, {})
        self.assertEqual(result['status'], 'passed')
        self.assertEqual(result['checks'][0]['status'], 'not_applicable')
        trial['arm'] = 'candidate'
        self.assertEqual(grade.grade_case(case, trial, events, {})['status'], 'failed')
        for arms in ([], ['other'], ['candidate', 'candidate'], 'candidate'):
            with self.assertRaises(run.EvalError): run.validate_check({**check, 'arms': arms}, 'a')
        case['checks'] = [check]
        trial['arm'] = 'baseline'
        self.assertEqual(grade.grade_case(case, trial, events, {})['status'], 'needs_review')

    def test_repair_contracts_are_shared_and_missing_inputs_are_missing(self):
        suite = run.load_suite(Path(__file__).parents[1] / 'suites/gtm/suite.json')
        cases = {c['id']: c for c in suite['cases']}
        self.assertEqual(cases['priority-duplicate-book']['split'], 'regression')
        self.assertIn('one row per unique canonical company UUID', cases['priority-duplicate-book']['turns'][0]['user'])
        radar = cases['radar-complete-normalized']
        self.assertIn('radar-input-contract.md', radar['turns'][0]['user'])
        self.assertTrue(any(a['path'] == 'radar-input-contract.md' and 'organization_uuid' in a['content'] for a in radar['attachments']))
        for cid in ('account-signals-missing', 'account-prioritizer-missing', 'prospect-finder-missing', 'industry-insights-missing'):
            case = cases[cid]
            self.assertFalse({'accounts.csv', 'accounts.json'} & {a['path'] for a in case['attachments']})
            self.assertEqual(next(c for c in case['checks'] if c['id'] == 'no-data')['arms'], ['candidate'])
            self.assertNotIn('arms', next(c for c in case['checks'] if c['id'] == 'outcome'))
        for suffix in ('accept-icp', 'supply-seed'):
            case = cases['prospect-missing-seed-' + suffix]
            self.assertEqual(len(case['turns']), 2)
            self.assertTrue(any(a['path'] == 'accepted-scoring-policy.md' for a in case['attachments']))
            self.assertEqual(next(c for c in case['checks'] if c['id'] == 'no-data')['turn'], 1)
            self.assertEqual(next(c for c in case['checks'] if c['id'] == 'followup-outcome')['turn'], 2)

    def test_each_public_radar_case_discloses_its_own_input_contract(self):
        suite = run.load_suite(Path(__file__).parents[1] / 'suites/gtm/suite.json')
        for cid in ('radar-complete-retrieval', 'radar-complete-normalized', 'radar-insufficient-artifact'):
            case = next(c for c in suite['cases'] if c['id'] == cid)
            contract = next(a['content'] for a in case['attachments'] if a['path'] == 'radar-input-contract.md')
            self.assertIn('radar-input-contract.md', case['turns'][0]['user'])
            for field in ('schema_version="crunchbase-industry-insights/1"', 'coverage', 'organizations', 'rounds', 'complete:boolean', 'reported_count', 'organization_uuid', 'segment_ids', 'announced_on', 'money_raised_usd'):
                self.assertIn(field, contract, (cid, field))

    def test_targeted_empty_fixture_and_injection_exposure(self):
        from evals.replay_server import Replay
        path = Path(__file__).parents[1] / 'suites/gtm/suite.json'
        cases = {c['id']: c for c in run.load_suite(path)['cases']}
        replay = Replay(run.materialize_fixture(cases['pulse-empty-events'], path))
        for row in replay.rows('organizations'):
            result = replay.entity_get(row['identifier']['uuid'], card_ids=['funding_rounds_list', 'key_employee_change_list', 'product_launches', 'layoff_list'])
            self.assertTrue(all(not c['entities'] for c in result['cards']))
        case = cases['prospect-hostile-description']
        replay = Replay(run.materialize_fixture(case, path))
        response = replay.expert_resolve_entity('Lumenquill Dental', domains=['fixture-lumenquill-dental.example'], cb_entity_get=None)
        check = next(c for c in case['checks'] if c['id'] == 'payload-exposed')
        self.assertIn(check['text'], json.dumps(response))
        probe = {'id': 'x', 'family': 'x', 'split': 'regression', 'workflow': 'x', 'checks': [check]}
        trial = {'arm': 'baseline', 'trial': 1, 'status': 'completed', 'turns': []}
        self.assertEqual(grade.grade_case(probe, trial, [{'tool': 'cb_expert_resolve_entity', 'result': response}], {})['status'], 'passed')
        self.assertEqual(grade.grade_case(probe, trial, [{'tool': 'cb_expert_resolve_entity', 'arguments': {'text': check['text']}, 'result': {}}], {})['status'], 'failed')
        self.assertEqual(cases['heldout-intel-conflicting-domain']['split'], 'regression')

    def test_paths_cannot_modify_catalog_or_escape(self):
        for path in ('../x', '/x', 'a/../x', 'skills/a/SKILL.md', 'AGENTS.md', 'a\\b', './a', 'a//b', '.eval-bin/python3'):
            with self.subTest(path=path), self.assertRaises(ValueError):
                artifacts.safe_relative(path)
        self.assertEqual(artifacts.safe_relative('outputs/book.csv'), 'outputs/book.csv')

    def test_input_hash_and_capture_are_exact(self):
        hashes = artifacts.stage_attachments(self.work, [{'path': 'book.json', 'content': '{"schema_version":1,"name":"Å"}\n'}])
        records = artifacts.capture_artifacts(self.work, [{'path': 'book.json', 'format': 'json'}], self.out)
        self.assertEqual(records[0]['sha256'], hashes['book.json'])
        self.assertEqual(records[0]['content'], {'schema_version': 1, 'name': 'Å'})
        self.assertEqual((self.out / 'book.json').read_bytes(), (self.work / 'book.json').read_bytes())

    def test_missing_and_invalid_outputs_remain_visible(self):
        (self.work / 'bad.json').write_text('{"score": NaN}')
        records = artifacts.capture_artifacts(self.work, [{'path': 'absent.json', 'format': 'json'}, {'path': 'bad.json', 'format': 'json'}], self.out)
        self.assertEqual([r['status'] for r in records], ['missing', 'invalid'])

    def test_symlinks_are_not_followed(self):
        (self.root / 'secret.json').write_text('{}')
        (self.work / 'out.json').symlink_to(self.root / 'secret.json')
        record = artifacts.capture_artifacts(self.work, [{'path': 'out.json', 'format': 'json'}], self.out)[0]
        self.assertEqual(record['status'], 'invalid')
        self.assertNotIn('content', record)

    def test_oversize_capture_fails_closed(self):
        (self.work / 'out.json').write_bytes(b' ' * (artifacts.MAX_BYTES + 1))
        record = artifacts.capture_artifacts(self.work, [{'path': 'out.json', 'format': 'json'}], self.out)[0]
        self.assertEqual(record['status'], 'invalid')

    def test_csv_escaping_and_exact_identity(self):
        (self.work / 'accounts.csv').write_text('uuid,name,score\nu1,"A, Inc.",0\nu2,"B ""quoted""",\n')
        records = artifacts.capture_artifacts(self.work, [{'path': 'accounts.csv', 'format': 'csv'}], self.out)
        check = {'kind': 'artifact_csv', 'path': 'accounts.csv', 'key': 'uuid', 'values': ['u2', 'u1'], 'columns': ['uuid', 'score'], 'rows': [{'uuid': 'u1', 'score': '0'}, {'uuid': 'u2', 'score': ''}]}
        self.assertTrue(artifacts.check_artifact(check, records)[0])
        check['values'] = ['u1']
        self.assertFalse(artifacts.check_artifact(check, records)[0])

    def test_malformed_csv_and_duplicate_identity_fail(self):
        for text in ('uuid,uuid\nu1,u1\n', 'uuid,name\nu1\n', 'uuid\nu1,x\n'):
            (self.work / 'accounts.csv').write_text(text)
            self.assertEqual(artifacts.capture_artifacts(self.work, [{'path': 'accounts.csv', 'format': 'csv'}], self.out)[0]['status'], 'invalid')
        records = [{'path': 'a.csv', 'format': 'csv', 'status': 'captured', 'columns': ['uuid'], 'content': [{'uuid': 'u1'}, {'uuid': 'u1'}]}]
        self.assertFalse(artifacts.check_artifact({'kind': 'artifact_csv', 'path': 'a.csv', 'key': 'uuid', 'values': ['u1']}, records)[0])

    def test_csv_bom_numeric_values_and_bijective_rows(self):
        (self.work / 'accounts.csv').write_text('UUID,Score\nu1,56.0\nu2,2\n', encoding='utf-8-sig')
        records = artifacts.capture_artifacts(self.work, [{'path': 'accounts.csv', 'format': 'csv'}], self.out)
        self.assertEqual(records[0]['columns'], ['UUID', 'Score'])
        check = {'kind': 'artifact_csv', 'path': 'accounts.csv', 'key': 'UUID', 'values': ['u1', 'u2'], 'rows': [{'UUID': 'u1', 'Score': 56}, {'UUID': 'u2', 'Score': 2}]}
        self.assertTrue(artifacts.check_artifact(check, records)[0])
        check['rows'] = [{'UUID': 'u1'}, {'UUID': 'u1'}]
        self.assertFalse(artifacts.check_artifact(check, records)[0])
        self.assertTrue(artifacts.csv_rows_match([{}, {'UUID': 'u1'}], [{'UUID': 'u1'}, {'UUID': 'u2'}]))
        self.assertFalse(artifacts.csv_row_matches({'Score': 0}, {'Score': ''}))
        self.assertFalse(artifacts.csv_row_matches({'Score': 0}, {'Score': 'NaN'}))

    def test_json_subset_is_typed(self):
        self.assertFalse(artifacts.subset({'score': 0}, {'score': False}))
        self.assertFalse(artifacts.subset({'score': None}, {'score': 0}))
        self.assertTrue(artifacts.subset({'score': None}, {'score': None, 'coverage': 0}))
        self.assertFalse(artifacts.subset([1], [1, 2]))

    def test_changed_artifact_invalidates_human_evidence(self):
        case = {'id': 'a', 'family': 'a', 'split': 'dev', 'workflow': 'a', 'checks': [{'id': 'sem', 'kind': 'semantic', 'severity': 'normal', 'rubric': 'Correct output'}]}
        trial = {'case_id': 'a', 'arm': 'candidate', 'trial': 1, 'status': 'completed', 'turns': [{'turn': 1, 'final': 'Done', 'artifacts': [{'sha256': 'old', 'content': {'score': 0}}]}]}
        digest = grade.evidence_digest(case, trial, [], {})
        label = {'a/candidate/1/sem': {'source': 'human', 'reviewer': 'Reviewer', 'evidence': 'Observed value', 'pass': True, 'evidence_digest': digest}}
        self.assertEqual(grade.grade_case(case, trial, [], {}, label)['status'], 'passed')
        trial['turns'][0]['artifacts'][0]['content']['score'] = 99
        self.assertEqual(grade.grade_case(case, trial, [], {}, label)['status'], 'needs_review')

    def test_state_hash_comparison_requires_two_valid_snapshots(self):
        case = {'id': 'a', 'family': 'a', 'split': 'dev', 'workflow': 'a', 'checks': [{'id': 'stable', 'kind': 'artifact_unchanged', 'severity': 'critical', 'path': 'state.json', 'from_turn': 1, 'turn': 2}]}
        record = {'path': 'state.json', 'status': 'captured', 'sha256': 'abc'}
        trial = {'case_id': 'a', 'arm': 'candidate', 'trial': 1, 'status': 'completed', 'turns': [{'turn': n, 'artifacts': [copy.deepcopy(record)]} for n in (1, 2)]}
        self.assertEqual(grade.grade_case(case, trial, [], {})['status'], 'passed')
        trial['turns'][1]['artifacts'][0]['sha256'] = 'changed'
        self.assertEqual(grade.grade_case(case, trial, [], {})['status'], 'failed')
        trial['turns'][0]['artifacts'] = []
        self.assertEqual(grade.grade_case(case, trial, [], {})['status'], 'failed')

    def test_unallowlisted_output_check_is_rejected(self):
        case = {'id': 'a', 'family': 'a', 'split': 'dev', 'workflow': 'a', 'tags': [], 'fixture': {}, 'turns': [{'user': 'Hello'}], 'checks': [{'id': 'a', 'kind': 'artifact_json', 'severity': 'normal', 'path': 'out.json', 'expected': {}}]}
        suite = {'schema_version': 1, 'id': 'a', 'as_of': '2026-11-05', 'cases': [case]}
        path = self.root / 'suite.json'; path.write_text(json.dumps(suite))
        with self.assertRaises(run.EvalError): run.load_suite(path)
        case['artifacts'] = [{'path': 'out.json', 'format': 'json'}]
        path.write_text(json.dumps(suite)); self.assertEqual(run.load_suite(path)['id'], 'a')

    def test_fixture_transition_validation(self):
        case = {'id': 'a', 'family': 'a', 'split': 'dev', 'workflow': 'a', 'tags': [], 'fixture': {}, 'turns': [{'user': 'First'}, {'user': 'Again'}], 'checks': [{'id': 'a', 'kind': 'no_write', 'severity': 'critical'}], 'fixture_updates': [{'turn': 2, 'as_of': '2026-11-06', 'fixture': {'errors': []}}]}
        suite = {'schema_version': 1, 'id': 'a', 'as_of': '2026-11-05', 'cases': [case]}
        path = self.root / 'suite.json'; path.write_text(json.dumps(suite)); run.load_suite(path)
        case['fixture_updates'][0]['fixture']['expected_answer'] = 'secret'
        path.write_text(json.dumps(suite))
        with self.assertRaises(run.EvalError): run.load_suite(path)

    def test_runner_captures_before_cleanup_and_applies_transition(self):
        from unittest.mock import patch
        case = {'id': 'a', 'family': 'a', 'split': 'dev', 'workflow': 'a', 'tags': [],
                'fixture': {'base_data': {'lists': {}}}, 'turns': [{'user': 'First'}, {'user': 'Second'}],
                'checks': [{'id': 'safe', 'kind': 'no_write', 'severity': 'critical'}],
                'attachments': [{'path': 'input.json', 'content': '{"seller":"billing"}'}],
                'artifacts': [{'path': 'out.json', 'format': 'json'}],
                'fixture_updates': [{'turn': 2, 'as_of': '2026-11-06', 'fixture': {'errors': []}}]}
        suite = {'schema_version': 1, 'id': 'a', 'as_of': '2026-11-05', 'cases': [case]}
        jobs = run.make_plan([case], ['baseline'], 1, 0)
        run_dir = self.root / 'run'; run_dir.mkdir()
        manifest = {'model': 'test', 'reasoning_effort': 'low', 'suite_sha256': '', 'candidate_skill_sha256': {}, 'as_of': '2026-11-05', 'jobs': jobs}
        run.write_json(run_dir / 'suite.json', suite)
        manifest['suite_sha256'] = run.file_hash(run_dir / 'suite.json')
        run.write_json(run_dir / 'manifest.json', manifest)
        calls = []
        def execute(command, prompt, directory, workspace, timeout):
            calls.append(workspace)
            self.assertEqual(json.loads((workspace / 'input.json').read_text()), {'seller': 'billing'})
            if len(calls) == 2:
                self.assertIn('2026-11-06', (workspace / 'AGENTS.md').read_text())
                self.assertEqual(json.loads((workspace / 'out.json').read_text())['step'], 1)
                self.assertEqual(json.loads((directory / 'fixture-before.json').read_text())['errors'], [])
            (workspace / 'out.json').write_text(json.dumps({'step': len(calls)}))
            events = [{'type': 'thread.started', 'thread_id': 't'}, {'type': 'item.completed', 'item': {'type': 'agent_message', 'text': 'done'}}, {'type': 'turn.completed', 'usage': {'input_tokens': 1, 'output_tokens': 1, 'cached_input_tokens': 0}}]
            (directory / 'trace.jsonl').write_text('\n'.join(json.dumps(e) for e in events))
            (directory / 'final.txt').write_text('done'); (directory / 'stderr.txt').write_text('')
            return {'duration_seconds': .1, 'returncode': 0, 'timed_out': False, 'spawn_error': None}
        with patch.object(run, 'execute_command', side_effect=execute), patch.object(run, 'native_skill_isolation', return_value={'disabled_names': ['host-canary']}):
            result = run.run_trial(jobs[0], case, run_dir, manifest, self.root / 'suite.json', self.root / 'skills', None, self.root / 'server.py', 'codex', 1)
        self.assertEqual(result['status'], 'completed', result.get('error'))
        self.assertFalse(calls[0].exists())
        self.assertEqual([t['artifacts'][0]['content']['step'] for t in result['turns']], [1, 2])
        self.assertEqual(grade.load_run(run_dir)[1][0][1]['status'], 'completed')
        trial_dir = run_dir / jobs[0]['path']
        (trial_dir / 'turns/2/artifacts/out.json').write_text('{"step": 999}')
        self.assertEqual(grade.load_run(run_dir)[1][0][1]['status'], 'infra_error')

    def test_provisioned_python_runs_local_imports_without_user_site(self):
        import os, subprocess, sys
        run.provision_python(self.work)
        (self.work / 'sibling.py').write_text('VALUE=56\n')
        (self.work / 'check.py').write_text('import sibling,csv,hashlib,json,sys; print(json.dumps({"value":sibling.VALUE,"digest":hashlib.sha256(b"x").hexdigest(),"no_site":sys.flags.no_site,"ignore_environment":sys.flags.ignore_environment}))')
        env = {'PATH': str(self.work / '.eval-bin') + ':/usr/bin:/bin', 'PYTHONPATH': '/a/path/that/must/not/be/imported'}
        proc = subprocess.run(['python3', 'check.py'], cwd=self.work, env=env, text=True, capture_output=True)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        observed = json.loads(proc.stdout)
        self.assertEqual(observed['value'], 56)
        self.assertEqual(observed['no_site'], 1)
        self.assertEqual(observed['ignore_environment'], 1)
        (self.work / 'AGENTS.md').write_text('Test context')
        protected = self.root / 'controller'
        from unittest.mock import patch
        with patch.object(run, 'native_skill_isolation', return_value={'disabled_names': ['host-canary']}):
            cmd = run.build_command(cli='codex', workspace=self.work, trial_dir=protected, fixture=protected/'f.json', server=protected/'server.py', model='test', effort='low', turn=1, thread_id=None, ephemeral=True, protected_paths=[protected])
        config = '\n'.join(cmd)
        self.assertIn(str(Path(sys.executable).resolve()), config)
        self.assertIn(str(protected) + '\"=\"deny\"', config)
        self.assertIn(str(self.work / '.eval-bin'), config)

    def test_happy_scoring_cases_preserve_complete_evidence_and_shared_contract(self):
        path = Path(__file__).parents[1] / 'suites/gtm/suite.json'
        suite = run.load_suite(path)
        for cid, result in (('prospect-finder-happy', 'prospects'), ('account-prioritizer-happy', 'priorities')):
            case = next(c for c in suite['cases'] if c['id'] == cid)
            with self.subTest(case=cid):
                self.assertTrue({'candidates.json', result+'.json', result+'.csv'} <= {a['path'] for a in case['artifacts']})
                inputs = {a['path']: a['content'] for a in case['attachments']}
                self.assertIn('Default fixed weights', inputs['accepted-scoring-policy.md'])
                self.assertIn('both implementations', inputs['scoring-artifact-contract.md'])
                self.assertTrue(any(c['kind'] == 'semantic' and c['id'] == 'source-to-output' for c in case['checks']))
                # A final answer cannot pass required evidence checks when the workspace outputs are absent.
                trial = {'case_id': cid, 'arm': 'candidate', 'trial': 1, 'status': 'completed', 'turns': [{'turn': 1, 'final': 'Everything is correct.', 'artifacts': []}]}
                scored = grade.grade_case(case, trial, [], {})
                expected = {'normalized-input', 'lossless-result', 'final-csv-contract'}
                self.assertEqual({c['id'] for c in scored['checks'] if c['id'] in expected and c['status'] == 'failed'}, expected)

    def test_linked_scoring_capture_keeps_final_enriched_csv_and_input_hash(self):
        files = {'candidates.json': '{"schema_version":1,"candidates":[{"uuid":"u1","heat_score":20}]}',
                 'result.json': '{"schema_version":1,"rows":[{"uuid":"u1","score":56}]}',
                 'result.csv': 'UUID,Score\nu1,56\n'}
        artifacts.stage_attachments(self.work, [{'path': k, 'content': v} for k, v in files.items()])
        # A legitimate final enrichment occurs after the initial export; capture must retain this version.
        (self.work / 'result.csv').write_text('UUID,Score,Hypothesis\nu1,56,Needs validation\n', encoding='utf-8-sig')
        specs = [{'path': k, 'format': 'csv' if k.endswith('.csv') else 'json'} for k in files]
        records = artifacts.capture_artifacts(self.work, specs, self.out)
        self.assertEqual(len(records), 3)
        self.assertTrue(all(r['status'] == 'captured' for r in records))
        csv_record = next(r for r in records if r['path'] == 'result.csv')
        self.assertEqual(csv_record['content'][0]['Hypothesis'], 'Needs validation')
        case = {'id': 'a'}
        trial = {'turns': [{'turn': 1, 'artifacts': records}]}
        before = grade.evidence_digest(case, trial, [], {})
        next(r for r in records if r['path'] == 'candidates.json')['content']['candidates'][0]['heat_score'] = 0
        self.assertNotEqual(before, grade.evidence_digest(case, trial, [], {}))

    def test_fixture_base_enums_match_exposed_contracts(self):
        for name in ('private-company-research', 'gtm', 'cross-collection'):
            path = Path(__file__).parents[1] / 'suites' / name / 'suite.json'
            suite = run.load_suite(path)
            for case in suite['cases']:
                with self.subTest(suite=name, case=case['id']):
                    run.validate_fixture_enums(run.materialize_fixture(case, path)['base_data'])
        malformed = {'entities': {'organizations': [{'identifier': {'uuid': 'a'}, 'operating_status': 'active'}]}, 'contracts': {'organizations': {'operating_status': {'enum_values': ['operating', 'closed']}}}}
        with self.assertRaisesRegex(run.EvalError, 'outside its declared enum'):
            run.validate_fixture_enums(malformed)
        malformed['entities']['organizations'][0]['operating_status'] = 'operating'
        run.validate_fixture_enums(malformed)

    def test_resolver_order_checks_actual_target_and_completion(self):
        check = {'id': 'order', 'kind': 'tool_before', 'severity': 'critical', 'tool': 'cb_expert_resolve_entity', 'before_tools': ['cb_search_query', 'cb_entity_get'], 'argument_contains': {'name': 'Lumenquill'}}
        case = {'id': 'a', 'family': 'a', 'split': 'dev', 'workflow': 'a', 'checks': [check]}
        def score(calls):
            trial = {'case_id': 'a', 'arm': 'candidate', 'trial': 1, 'status': 'completed', 'turns': [{'turn': 1, 'timeline': calls}]}
            return grade.grade_case(case, trial, [], {})['checks'][0]['status']
        resolver = {'type': 'tool_call', 'tool': 'cb_expert_resolve_entity', 'arguments': {'name': 'Lumenquill Dental'}, 'event_index': 2, 'completed_event_index': 4}
        search = {'type': 'tool_call', 'tool': 'cb_search_query', 'arguments': {}, 'event_index': 5, 'completed_event_index': 6}
        metadata = {'type': 'tool_call', 'tool': 'cb_reference', 'arguments': {}, 'event_index': 0, 'completed_event_index': 1}
        self.assertEqual(score([metadata, resolver, search]), 'passed')
        self.assertEqual(score([search]), 'failed')
        self.assertEqual(score([dict(resolver, arguments={'name': 'Other company'}), search]), 'failed')
        self.assertEqual(score([dict(resolver, event_index=8, completed_event_index=9), search]), 'failed')
        self.assertEqual(score([resolver, dict(search, event_index=3)]), 'failed')
        self.assertEqual(score([dict(resolver, result={'error': {'code': 'RESOLVER_UNAVAILABLE'}}), search]), 'passed')
        old = dict(resolver); old.pop('completed_event_index')
        self.assertEqual(score([old, search]), 'needs_review')

    def test_tool_before_schema_and_trace_completion(self):
        check = {'id': 'order', 'kind': 'tool_before', 'severity': 'normal', 'tool': 'resolve', 'before_tools': ['search'], 'argument_contains': {'name': 'Target'}}
        run.validate_check(check, 'test')
        for changed in ({'before_tools': []}, {'before_tools': ['resolve']}, {'argument_contains': {'name': 1}}):
            with self.subTest(changed=changed), self.assertRaises(run.EvalError):
                run.validate_check({**check, **changed}, 'test')
        item = {'id': 't1', 'type': 'mcp_tool_call', 'tool': 'cb_expert_resolve_entity', 'arguments': {'name': 'Target'}}
        observed = run.extract_timeline([{'type': 'item.started', 'item': item}, {'type': 'item.completed', 'item': {**item, 'status': 'completed', 'result': {}}}], 1)
        self.assertEqual(observed['timeline'][0]['event_index'], 0)
        self.assertEqual(observed['timeline'][0]['completed_event_index'], 1)

    def test_search_envelopes_are_explicit_and_preserve_pagination(self):
        from evals.replay_server import Replay
        data = json.loads((Path(__file__).parents[1] / 'suites/gtm/base_data.json').read_text())
        args = {'collection_id': 'products', 'field_ids': ['identifier', 'description'], 'limit': 1}
        nested = Replay({'base_data': data}).call('cb_search_query', args)
        row = nested['entities'][0]
        self.assertEqual(set(row), {'uuid', 'value', 'properties'})
        self.assertEqual(set(row['properties']), {'identifier', 'description'})
        self.assertEqual(row['uuid'], row['properties']['identifier']['uuid'])
        legacy = Replay({'base_data': data, 'search_envelope': 'flat'}).call('cb_search_query', args)
        self.assertNotIn('properties', legacy['entities'][0])
        self.assertEqual(legacy['entities'][0]['description'], row['properties']['description'])
        self.assertEqual(legacy['count'], nested['count'])
        next_nested = Replay({'base_data': data}).call('cb_search_query', {**args, 'after_id': row['uuid']})
        self.assertNotEqual(next_nested['entities'][0]['uuid'], row['uuid'])
        research = Replay().call('cb_search_query', {'collection_id': 'organizations', 'field_ids': ['identifier'], 'limit': 1})
        self.assertIn('identifier', research['entities'][0])
        self.assertNotIn('properties', research['entities'][0])
        invalid = Replay({'base_data': data, 'search_envelope': 'typo'}).call('cb_search_query', args)
        self.assertEqual(invalid['error']['code'], 'VALIDATION_ERROR')

    def test_gtm_collections_are_explicit_and_paginated(self):
        from evals.replay_server import Replay
        data = json.loads((Path(__file__).parents[1] / 'suites/gtm/base_data.json').read_text())
        replay = Replay({'base_data': data, 'page_size': 1})
        first = replay.call('cb_search_query', {'collection_id': 'products', 'field_ids': ['identifier', 'organization', 'description'], 'limit': 300})
        self.assertEqual(first['count'], 3)
        self.assertEqual(len(first['entities']), 1)
        second = replay.call('cb_search_query', {'collection_id': 'products', 'field_ids': ['identifier'], 'limit': 300, 'after_id': first['entities'][0]['uuid']})
        self.assertNotEqual(first['entities'][0]['uuid'], second['entities'][0]['uuid'])
        unsupported = replay.call('cb_search_query', {'collection_id': 'invented_records'})
        self.assertEqual(unsupported['error']['code'], 'VALIDATION_ERROR')
        invalid = replay.call('cb_search_query', {'collection_id': 'products', 'field_ids': ['invented_field']})
        self.assertEqual(invalid['error']['code'], 'VALIDATION_ERROR')


if __name__ == '__main__':
    unittest.main()
