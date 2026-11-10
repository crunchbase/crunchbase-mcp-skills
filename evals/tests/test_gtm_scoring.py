"""Independent numeric examples, artifact and identity invariants for GTM scoring."""
import copy
import csv
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
SKILLS = ROOT / 'skills'
SCRIPTS = SKILLS / 'crunchbase-prospect-finder/scripts'
spec = importlib.util.spec_from_file_location('gtm_score', SCRIPTS / 'scoring.py')
score = importlib.util.module_from_spec(spec)
spec.loader.exec_module(score)


def company(**updates):
    base = {'uuid':'org-1','permalink':'fictional-one','name':'Fictional One',
            'url':'https://www.crunchbase.com/organization/fictional-one','domain':'one.example',
            'growth_score':80,'heat_score':60,'heat_delta':0,
            'last_funding_at':'2026-09-01','last_funding_type':'series_b'}
    base.update(updates)
    if 'permalink' in updates and 'url' not in updates: base['url']='https://www.crunchbase.com/organization/'+base['permalink']
    return base


def payload(*rows):
    return {'schema_version':1,'run':{'today':'2026-11-05','complete':True,'scope_id':'book-v1','mode':'icp','count':50},
            'candidates':list(rows) or [company()]}


def observation(**kwargs):
    return {'source':'Crunchbase','complete':True,'as_of':'2026-11-05','query_scope':'complete eligible history',**kwargs}


