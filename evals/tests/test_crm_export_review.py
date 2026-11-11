"""Regression coverage for CRM account selection and monetary input."""
import csv
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
READERS = sorted((ROOT / 'skills').glob('*/scripts/crm_export.py'))


class CRMReviewTests(unittest.TestCase):
    def run_reader(self, reader, rows, account=None):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        work = Path(tmp.name)
        source = work / 'input.csv'
        with source.open('w', newline='') as fh:
            csv.writer(fh).writerows(rows)
        args = [sys.executable, str(reader), '--input', str(source), '--out-dir', str(work / 'out')]
        if account:
            args += ['--account', account]
        return subprocess.run(args, capture_output=True, text=True), work / 'out'

    def test_selected_contacts_keep_account_identity(self):
        for reader in READERS:
            for ids in [('a1', 'a2'), ('', '')]:
                with self.subTest(reader=reader.parent.parent.name, ids=ids):
                    result, out = self.run_reader(reader, [
                        ['Account Name', 'Website', 'Account ID', 'Full Name', 'Title'],
                        ['Acme', 'one.example', ids[0], 'First Person', 'CEO'],
                        ['Acme', 'two.example', ids[1], 'Other Person', 'CFO'],
                        ['Acme', 'one.example', ids[0], 'Third Person', 'CTO'],
                    ], 'one.example')
                    self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                    selected = json.loads(result.stdout)['account']['contacts']
                    self.assertEqual([c['Name'] for c in selected], ['First Person', 'Third Person'])
                    self.assertEqual({c['CRM ID'] for c in selected}, {ids[0]})
                    with (out / 'crm-contacts.csv').open(encoding='utf-8-sig') as fh:
                        contacts = list(csv.DictReader(fh))
                    self.assertEqual(len(contacts), 3)
                    self.assertEqual([c['CRM ID'] for c in contacts], [ids[0], ids[0], ids[1]])

    def test_ambiguous_amounts_fail_before_writing_totals(self):
        for reader in READERS:
            for amount in ['1234,56', '1.234,56', '(1,000.00)', '1,234', '1,234.56', 'USD 100', '1e3']:
                with self.subTest(reader=reader.parent.parent.name, amount=amount):
                    result, out = self.run_reader(reader, [
                        ['Account Name', 'Website', 'Opportunity Name', 'Stage', 'Amount', 'Currency'],
                        ['Acme', 'one.example', 'Deal', 'Qualification', amount, 'USD'],
                    ])
                    self.assertNotEqual(result.returncode, 0)
                    self.assertIn('ambiguous CRM amount', json.loads(result.stdout)['error'])
                    self.assertFalse(out.exists())

    def test_supported_amounts_preserve_sign_and_missing_values(self):
        for reader in READERS:
            for amount, expected in [('1234.56', 1234.56), ('-1000.00', -1000), ('$100.00', 100), ('0', 0), ('', None)]:
                with self.subTest(reader=reader.parent.parent.name, amount=amount):
                    result, out = self.run_reader(reader, [
                        ['Account Name', 'Website', 'Opportunity Name', 'Stage', 'Amount', 'Currency'],
                        ['Acme', 'one.example', 'Deal', 'Qualification', amount, 'USD'],
                    ])
                    self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                    deals = json.loads((out / 'crm-deals.json').read_text())['deals']
                    self.assertEqual(deals[0]['amount'], expected)
                    self.assertEqual(deals[0]['amount_original'], amount)
                    with (out / 'crm-accounts.csv').open(encoding='utf-8-sig') as fh:
                        account = next(csv.DictReader(fh))
                    self.assertEqual(account['Open amount status'], 'missing_amount' if expected is None else 'complete')
                    if expected is not None:
                        self.assertEqual(float(account['Open amount'].lstrip("'")), expected)


if __name__ == '__main__':
    unittest.main()
