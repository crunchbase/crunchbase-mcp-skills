"""Behavioral checks for isolated installs and repaired replay fixtures."""
import importlib.util
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('revision_replay', ROOT / 'evals/replay_server.py')
replay = importlib.util.module_from_spec(spec)
spec.loader.exec_module(replay)
BASE = json.loads(replay.BASE.read_text())
ORGS = BASE['entities']['organizations']
LIST = next(k for k, v in BASE['lists'].items() if v['name'] == 'Research shortlist')

class RevisionTests(unittest.TestCase):
    def test_individual_skill_install_documented_cli_and_errors(self):
        for source in sorted((ROOT / 'skills').glob('*/scripts/derive_metrics.py')):
            with self.subTest(skill=source.parent.parent.name), tempfile.TemporaryDirectory() as directory:
                installed = Path(directory) / 'installed'
                shutil.copytree(source.parent.parent, installed)
                reference = (installed / 'references/calculation-spec.md').read_text()
                payload = json.loads(re.search(r'```json\n(.*?)\n```', reference, re.S).group(1))
                (installed / 'input.json').write_text(json.dumps(payload))
                command = [sys.executable, '-I', 'scripts/derive_metrics.py']
                result = subprocess.run(command + ['input.json'], cwd=installed, capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stderr)
                data = json.loads(result.stdout)
                self.assertEqual(data['current_12_months']['capital_usd'], 1000000)
                self.assertEqual(data['formation_within_confirmed_universe'], {'2020': 1})
                for amount in (0, None):
                    payload['rounds'][0]['money_raised_usd'] = amount
                    result = subprocess.run(command, cwd=installed, input=json.dumps(payload), capture_output=True, text=True)
                    self.assertEqual(result.returncode, 0, result.stderr)
                    metrics = json.loads(result.stdout)['current_12_months']
                    self.assertEqual(metrics['numeric_amount_count'], int(amount is not None))
                    self.assertEqual(metrics['median_round_usd'], amount)
                payload['rounds'][0]['announced_on'] = '2027-01-01'
                result = subprocess.run(command, cwd=installed, input=json.dumps(payload), capture_output=True, text=True)
                self.assertEqual(result.returncode, 2)
                self.assertEqual(result.stdout, '')
                self.assertIn('error:', result.stderr)

    def test_membership_uses_selected_field_on_rounds_and_organizations(self):
        r = replay.Replay()
        for collection, field in [('organizations', 'identifier'), ('funding_rounds', 'funded_organization_identifier')]:
            for row in BASE['entities'][collection]:
                expected = row[field]['uuid'] in BASE['lists'][LIST]['entity_ids']
                for op in ('in_list', 'not_in_list'):
                    predicate = {'field_id': field, 'operator_id': op, 'values': [LIST]}
                    self.assertEqual(r.predicate(row, predicate, collection), expected if op == 'in_list' else not expected)

    def test_partial_append_is_independent_of_batch_size_and_retry(self):
        accepted, rejected = ORGS[2]['identifier']['uuid'], ORGS[5]['identifier']['uuid']
        for batches in ([[accepted, rejected]], [[rejected], [accepted]]):
            r = replay.Replay({'reject_add_ids': [rejected]})
            for batch in batches + [[rejected]]:
                r.call('cb_list_add_entities', {'list_id': LIST, 'entity_ids': batch})
            self.assertEqual(set(r.state['lists'][LIST]['entity_ids']), set(BASE['lists'][LIST]['entity_ids'] + [accepted]))

    def test_failure_follows_successful_target_collection_not_validation_error(self):
        r = replay.Replay({'page_size': 1, 'errors': [{'tool': 'cb_search_query', 'match': {'collection_id': 'funding_rounds'}, 'after_successes': 1, 'code': 'USAGE_LIMIT'}]})
        r.call('cb_search_query', {'collection_id': 'organizations'})
        bad = r.call('cb_search_query', {'collection_id': 'funding_rounds', 'field_ids': ['invented']})
        self.assertEqual(bad['error']['code'], 'VALIDATION_ERROR')
        self.assertNotIn('error', r.call('cb_search_query', {'collection_id': 'funding_rounds', 'field_ids': ['identifier']}))
        self.assertEqual(r.call('cb_search_query', {'collection_id': 'funding_rounds', 'field_ids': ['identifier']})['error']['code'], 'USAGE_LIMIT')
        self.assertNotIn('error', r.call('cb_search_query', {'collection_id': 'organizations'}))

    def test_all_unknown_fixture_clears_duplicate_money_fields(self):
        suite = json.loads((ROOT / 'evals/suites/private-company-research/suite.json').read_text())
        fixture = next(c['fixture'] for c in suite['cases'] if c['id'] == 'capital-unknown-all')
        for fields in fixture['overrides'].values():
            self.assertTrue(all(v is None for v in fields.values()))
            self.assertTrue('last_funding_total' in fields or 'funded_organization_funding_total' in fields)