class GtmScoringTests(unittest.TestCase):
    def test_default_math_and_pair_parity(self):
        data = payload()
        a = score.run(data, 'prospect-finder')['rows'][0]
        b = score.run(data, 'account-prioritizer')['rows'][0]
        self.assertEqual((a['score'], a['tier']), (80, 'A'))
        self.assertEqual(a, b)
        self.assertEqual((SCRIPTS/'scoring.py').read_bytes(), (SKILLS/'crunchbase-account-prioritizer/scripts/scoring.py').read_bytes())

    def test_unknown_is_not_zero(self):
        unknown = score.run(payload(company(growth_score=None)), 'account-prioritizer')['rows'][0]
        zero = score.run(payload(company(growth_score=0)), 'account-prioritizer')['rows'][0]
        self.assertIsNone(unknown['score']); self.assertIsNone(unknown['tier'])
        self.assertEqual(unknown['coverage']['missing'], ['growth'])
        self.assertEqual(zero['score'], 48)
        self.assertEqual(zero['tier'], 'C')

    def test_funding_absence_requires_provenance(self):
        c = company(last_funding_at=None,last_funding_type=None)
        self.assertIsNone(score.run(payload(c),'prospect-finder')['rows'][0]['score'])
        c.update(funding_observation=observation(no_completed_funding=True), prediction_observation=observation(no_prediction=True))
        self.assertEqual(score.run(payload(c),'prospect-finder')['rows'][0]['score'],50)
        c['funding_observation']['complete'] = False
        with self.assertRaises(ValueError): score.run(payload(c),'prospect-finder')

    def test_future_invalid_imprecise_dates_and_nonfinite_rejected(self):
        for changes in ({'last_funding_at':'2027-11-05'},{'last_funding_at':'2026-09'},
                        {'last_fund_at':'2027-01-01'},{'heat_score':float('nan')},
                        {'growth_score':True},{'heat_delta':101}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                score.run(payload(company(**changes)),'prospect-finder')

    def test_date_boundaries(self):
        for event, expected in [('2026-05-05',100),('2026-04-05',75),('2025-11-05',75),
                                ('2025-10-05',50),('2024-11-05',50),('2024-10-05',25),('2023-10-05',0)]:
            c=company(last_funding_at=event,funding_tier='p500_negative_high')
            row=score.run(payload(c),'prospect-finder')['rows'][0]
            self.assertEqual(row['points']['funding'], expected)
        self.assertEqual(score.months_between(score.iso('2024-02-29','date'),score.iso('2025-02-28','date')),11)

    def test_custom_weights_fixed_tiers_public_and_investor(self):
        data=payload();data['rubric']={'weights':{'growth':2,'heat':0,'funding':0},'tiers':[85,80],'customer_bonus':0}
        row=score.run(data,'account-prioritizer')['rows'][0]
        self.assertEqual((row['score'],row['tier']),(80,'B'))
        data['candidates'][0]['heat_score']=None
        self.assertEqual(score.run(data,'account-prioritizer')['rows'][0]['score'],80)
        self.assertEqual(score.run(payload(company(ipo_status='public')),'prospect-finder')['rows'][0]['score'],65)
        self.assertEqual(score.run(payload(company(last_funding_at=None,last_fund_at='2026-10-01')),'prospect-finder')['rows'][0]['score'],80)
        data['rubric']['weights']={'growth':0}
        with self.assertRaises(ValueError):score.run(data,'account-prioritizer')

    def test_dedupe_identity_exclusions_and_order(self):
        c=company();d=company(uuid='org-2',permalink='fictional-two',name='Fictional Two',domain='two.example')
        data=payload(c,d,c)
        a=score.run(data,'prospect-finder')
        data['candidates'].reverse()
        self.assertEqual(a,score.run(data,'prospect-finder'))
        self.assertEqual(a['input_count'],2)
        data['exclude']={'domains':['https://www.one.example/path']}
        self.assertEqual(score.run(data,'prospect-finder')['list_uuids'],['org-2'])
        with self.assertRaises(ValueError): score.run(payload(c,company(growth_score=50)),'prospect-finder')
        data['exclude']={'names':['Fictional One']}
        with self.assertRaises(ValueError):score.run(data,'prospect-finder')

    def test_full_pool_state_not_display_limit(self):
        data=payload(company(),company(uuid='org-2',permalink='two',name='Two'))
        data['run']['count']=1
        r=score.run(data,'prospect-finder'); diff, state=score.state_diff(r,None)
        self.assertTrue(diff['baseline']);self.assertEqual(len(state['accounts']),2)
        diff,_=score.state_diff(r,state);self.assertFalse(diff['baseline']);self.assertEqual(diff['changes'],[])
        data['run']['scope_id']='new-book'
        self.assertTrue(score.state_diff(score.run(data,'prospect-finder'),state)[0]['baseline'])
        with self.assertRaises(ValueError):score.state_diff(r,{'schema_version':1})

    def test_cli_standalone_csv_and_failure_preserves_state(self):
        for slug,script in [('prospect-finder','score_prospects.py'),('account-prioritizer','account_prioritizer.py')]:
            with self.subTest(skill=slug), tempfile.TemporaryDirectory() as td:
                path=Path(td);inp=path/'input.json';out=path/'out.csv';state=path/'state.json'
                inp.write_text(json.dumps(payload(company(name='=1+1'))))
                command=[sys.executable,str(SKILLS/('crunchbase-'+slug)/'scripts'/script),'score','--input',str(inp),'--csv',str(out),'--state',str(state),'--write-state']
                p=subprocess.run(command,capture_output=True,text=True)
                self.assertEqual(p.returncode,0,p.stderr)
                result=json.loads(p.stdout);self.assertEqual(result['schema_version'],1)
                with out.open(encoding='utf-8-sig') as fh:row=next(csv.DictReader(fh))
                self.assertEqual(row['Name'],"'=1+1"); self.assertEqual(row['UUID'],'org-1')
                before=state.read_bytes();inp.write_text(json.dumps(payload(company(last_funding_at='2027-01-01'))))
                p=subprocess.run(command,capture_output=True,text=True)
                self.assertEqual(p.returncode,2);self.assertEqual(p.stdout,'');self.assertEqual(state.read_bytes(),before)

    def test_failed_stdout_delivery_preserves_monitoring_state(self):
        for skill, script in [('crunchbase-prospect-finder','score_prospects.py'),
                              ('crunchbase-account-prioritizer','account_prioritizer.py')]:
            with self.subTest(skill=skill), tempfile.TemporaryDirectory() as td:
                folder=Path(td); inp=folder/'input.json'; state=folder/'state.json'
                inp.write_text(json.dumps(payload()))
                command=[sys.executable,str(SKILLS/skill/'scripts'/script),'score','--input',str(inp),
                         '--state',str(state),'--write-state']
                for existing in (False,True):
                    if existing:
                        good=subprocess.run(command,capture_output=True,text=True)
                        self.assertEqual(good.returncode,0,good.stderr)
                    before=state.read_bytes() if state.exists() else None
                    read_fd,write_fd=os.pipe(); os.close(read_fd)
                    try:
                        failed=subprocess.run(command,stdout=write_fd,stderr=subprocess.PIPE,text=True)
                    finally:
                        os.close(write_fd)
                    self.assertNotEqual(failed.returncode,0)
                    self.assertEqual(state.read_bytes() if state.exists() else None,before)

    def test_empty_and_fully_excluded_pool_are_valid(self):
        data=payload();data['candidates']=[];del data['run']['count']
        result=score.run(data,'prospect-finder')
        self.assertEqual(result['rows'],[]);self.assertEqual(result['input_count'],0)
        data['candidates']=[company()];data['exclude']={'uuids':['org-1']}
        result=score.run(data,'prospect-finder');self.assertEqual(result['rows'],[])
        self.assertEqual(result['excluded_uuids'],['org-1'])

    def test_customer_bonus_requires_evidence_and_is_capped(self):
        c = company(growth_score=100,heat_score=100,customer_peer=[{'customer':'customer-1','dir':'fwd','shared':['segment-1']}])
        self.assertEqual(score.run(payload(c),'prospect-finder')['rows'][0]['score'],100)
        c['customer_peer'][0]['customer']='org-1'
        with self.assertRaises(ValueError):score.run(payload(c),'prospect-finder')
        c['customer_peer'][0]={'customer':'other','dir':'fwd'}
        with self.assertRaises(ValueError):score.run(payload(c),'prospect-finder')

    def test_mixed_selection_and_unknown_records_remain_in_pool(self):
        c=company();d=company(uuid='org-2',permalink='two',name='Two',similar=[{'seed':'seed-1','dir':'fwd','shared':['segment-1']}])
        e=company(uuid='org-3',permalink='three',name='Three',growth_score=None)
        data=payload(c,d,e);data['seeds']=[{'uuid':'seed-1'}];data['run'].update(mode='mixed',count=2,lookalike_count=1)
        r=score.run(data,'prospect-finder')
        self.assertEqual({v['uuid'] for v in r['rows']},{'org-1','org-2'})
        self.assertEqual(r['pool_unscored_count'],1);self.assertEqual(len(r['scope_rows']),3)

    def test_scoring_failure_and_corrupted_state_do_not_become_success(self):
        with self.assertRaises(ValueError):score.run([], 'prospect-finder')
        data=payload();data['run']['complete']=False
        with self.assertRaises(ValueError):score.run(data,'prospect-finder')
        r=score.run(payload(),'account-prioritizer');_,state=score.state_diff(r,None)
        state['accounts']['org-1']['tier']='invented'
        with self.assertRaises(ValueError):score.state_diff(r,state)
        state['accounts']['org-1']['tier']='A';state['accounts']['org-1']['score']=None
        with self.assertRaises(ValueError):score.state_diff(r,state)

    def test_prioritization_book_change_is_new_baseline(self):
        first=score.run(payload(),'account-prioritizer');_,state=score.state_diff(first,None)
        second=score.run(payload(company(),company(uuid='org-2',permalink='two',name='Two')),'account-prioritizer')
        self.assertTrue(score.state_diff(second,state)[0]['baseline'])

    def test_reject_wrong_profile_url_and_unaccepted_similarity(self):
        with self.assertRaises(ValueError):score.run(payload(company(url='https://www.crunchbase.com/organization/wrong')),'prospect-finder')
        data=payload(company(similar=[{'seed':'unaccepted','dir':'fwd','shared':['segment-1']}]))
        data['seeds']=[{'uuid':'accepted'}];data['run']['mode']='lookalike'
        with self.assertRaises(ValueError):score.run(data,'prospect-finder')
        data['candidates'][0]['similar'][0]['seed']='accepted'
        self.assertEqual(len(score.run(data,'prospect-finder')['rows']),1)

    def test_destination_export_headers_preserve_crm_id(self):
        row=score.run(payload(company(crm_accounts=[{'crm_id':'crm-123'}])),'account-prioritizer')['rows']
        for mode, id_column in [('clay','CRM ID'),('crm','Id'),('hubspot','Record ID')]:
            with self.subTest(mode=mode),tempfile.TemporaryDirectory() as td:
                path=Path(td)/'out.csv';score.write_csv(path,row,mode)
                with path.open(encoding='utf-8-sig') as fh: exported=next(csv.DictReader(fh))
                self.assertEqual(exported[id_column],'crm-123')

    def test_parser_to_scoring_exports_preserve_currency_and_blank_mixed_total(self):
        for currencies, amount, currency, status in [
                (("USD", "USD"), "200", "USD", "complete"),
                (("USD", "EUR"), "", "", "mixed_currencies"),
                (("", ""), "", "", "unknown_currency")]:
            with self.subTest(currencies=currencies), tempfile.TemporaryDirectory() as td:
                work = Path(td); source = work / 'crm.csv'
                source.write_text('Account Name,Website,Account ID,Opportunity Name,Stage,Amount,Currency\n'
                                  + ''.join(f'One,one.example,crm-1,Deal {i},Qualification,100,{cur}\n' for i, cur in enumerate(currencies)))
                parsed = subprocess.run([sys.executable, str(SCRIPTS / 'crm_export.py'), '--input', str(source), '--out-dir', str(work / 'parsed')], capture_output=True, text=True)
                self.assertEqual(parsed.returncode, 0, parsed.stderr)
                with (work / 'parsed/crm-accounts.csv').open(encoding='utf-8-sig') as fh:
                    crm = next(csv.DictReader(fh))
                normalized = {key: crm.get(header, '') for key, header in score.CRM_COLUMNS.items()}
                normalized['crm_name'] = crm['Account']
                for workflow in ('prospect-finder', 'account-prioritizer'):
                    result = score.run(payload(company(crm_accounts=[normalized])), workflow)
                    self.assertEqual(result['rows'][0]['crm_accounts'][0]['open_amount_status'], status)
                    for fmt in ('csv', 'clay', 'crm', 'hubspot'):
                        target = work / (fmt + '.csv'); score.write_csv(target, result['rows'], fmt)
                        with target.open(encoding='utf-8-sig') as fh:
                            row = next(csv.DictReader(fh))
                        self.assertEqual(row['Open amount'], amount)
                        self.assertEqual(row['Open amount currency'], currency)
                        self.assertEqual(row['Open amount status'], status)

    def test_crm_passthrough_preserves_distinct_ids_and_escapes(self):
        c=company(crm_accounts=[{'crm_id':'crm-1','owner':'=FORMULA','deal_stage':'Qualification'},
                                {'crm_id':'crm-2','owner':'Sarah','next_step':'Recorded next step'}])
        result=score.run(payload(c),'account-prioritizer')
        with tempfile.TemporaryDirectory() as td:
            path=Path(td)/'output.csv';score.write_csv(path,result['rows'])
            with path.open(encoding='utf-8-sig') as fh:rows=list(csv.DictReader(fh))
        self.assertEqual([r['CRM ID'] for r in rows],['crm-1','crm-2'])
        self.assertEqual([r['UUID'] for r in rows],['org-1','org-1'])
        self.assertEqual(rows[0]['Owner'],"'=FORMULA")
        self.assertEqual(rows[1]['Next step'],'Recorded next step')
        other=company(uuid='org-2',permalink='other',crm_accounts=[{'crm_id':'crm-1'}])
        with self.assertRaisesRegex(ValueError,'conflicting canonical'):
            score.run(payload(c,other),'account-prioritizer')
        with self.assertRaises(ValueError):
            score.run(payload(company(crm_accounts=[{'crm_id':'crm-1','email':'private@example.com'}])),'account-prioritizer')

    def test_crm_does_not_merge_names_or_distinct_ids_and_escapes(self):
        with tempfile.TemporaryDirectory() as td:
            path=Path(td); inp=path/'crm.csv';out=path/'out'
            inp.write_text('Account Name,Website,Account ID,Account Owner\nSame,one.example,one,Sarah\nSame,two.example,two,Sarah\n=1+1,three.example,three,Sarah\nSame,one.example,four,Sarah\n')
            p=subprocess.run([sys.executable,str(SCRIPTS/'crm_export.py'),'--input',str(inp),'--out-dir',str(out)],capture_output=True,text=True)
            self.assertEqual(p.returncode,0,p.stderr); self.assertEqual(json.loads(p.stdout)['accounts'],4)
            with (out/'crm-accounts.csv').open(encoding='utf-8-sig') as fh: rows=list(csv.DictReader(fh))
            self.assertEqual(len(rows),4);self.assertIn("'=1+1",[r['Account'] for r in rows])


if __name__ == '__main__': unittest.main()
