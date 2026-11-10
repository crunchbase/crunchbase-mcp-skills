"""Bounded export-capture closure: no agent trials, source edits, or human labels."""
import json
import tempfile
import unittest
from pathlib import Path

from evals import artifacts_io, run

SUITE = Path(__file__).parents[1] / 'suites/gtm/suite.json'
NORMAL = {
    'prospect-hostile-description': (1, 'prospects'),
    'prospect-missing-seed-accept-icp': (2, 'prospects'),
    'prospect-missing-seed-supply-seed': (2, 'prospects'),
    'account-prioritizer-followup': (2, 'priorities'),
    'priority-null-factor': (1, 'priorities'),
    'priority-duplicate-book': (1, 'priorities'),
}
BLOCKED = {'prospect-finder-access-failure': 'prospects',
           'account-prioritizer-access-failure': 'priorities'}
RADAR = {'industry-insights-happy', 'heldout-radar-overlap'}


class CaptureCoverageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cases = {c['id']: c for c in run.load_suite(SUITE)['cases']}

    def assert_captured_on_turn(self, case, paths, turn):
        self.assertEqual({a['path'] for a in case['artifacts']}, paths)
        for path in paths:
            checks = [c for c in case['checks'] if c.get('path') == path
                      and c['kind'] in {'artifact_csv', 'artifact_json'}]
            self.assertTrue(checks, (case['id'], path))
            self.assertTrue(any(c.get('turn', 1) == turn and 'arms' not in c
                                for c in checks), (case['id'], path))
            self.assertIn(path, case['turns'][turn - 1]['user'])
        if turn > 1:
            self.assertFalse(any(c['kind'].startswith('artifact_') and c.get('turn', 1) < turn
                                 for c in case['checks']))
            self.assertNotIn('Save', case['turns'][0]['user'])

    def test_scored_exports_are_captured_at_delivery_with_shared_policy(self):
        for cid, (turn, stem) in NORMAL.items():
            case = self.cases[cid]
            self.assert_captured_on_turn(case, {'candidates.json', stem + '.json', stem + '.csv'}, turn)
            attached = {a['path']: a['content'] for a in case['attachments']}
            self.assertIn('scoring-artifact-contract.md', attached)
            self.assertIn('Default fixed weights are growth 40%', attached['accepted-scoring-policy.md'])
            self.assertIn('unknown', attached['scoring-artifact-contract.md'].lower())
            self.assertTrue(any(c['id'] == 'capture-final-correspondence' and c['severity'] == 'critical'
                                and c.get('turn') == turn and 'arms' not in c for c in case['checks']))

    def test_blocked_exports_do_not_require_invented_normalized_candidates(self):
        for cid, stem in BLOCKED.items():
            case = self.cases[cid]
            self.assert_captured_on_turn(case, {stem + '.json', stem + '.csv'}, 1)
            contract = next(a['content'] for a in case['attachments'] if a['path'] == 'blocked-export-contract.md')
            for phrase in ('headers only', 'user-provided identifiers', 'input_identity_verified=false',
                           'Score/Tier/Rank are blank', 'No normalized scoring candidates file is required'):
                self.assertIn(phrase, contract)
            check = next(c for c in case['checks'] if c.get('path') == stem + '.json')
            self.assertFalse(check['expected']['complete'])
            self.assertFalse(check['expected']['input_identity_verified'])
            self.assertEqual(check['expected']['status'], 'blocked')

    def test_radar_chain_retained_and_inspected_holdout_retired(self):
        for cid in RADAR:
            case = self.cases[cid]
            self.assert_captured_on_turn(case, {'source-records.json', 'radar-input.json',
                'radar-out/result.json', 'radar-out/segments.csv', 'radar-out/handoff.json'}, 1)
            attachments = {a['path'] for a in case['attachments']}
            self.assertTrue({'radar-policy.md', 'radar-input-contract.md'} <= attachments)
            self.assertNotEqual(case['split'], 'holdout')
        self.assertEqual(self.cases['heldout-radar-overlap']['split'], 'regression')

    def test_existing_insufficient_radar_captures_its_policy_requested_csv(self):
        case = self.cases['radar-insufficient-artifact']
        self.assert_captured_on_turn(case, {'radar-input.json', 'radar-out/result.json',
            'radar-out/handoff.json', 'radar-out/segments.csv'}, 1)
        self.assertTrue(any(c.get('path') == 'radar-out/segments.csv'
                            and c['kind'] == 'artifact_csv' and 'arms' not in c for c in case['checks']))

    def test_clarification_and_prose_only_tasks_do_not_acquire_export_requirements(self):
        for cid in ('prospect-finder-missing', 'account-prioritizer-missing', 'industry-insights-missing',
                    'heldout-prospect-no-seller', 'industry-insights-access-failure', 'account-brief-happy',
                    'account-signals-happy'):
            case = self.cases[cid]
            self.assertFalse(case.get('artifacts'), cid)
            self.assertFalse(any(c['kind'].startswith('artifact_') for c in case['checks']), cid)

    def test_new_allowlists_record_absent_files_instead_of_accepting_link_claims(self):
        for cid in set(NORMAL) | set(BLOCKED) | RADAR | {'radar-insufficient-artifact'}:
            case = self.cases[cid]
            with tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                work = root / 'work'
                work.mkdir()
                records = artifacts_io.capture_artifacts(work, case['artifacts'], root / 'captured')
                self.assertEqual({r['path'] for r in records}, {a['path'] for a in case['artifacts']})
                self.assertTrue(all(r['status'] == 'missing' for r in records), cid)


if __name__ == '__main__':
    unittest.main()
