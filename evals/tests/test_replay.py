"""Contract and mutation tests for the offline provider subset."""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from statistics import median

ROOT=Path(__file__).parents[1]
spec=importlib.util.spec_from_file_location('replay_server',ROOT/'replay_server.py')
replay=importlib.util.module_from_spec(spec);spec.loader.exec_module(replay)
BASE=json.loads((ROOT/'suites/private-company-research/base_data.json').read_text())
ORG=[o['identifier']['uuid'] for o in BASE['entities']['organizations']]
LIST=next(k for k,v in BASE['lists'].items() if v['name']=='Research shortlist')
class ReplayTests(unittest.TestCase):
 def new(self,**fixture): return replay.Replay(fixture)
 def test_nine_tools(self):
  self.assertEqual(len(replay.TOOLS),9)
  self.assertEqual(len({t['name'] for t in replay.TOOLS}),9)
 def test_tool_annotations_preserve_mutation_truth(self):
  tools={t['name']:t for t in replay.TOOLS}
  for name,tool in tools.items():
   annotations=tool['annotations']
   self.assertEqual(annotations['readOnlyHint'],name not in {'cb_list_create','cb_list_add_entities'})
   self.assertFalse(annotations['destructiveHint'])
   self.assertFalse(annotations['openWorldHint'])
   self.assertEqual(annotations['idempotentHint'],name!='cb_list_create')
  self.assertTrue(tools['cb_list_add_entities']['annotations']['idempotentHint'])
 def test_person_biography_projection(self):
  person=BASE['entities']['people'][0]
  result=self.new().call('cb_entity_get',{'entity_id':person['identifier']['uuid'],'entity_def_id':'person','field_ids':['identifier','description'],'card_ids':[]})
  self.assertNotIn('error',result)
  bio=next(p['value'] for p in result['properties'] if p['field_id']=='description')
  self.assertEqual(bio,person['description'])
  self.assertTrue(bio.startswith('Fictional'))
 def test_tool_errors_are_diagnostics_not_blanket_failure(self):
  suite=json.loads((ROOT/'suites/private-company-research/suite.json').read_text())
  for case in suite['cases']:
   self.assertFalse(any(c['kind']=='tool_errors' for c in case['checks']))
   self.assertTrue(any(c['kind']=='semantic' and 'recoverable validation error' in c['rubric'] for c in case['checks']))
 def test_predicate_values_explicitly_allow_arbitrary_json(self):
  tool=next(t for t in replay.TOOLS if t['name']=='cb_search_query')
  values=tool['inputSchema']['properties']['predicates']['items']['properties']['values']
  self.assertEqual(values,{'type':'array','items':{}})
  replay.validate_schema([15000000,True,None,{'key':'value'},['nested']],values)
 def test_required_and_unknown_arguments(self):
  r=self.new()
  for args in ({},{'entity_id':ORG[0],'unknown':True}):
   self.assertEqual(r.call('cb_entity_get',args)['error']['code'],'VALIDATION_ERROR')
 def test_profile_current_envelope(self):
  r=self.new().call('cb_entity_get',{'entity_id':ORG[0],'field_ids':['identifier','funding_total'],'card_ids':['funding_rounds_list']})
  self.assertIsInstance(r['properties'],list);self.assertIsInstance(r['cards'],list)
  self.assertEqual([p['field_id'] for p in r['properties']],['identifier','funding_total'])
  self.assertTrue(r['cards'][0]['entities'][0]['properties'])
 def test_skip_profile_fields_and_card_paging(self):
  r=self.new(card_page_size=1)
  args={'entity_id':ORG[0],'field_ids':[],'card_ids':['funding_rounds_list']}
  first=r.call('cb_entity_get',args)
  self.assertEqual(first['properties'],[]);self.assertTrue(first['cards'][0]['has_more_entities'])
  key=next(p['value']['uuid'] for p in first['cards'][0]['entities'][0]['properties'] if p['field_id']=='identifier')
  second=r.call('cb_entity_get',{**args,'after_id':key})
  self.assertNotEqual(first['cards'][0]['entities'],second['cards'][0]['entities'])
 def test_card_cursor_requires_one_card(self):
  self.assertIn('error',self.new().call('cb_entity_get',{'entity_id':ORG[0],'after_id':'made-up','card_ids':[]}))
 def test_unknown_entity_card_projection(self):
  r=self.new()
  for args in ({'entity_id':'invented'}, {'entity_id':ORG[0],'card_ids':['invented']},{'entity_id':ORG[0],'field_ids':['invented']}):self.assertIn('error',r.call('cb_entity_get',args))
 def test_resolver_and_ambiguity(self):
  r=self.new()
  one=r.call('cb_expert_resolve_entity',{'name':'Lumenquill Dental','cb_entity_get':None})
  self.assertEqual(one['disambiguation']['result_type'],'match');self.assertNotIn('entity',one)
  self.assertEqual(one['disambiguation']['entity']['properties']['identifier']['uuid'],ORG[0])
  self.assertIsInstance(one['disambiguation']['entity']['confidence'],float)
  embedded=r.call('cb_expert_resolve_entity',{'name':'Lumenquill Dental','cb_entity_get':{'field_ids':['identifier'],'card_ids':[]}})
  self.assertIsInstance(embedded['entity']['properties'],list)
  two=r.call('cb_expert_resolve_entity',{'name':'Rivetwillow','cb_entity_get':None})
  self.assertEqual(len(two['disambiguation']['candidates']),2)
 def test_profile_failure_applies_to_embedded_and_standalone(self):
  r=self.new(profile_error={'code':'AUTHENTICATION_REQUIRED'})
  direct=r.call('cb_entity_get',{'entity_id':ORG[0]})
  embedded=r.call('cb_expert_resolve_entity',{'name':'Lumenquill Dental'})
  self.assertEqual(direct['error']['code'],'AUTHENTICATION_REQUIRED')
  self.assertEqual(embedded['entity']['error']['code'],'AUTHENTICATION_REQUIRED')
 def test_domain_resolution(self):
  r=self.new().call('cb_expert_resolve_entity',{'name':'Rivetwillow','domains':['https://fixture-rivetwillow-health.example/about'],'cb_entity_get':None})
  self.assertEqual(r['disambiguation']['entity']['properties']['identifier']['uuid'],ORG[9])
 def test_strict_cap_and_scope(self):
  args={'collection_id':'organizations','field_ids':['identifier','funding_total'],'predicates':[{'field_id':'funding_total','operator_id':'lt','values':[15000000]},{'field_id':'status','operator_id':'eq','values':['operating']},{'field_id':'ipo_status','operator_id':'eq','values':['private']},{'field_id':'categories','operator_id':'includes','values':['fixture-dental']},{'field_id':'location_identifiers','operator_id':'includes','values':['fixture-united-states']}]}
  rows=self.new().call('cb_search_query',args)['entities']
  self.assertEqual({r['uuid'] for r in rows},{ORG[0],ORG[1],ORG[9]})
 def test_null_is_not_zero(self):
  r=self.new()
  result=r.call('cb_search_query',{'collection_id':'organizations','predicates':[{'field_id':'funding_total','operator_id':'eq','values':[0]}]})
  self.assertEqual(result['count'],0)
  result=r.call('cb_search_query',{'collection_id':'organizations','predicates':[{'field_id':'funding_total','operator_id':'blank','values':[True]}]})
  self.assertEqual(result['count'],1)
 def test_money_normalization_case_distinguishes_raw_and_usd(self):
  suite=json.loads((ROOT/'suites/private-company-research/suite.json').read_text())
  case=next(c for c in suite['cases'] if c['id']=='funding-money-normalization')
  r=self.new(**case['fixture'])
  orgs=r.call('cb_search_query',{'collection_id':'organizations','field_ids':['identifier'],'predicates':[
   {'field_id':'operating_status','operator_id':'eq','values':['operating']},
   {'field_id':'ipo_status','operator_id':'eq','values':['private']},
   {'field_id':'categories','operator_id':'includes','values':['fixture-dental']},
   {'field_id':'location_identifiers','operator_id':'includes','values':['fixture-united-states']},
  ]})['entities']
  rounds=r.call('cb_search_query',{'collection_id':'funding_rounds','field_ids':['identifier','money_raised'],'predicates':[
   {'field_id':'funded_organization_identifier','operator_id':'includes','values':[o['uuid'] for o in orgs]},
   {'field_id':'investment_type','operator_id':'eq','values':['seed']},
   {'field_id':'announced_on','operator_id':'between','values':['2026-09-01','2026-09-30']},
  ]})['entities']
  amounts=[row['money_raised'] for row in rounds]
  normalized=[a['value_usd'] for a in amounts if a is not None and a['value_usd'] is not None]
  self.assertEqual((len(rounds),len(normalized)),(6,5))
  self.assertEqual(sorted(normalized),[2500000,3000000,6000000,7500000,10000000])
  self.assertEqual(median(normalized),6000000)
  self.assertNotEqual(median(a['value'] for a in amounts if a is not None),median(normalized))
  unnormalized=[a for a in amounts if a['value_usd'] is None]
  self.assertEqual(unnormalized,[{'value':10000000,'currency':'EUR','value_usd':None}])
  self.assertEqual(len([a for a in amounts if a['currency']!='USD' and a['value_usd'] is not None and a['value']!=a['value_usd']]),2)
  for org_id in ORG[:2]:
   org=next(o for o in r.data['entities']['organizations'] if o['identifier']['uuid']==org_id)
   related=[row for row in r.data['entities']['funding_rounds'] if row['funded_organization_identifier']['uuid']==org_id]
   self.assertEqual(sum(row['money_raised']['value_usd'] for row in related),org['funding_total']['value_usd'])
   self.assertTrue(all(row['funded_organization_funding_total']==org['funding_total'] for row in related))
   self.assertEqual(next(row['money_raised'] for row in related if row['announced_on']=='2026-09-10'),org['last_funding_total'])
 def test_predicates_and_queries_exclusive(self):
  self.assertIn('error',self.new().call('cb_search_query',{'collection_id':'organizations','predicates':[],'query':[]}))
 def test_unsupported_subquery_is_explicit(self):
  r=self.new().call('cb_search_query',{'collection_id':'organizations','query':[{'type':'sub_query'}]})
  self.assertEqual(r['error']['code'],'UNSUPPORTED_FIXTURE')
 def test_projection_and_predicate_validation(self):
  r=self.new();base={'collection_id':'organizations'}
  bad=[{'field_ids':['invented']},{'predicates':[{'field_id':'invented','operator_id':'eq','values':['x']}]},{'predicates':[{'field_id':'funding_total','operator_id':'contains','values':['x']}]},{'predicates':[{'field_id':'funding_total','operator_id':'lt','values':['15000000']}]},{'predicates':[{'field_id':'status','operator_id':'eq','values':['active']}]},{'predicates':[{'field_id':'categories','operator_id':'includes','values':['Dental']}]},{'predicates':[{'field_id':'founded_on','operator_id':'gte','values':['yesterday']}]},{'predicates':[{'field_id':'status','operator_id':'blank','values':['true']}]}]
  for extra in bad:
   with self.subTest(extra=extra): self.assertIn('error',r.call('cb_search_query',{**base,**extra}))
 def test_empty_collections_still_validate(self):
  r=self.new(empty_collections=['organizations']).call('cb_search_query',{'collection_id':'organizations','predicates':[{'field_id':'invented','operator_id':'eq','values':['x']}]})
  self.assertIn('error',r)
 def test_search_uuid_pagination(self):
  r=self.new(page_size=2); args={'collection_id':'organizations','field_ids':['identifier']};rows=[];cursor=None
  while True:
   result=r.call('cb_search_query',{**args,'after_id':cursor});self.assertEqual(result['count'],10)
   page=result['entities'];rows+=page
   if not page or len(rows)==result['count']:break
   cursor=page[-1]['uuid']
  self.assertEqual(len({x['uuid'] for x in rows}),10)
  self.assertIn('error',r.call('cb_search_query',{**args,'after_id':'wrong'}))
 def test_includes_or_includes_all_and(self):
  r=self.new();args={'collection_id':'organizations','field_ids':['identifier']}
  any_=r.call('cb_search_query',{**args,'predicates':[{'field_id':'categories','operator_id':'includes','values':['fixture-dental','fixture-software']}]})
  all_=r.call('cb_search_query',{**args,'predicates':[{'field_id':'categories','operator_id':'includes_all','values':['fixture-dental','fixture-software']}]})
  self.assertEqual(any_['count'],10);self.assertEqual(all_['count'],9)
 def test_sort_and_projection(self):
  r=self.new().call('cb_search_query',{'collection_id':'organizations','field_ids':['identifier'],'order':[{'field_id':'funding_total','sort':'desc'}]})
  self.assertEqual(r['entities'][0]['uuid'],ORG[7]);self.assertNotIn('funding_total',r['entities'][0])
 def test_list_creation_append_dedupe(self):
  r=self.new();new=r.call('cb_list_create',{'name':'Unit test'})['list_id']
  r.call('cb_list_add_entities',{'list_id':new,'entity_ids':[ORG[0],ORG[0],ORG[1]]})
  got=r.call('cb_list_get',{'list_id':new});self.assertEqual(got['total_count'],2)
  self.assertIn('error',r.call('cb_list_add_entities',{'list_id':new,'entity_ids':['invalid']}))
 def test_list_paging(self):
  r=self.new(list_page_size=1);a=r.call('cb_list_get',{'list_id':LIST});b=r.call('cb_list_get',{'list_id':LIST,'after_id':a['next_after_id']})
  self.assertEqual(a['total_count'],2);self.assertIsNone(b['next_after_id']);self.assertNotEqual(a['company_identifiers'],b['company_identifiers'])
 def test_uncertain_write_can_commit(self):
  r=self.new(uncertain_add=True)
  got=r.call('cb_list_add_entities',{'list_id':LIST,'entity_ids':[ORG[2]]})
  self.assertEqual(got['error']['code'],'SERVICE_UNCERTAIN')
  self.assertEqual(r.call('cb_list_get',{'list_id':LIST})['total_count'],3)
 def test_partial_write_and_readback(self):
  r=self.new(reject_add_ids=[ORG[5]]);r.call('cb_list_add_entities',{'list_id':LIST,'entity_ids':[ORG[2],ORG[5]]})
  self.assertEqual(r.state['lists'][LIST]['entity_ids'],ORG[:3])
 def test_state_and_log_survive_restart(self):
  with tempfile.TemporaryDirectory() as d:
   state=Path(d)/'state.json';log=Path(d)/'tools.jsonl'
   a=replay.Replay({},state,log,1);a.call('cb_list_add_entities',{'list_id':LIST,'entity_ids':[ORG[2]]})
   b=replay.Replay({},state,log,2);b.call('cb_list_get',{'list_id':LIST})
   self.assertEqual(len(b.state['lists'][LIST]['entity_ids']),3)
   events=[json.loads(l) for l in log.read_text().splitlines()];self.assertEqual([e['turn'] for e in events],[1,2]);self.assertIn('state_after',events[0])
 def test_failures_are_logged(self):
  with tempfile.TemporaryDirectory() as d:
   log=Path(d)/'tools.jsonl';r=replay.Replay({'errors':[{'tool':'cb_list_create','code':'PERMISSION_DENIED','persist':True}]},log_path=log)
   r.call('cb_list_create',{'name':'Fail'})
   self.assertEqual(json.loads(log.read_text())['result']['error']['code'],'PERMISSION_DENIED')
 def test_jsonrpc_server(self):
  with tempfile.TemporaryDirectory() as d:
   fixture=Path(d)/'fixture.json';fixture.write_text('{}')
   req='\n'.join(json.dumps(x) for x in [{'jsonrpc':'2.0','id':1,'method':'initialize','params':{}},{'jsonrpc':'2.0','id':2,'method':'tools/list','params':{}},{'jsonrpc':'2.0','id':3,'method':'tools/call','params':{'name':'cb_list_query','arguments':{}}}])+'\n'
   p=subprocess.run([sys.executable,str(ROOT/'replay_server.py'),'--fixture',str(fixture),'--state',str(Path(d)/'state.json'),'--log',str(Path(d)/'log.jsonl')],input=req,text=True,capture_output=True,check=True)
   results=[json.loads(line) for line in p.stdout.splitlines()]
   self.assertEqual(len(results),3);self.assertEqual(len(results[1]['result']['tools']),9)
   self.assertEqual(len(results[2]['result']['structuredContent']['company_lists']),4)
 def test_corpus_family_separation_and_semantic_checks(self):
  suite=json.loads((ROOT/'suites/private-company-research/suite.json').read_text());families={}
  self.assertEqual(len(suite['cases']),63)
  self.assertEqual(len({c['id'] for c in suite['cases']}),63)
  for case in suite['cases']:
   self.assertEqual(families.setdefault(case['family'],case['split']),case['split'])
   self.assertTrue(any(c['kind']=='semantic' for c in case['checks']))
   self.assertNotIn('checks',case['fixture']);self.assertNotIn('expected',case['fixture'])
 def test_negative_routing_excludes_all_workflows(self):
  suite=json.loads((ROOT/'suites/private-company-research/suite.json').read_text())
  workflows={c['workflow'] for c in suite['cases']}
  negative=[c for c in suite['cases'] if 'negative-routing' in c['tags']]
  self.assertEqual(len(negative),5)
  for case in negative:
   self.assertEqual({c['skill'] for c in case['checks'] if c['kind']=='activation' and c['expected'] is False},workflows)
 def test_brief_outcome_accepts_embedded_profile(self):
  suite=json.loads((ROOT/'suites/private-company-research/suite.json').read_text())
  case=next(c for c in suite['cases'] if c['id']=='brief-happy')
  self.assertFalse(any(c['kind']=='called' and c.get('tool')=='cb_entity_get' for c in case['checks']))
 def test_write_cases_separate_preview_and_preservation(self):
  suite=json.loads((ROOT/'suites/private-company-research/suite.json').read_text())
  writes=[c for c in suite['cases'] if 'authorized-write' in c['tags']]
  self.assertEqual(len(writes),6)
  for case in writes:
   preview=[c for c in case['checks'] if c['id'].endswith('-pre-write-preview')]
   self.assertEqual(len(preview),1)
   self.assertEqual(preview[0]['kind'],'semantic');self.assertEqual(preview[0]['severity'],'critical')
   protected=[c for c in case['checks'] if '-preserve-' in c['id']]
   self.assertGreaterEqual(len(protected),3)
   self.assertTrue(all(c['kind']=='membership' and c['mode']=='exact' and c['severity']=='critical' for c in protected))
  self.assertIn('independent human review',suite['description'])
 def test_every_fixture_initializes(self):
  for case in json.loads((ROOT/'suites/private-company-research/suite.json').read_text())['cases']:
   with self.subTest(case=case['id']): replay.Replay(case['fixture'])

if __name__=='__main__':unittest.main()
