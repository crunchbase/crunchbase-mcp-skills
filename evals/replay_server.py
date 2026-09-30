#!/usr/bin/env python3
"""Offline JSON-RPC MCP fixture for a documented subset of Crunchbase tools.

No network calls. Synthetic provider responses, not a production API emulator.
Scoring expectations never enter this process or its responses.
"""
from __future__ import annotations
import argparse
import copy
import datetime as dt
import json
from pathlib import Path
import sys
import uuid

BASE = Path(__file__).parent / 'suites/private-company-research/base_data.json'
MUTATIONS = {'cb_list_create', 'cb_list_add_entities'}
ALIASES = {'organization':'organizations', 'organization.companies':'organizations', 'organization.companies.private':'organizations', 'funding_round':'funding_rounds', 'category':'categories', 'location':'locations', 'person':'people'}

def schema(properties, required=()):
    return {'type':'object','properties':properties,'required':list(required),'additionalProperties':False}
S={'type':'string'}
N={'type':['string','null']}
A={'type':['array','null'],'items':S}
PRED=schema({'field_id':S,'operator_id':S,'values':{'type':'array','items':{}}},['field_id','operator_id'])
TOOLS = [
 {'name':'cb_reference','description':'Look up entity fields, operators, cards, and search guidance by reference path. Empty path returns the index.','inputSchema':schema({'path':S})},
 {'name':'cb_entity_autocomplete','description':'Find identifiers by name in specified collections.','inputSchema':schema({'query':S,'collection_ids':N,'limit':{'type':['integer','null'],'minimum':1,'maximum':25}},['query'])},
 {'name':'cb_expert_resolve_entity','description':'Resolve a named entity to a confident match or candidate identifiers. Set cb_entity_get to null to disable embedded profile retrieval.','inputSchema':schema({'name':{'type':'string','minLength':1,'maxLength':100},'collection_id':N,'domains':A,'context':N,'cb_entity_get':{'anyOf':[{'type':'null'},schema({'field_ids':A,'card_ids':A,'related_entity_limit':{'type':['integer','null'],'minimum':1,'maximum':2000}})]}},['name'])},
 {'name':'cb_entity_get','description':'Retrieve a known entity profile as labeled properties and relationship cards. after_id paginates exactly one selected card. field_ids=[] omits top-level properties.','inputSchema':schema({'entity_id':S,'entity_def_id':N,'field_ids':A,'card_ids':A,'after_id':N,'related_entity_limit':{'type':['integer','null'],'minimum':1,'maximum':2000}},['entity_id'])},
 {'name':'cb_search_query','description':'Search entities with explicit projections, AND predicates or recursive query items, sort clauses, and UUID pagination. Resolve field contracts through cb_reference.','inputSchema':schema({'collection_id':S,'field_ids':A,'predicates':{'type':['array','null'],'items':PRED},'query':{'type':['array','null'],'items':{'type':'object'}},'order':{'type':['array','null'],'items':schema({'field_id':S,'sort':{'enum':['asc','desc']},'nulls':{'enum':['first','last',None]}},['field_id'])},'limit':{'type':['integer','null'],'minimum':1,'maximum':1000},'after_id':N},['collection_id'])},
 {'name':'cb_list_query','description':'List the saved lists owned by the caller.','inputSchema':schema({})},
 {'name':'cb_list_get','description':'Read company identifiers in a saved list, using next_after_id for further pages.','inputSchema':schema({'list_id':S,'after_id':N},['list_id'])},
 {'name':'cb_list_create','description':'Create a new empty saved list.','inputSchema':schema({'name':S},['name'])},
 {'name':'cb_list_add_entities','description':'Append organization UUIDs to an existing saved list.','inputSchema':schema({'list_id':S,'entity_ids':{'type':'array','items':S}},['list_id','entity_ids'])},
]
# These are offline fixture operations. Mutating tools remain explicitly writable;
# approval policy belongs to the runner and must not be bypassed by metadata.
for tool in TOOLS:
    tool['annotations']={
        'readOnlyHint':tool['name'] not in MUTATIONS,
        'destructiveHint':False,
        'idempotentHint':tool['name']!='cb_list_create',
        'openWorldHint':False,
    }

class ValidationError(Exception):
    pass

def validate_schema(value, contract, path='arguments'):
    if 'anyOf' in contract:
        for option in contract['anyOf']:
            try:
                validate_schema(value,option,path)
                return
            except ValidationError:
                pass
        raise ValidationError(f'{path} does not match an allowed type')
    types=contract.get('type',[])
    if isinstance(types,str): types=[types]
    actual=('null' if value is None else 'boolean' if isinstance(value,bool) else 'integer' if isinstance(value,int) else 'number' if isinstance(value,float) else 'string' if isinstance(value,str) else 'array' if isinstance(value,list) else 'object' if isinstance(value,dict) else 'unknown')
    if types and actual not in types: raise ValidationError(f'{path} must have type {types}')
    if 'enum' in contract and value not in contract['enum']: raise ValidationError(f'{path} must be one of {contract["enum"]}')
    if actual in ('integer','number'):
        if value<contract.get('minimum',value) or value>contract.get('maximum',value): raise ValidationError(f'{path} outside allowed range')
    if actual=='string':
        if len(value)<contract.get('minLength',0) or len(value)>contract.get('maxLength',len(value)): raise ValidationError(f'{path} outside allowed length')
    if actual=='array':
        for i,v in enumerate(value): validate_schema(v,contract.get('items',{}),f'{path}[{i}]')
    if actual=='object':
        missing=set(contract.get('required',[]))-value.keys()
        if missing: raise ValidationError(f'{path} missing {sorted(missing)}')
        props=contract.get('properties')
        if props is not None:
            if contract.get('additionalProperties') is False and value.keys()-props.keys(): raise ValidationError(f'{path} unexpected fields {sorted(value.keys()-props.keys())}')
            for k,v in value.items(): validate_schema(v,props.get(k,{}),f'{path}.{k}')

def error(code, message): return {'error':{'code':code,'message':message}}
def ident(row): return row['identifier']
def uid(row): return ident(row)['uuid']
def properties(row, fields=None):
    return [{'field_id':k,'label':k.replace('_',' ').title(),'value':copy.deepcopy(row.get(k))} for k in (fields if fields is not None else row.keys()) if k!='url']
def scalar(value):
    if isinstance(value,dict): return value.get('value_usd',value.get('value',value))
    return value

def flatten(value):
    if value is None: return []
    if isinstance(value,list): return [v for item in value for v in flatten(item)]
    if isinstance(value,dict): return [value[k] for k in ('uuid','permalink','value') if k in value]
    return [value]

class Replay:
    def __init__(self, fixture=None, state_path=None, log_path=None, turn=1):
        self.fixture=copy.deepcopy(fixture or {})
        self.data=copy.deepcopy(self.fixture.get('base_data') or json.loads(BASE.read_text()))
        self.state_path=Path(state_path) if state_path else None
        self.log_path=Path(log_path) if log_path else None
        self.turn=turn
        self.state=json.loads(self.state_path.read_text()) if self.state_path and self.state_path.exists() else {'lists':copy.deepcopy(self.data['lists']),'call_counts':{},'created_count':0}
        self.state.setdefault('call_counts',{})
        self.state.setdefault('created_count',0)
        for collection in self.fixture.get('empty_collections',[]): self.data['entities'][collection]=[]
        for rows in self.data['entities'].values():
            for row in rows:
                row.update(copy.deepcopy(self.fixture.get('overrides',{}).get(uid(row),{})))
        self.schemas={t['name']:t['inputSchema'] for t in TOOLS}
        self.persist()
    def persist(self):
        if self.state_path:
            self.state_path.parent.mkdir(parents=True,exist_ok=True)
            temporary=self.state_path.with_suffix('.tmp')
            temporary.write_text(json.dumps(self.state,indent=2)+'\n')
            temporary.replace(self.state_path)
    def call(self, tool, arguments):
        self.state['call_counts'][tool]=self.state['call_counts'].get(tool,0)+1
        number=self.state['call_counts'][tool]
        try:
            if tool not in self.schemas: raise ValidationError(f'Unknown tool: {tool}')
            validate_schema(arguments,self.schemas[tool])
            injected=next((r for r in self.fixture.get('errors',[]) if r['tool']==tool and (number==r.get('at',1) or r.get('persist') and number>=r.get('at',1))),None)
            if injected:
                result=error(injected['code'],injected.get('message','Synthetic service failure'))
            else:
                result=getattr(self,tool.removeprefix('cb_'))(**arguments)
        except (ValidationError,KeyError,ValueError,TypeError) as exc:
            result=error('VALIDATION_ERROR',str(exc))
        self.persist()
        event={'turn':self.turn,'tool':tool,'arguments':arguments,'result':result}
        if tool in MUTATIONS: event['state_after']=copy.deepcopy(self.state)
        if self.log_path:
            self.log_path.parent.mkdir(parents=True,exist_ok=True)
            with self.log_path.open('a') as out: out.write(json.dumps(event)+'\n')
        return result
    def collection(self,name):
        name=ALIASES.get(name,name)
        if name not in self.data['entities']: raise ValidationError(f'Unsupported fixture collection {name}; see cb_reference entities')
        return name
    def rows(self,collection): return self.data['entities'][self.collection(collection)]
    def record(self,key,collection='organizations'):
        found=[row for row in self.rows(collection) if key in (uid(row),ident(row)['permalink'])]
        if len(found)!=1: raise ValidationError(f'Unknown canonical entity identifier {key}')
        return found[0]
    def contracts(self,collection): return self.data['contracts'][self.collection(collection)]
    def reference(self,path=''):
        parts=path.strip('/').split('/')
        collection=ALIASES.get(parts[1],parts[1]) if len(parts)>1 and parts[0]=='entities' else None
        if collection in self.data['contracts'] and len(parts)>2 and parts[2]=='fields':
            fields=self.data['contracts'][collection]
            if len(parts)>3:
                if parts[3] not in fields: return {'path':path,'content':'Unknown fixture field. Available fields: '+', '.join(fields)}
                body=json.dumps({'field_id':parts[3],**fields[parts[3]]},indent=2)
            else:
                body='Field contracts for this synthetic fixture. Each entry exposes operators, values, and sortable status.\n'+json.dumps(fields,indent=2)
        elif collection and len(parts)>2 and parts[2]=='cards':
            body=json.dumps(self.data.get('card_contracts',{}),indent=2)
        elif path.startswith('guidance/') or path in ('operators','field_types'):
            body=('Use explicit field_ids; flat predicates are AND; includes values are OR and includes_all values are AND. query and predicates are mutually exclusive. Each query item is type=predicate; sub_query is outside this synthetic fixture contract and returns UNSUPPORTED_FIXTURE. Money values are USD integers; ISO dates are YYYY-MM-DD. after_id is last returned entity UUID; count is full matching count. Review entities/organization/fields or entities/funding_round/fields for operators and enum identifiers.')
        else:
            body='Available paths: entities; entities/organization/fields; entities/organization/cards; entities/funding_round/fields; guidance/search_query. Collections: organizations (organization.companies), funding_rounds, categories, locations, people. Full field contracts are in the collection fields response.'
        return {'path':path,'content':body}
    def entity_autocomplete(self,query,collection_ids=None,limit=10):
        collections=[self.collection(c.strip()) for c in collection_ids.split(',')] if collection_ids else list(self.data['entities'])
        q=query.casefold().strip()
        rows=[r for c in collections for r in self.rows(c) if q in ident(r)['value'].casefold() or q in ident(r)['permalink'] or q in str(r.get('aliases',[])).casefold()]
        return {'entities':[{'identifier':ident(r),'facet_ids':r.get('facet_ids',[]),'short_description':r.get('short_description')} for r in rows[:limit or 10]]}
    def expert_resolve_entity(self,name,collection_id=None,domains=None,context=None,cb_entity_get='default'):
        rows=self.rows(collection_id or 'organizations')
        if domains:
            from urllib.parse import urlparse
            hosts={urlparse(d if '://' in d else 'https://'+d).hostname.removeprefix('www.') for d in domains}
            matches=[r for r in rows if urlparse(r.get('website_url','')).hostname in hosts]
        else:
            q=name.casefold().strip()
            matches=[r for r in rows if q==ident(r)['value'].casefold() or q in ident(r)['value'].casefold() or q in [a.casefold() for a in r.get('aliases',[])]]
        if self.fixture.get('resolver_candidates'):
            matches=[self.record(i) for i in self.fixture['resolver_candidates']]
        if len(matches)==1:
            r=matches[0]
            result={'disambiguation':{'result_type':'match','entity':{'properties':{'identifier':ident(r),'short_description':r.get('short_description')},'confidence':0.95}}}
            if cb_entity_get is not None:
                result['entity']=self.entity_get(uid(r),**(cb_entity_get if isinstance(cb_entity_get,dict) else {}))
            return result
        return {'disambiguation':{'result_type':'candidates','candidates':[{'identifier':ident(r),'url':r.get('url'),'short_description':r.get('short_description')} for r in matches]}}
    def page(self,rows,after_id,limit):
        start=0
        if after_id:
            positions=[i for i,r in enumerate(rows) if uid(r)==after_id]
            if not positions: raise ValidationError('after_id must be a UUID present in this result set')
            start=positions[0]+1
        return rows[start:start+limit],start+limit<len(rows)
    def entity_get(self,entity_id,entity_def_id=None,field_ids=None,card_ids=None,after_id=None,related_entity_limit=100):
        if self.fixture.get('profile_error'):
            problem=self.fixture['profile_error']
            return error(problem['code'],problem.get('message','Profile retrieval unavailable'))
        collection=self.collection(entity_def_id or 'organizations')
        row=self.record(entity_id,collection)
        allowed=self.contracts(collection)
        if field_ids is not None and any(f not in allowed for f in field_ids): raise ValidationError('Unknown projection field; see reference fields')
        card_ids=card_ids if card_ids is not None else ['funding_rounds_list','founders_lookup','org_similarity_org_list']
        if after_id and len(card_ids)!=1: raise ValidationError('after_id requires exactly one card_id')
        cards=[]
        for card in card_ids:
            if card not in self.data['card_contracts']: raise ValidationError(f'Unknown card {card}; see entities/organization/cards')
            keys=self.data.get('cards',{}).get(uid(row),{}).get(card,[])
            target=self.data['card_contracts'][card]['entity_def_id']
            rows=[self.record(k,target) for k in keys]
            budget=max(1,(related_entity_limit or 100)//max(1,len(card_ids)))
            page,more=self.page(rows,after_id,min(budget,self.fixture.get('card_page_size',100)))
            cards.append({'card_id':card,'label':card.replace('_',' ').title(),'entity_def_id':target,'entities':[{'properties':properties(r)} for r in page],'has_more_entities':more})
        return {'collection_id':collection,'entity_def_id':ident(row)['entity_def_id'],'properties':properties(row,field_ids),'cards':cards}
    def predicate(self,row,p,collection):
        field=p.get('field_id'); op=p.get('operator_id'); values=p.get('values',[])
        contract=self.contracts(collection).get(field)
        if contract is None: raise ValidationError(f'Invalid field_id {field}')
        if op not in contract['operators']: raise ValidationError(f'Unsupported operator {op} for {field}; allowed: {contract["operators"]}')
        expected=2 if op=='between' else 1 if op in ('eq','not_eq','gt','gte','lt','lte','blank') else None
        if not values or expected is not None and len(values)!=expected: raise ValidationError(f'Invalid values count for {op}')
        ft=contract['field_type']
        if op=='blank':
            if len(values)!=1 or not isinstance(values[0],bool): raise ValidationError('blank requires one boolean')
            return (row.get(field) is None or row.get(field)==[]) == values[0]
        if ft in ('money','integer','decimal') and any(isinstance(v,bool) or not isinstance(v,(int,float)) for v in values): raise ValidationError(f'{field} requires numeric values')
        if ft.startswith('date'):
            for v in values:
                try: dt.date.fromisoformat(v)
                except (ValueError,TypeError): raise ValidationError(f'{field} requires YYYY-MM-DD dates')
        if 'enum_values' in contract and any(v not in contract['enum_values'] for v in values): raise ValidationError(f'Invalid enum for {field}; allowed {contract["enum_values"]}')
        if ft.startswith('identifier') and op in ('eq','not_eq','includes','includes_all','not_includes','not_includes_all'):
            valid={v for rows in self.data['entities'].values() for r in rows for v in (uid(r),ident(r)['permalink'])}
            if any(v not in valid for v in values): raise ValidationError(f'{field} requires known UUIDs or permalinks, not display labels')
        raw=row.get(field); got=scalar(raw); allvalues=flatten(raw)
        if op in ('in_list','not_in_list'):
            if any(v not in self.state['lists'] for v in values): raise ValidationError('Unknown saved-list UUID')
            answer=any(uid(row) in self.state['lists'][v]['entity_ids'] for v in values)
            return not answer if op=='not_in_list' else answer
        if op in ('contains','not_contains','starts'):
            text=' '.join(map(str,allvalues)).casefold()
            answer=any(text.startswith(str(v).casefold()) if op=='starts' else str(v).casefold() in text for v in values)
            return not answer if op=='not_contains' else answer
        if op in ('includes','not_includes','includes_all','not_includes_all'):
            answer=all(v in allvalues for v in values) if op.endswith('_all') else any(v in allvalues for v in values)
            return not answer if op.startswith('not_') else answer
        if raw is None: return False
        if op=='eq': return values[0] in allvalues if ft.startswith('identifier') else got==values[0]
        if op=='not_eq': return values[0] not in allvalues if ft.startswith('identifier') else got!=values[0]
        if op=='gt': return got>values[0]
        if op=='gte': return got>=values[0]
        if op=='lt': return got<values[0]
        if op=='lte': return got<=values[0]
        if op=='between': return values[0]<=got<=values[1]
        raise ValidationError(f'Unsupported operator {op}')
    def search_query(self,collection_id,field_ids=None,predicates=None,query=None,order=None,limit=20,after_id=None):
        collection=self.collection(collection_id)
        if predicates is not None and query is not None: raise ValidationError('query and predicates are mutually exclusive')
        if query and any(q.get('type')!='predicate' for q in query): return error('UNSUPPORTED_FIXTURE','This replay supports flat predicate query items; recursive subqueries are outside its coverage.')
        fields=field_ids if field_ids is not None else ['identifier','short_description']
        if any(f not in self.contracts(collection) for f in fields): raise ValidationError('Unknown projection field; see reference fields')
        rows=self.rows(collection)
        clauses=query if query is not None else predicates or []
        # Validate even for an empty result set; unknown filters must not silently pass.
        sample=rows[0] if rows else {'identifier':{'uuid':'','permalink':'','value':''}}
        for p in clauses: self.predicate(sample,p,collection)
        rows=[r for r in rows if all(self.predicate(r,p,collection) for p in clauses)]
        for o in reversed(order or []):
            f=o['field_id']; c=self.contracts(collection).get(f)
            if not c or not c['sortable']: raise ValidationError(f'{f} is not sortable')
            present=[r for r in rows if r.get(f) is not None]; absent=[r for r in rows if r.get(f) is None]
            present.sort(key=lambda r:scalar(r[f]),reverse=o.get('sort','asc')=='desc')
            rows=absent+present if o.get('nulls')=='first' else present+absent
        count=len(rows)
        page,_=self.page(rows,after_id,min(limit or 20,self.fixture.get('page_size',1000)))
        return {'collection_id':collection,'count':count,'entities':[{'uuid':uid(r),'url':r.get('url'),**{f:copy.deepcopy(r.get(f)) for f in fields}} for r in page],'response_status':200}
    def list_query(self):
        return {'company_lists':[{'list_id':k,'name':v['name'],'is_modifiable':True,'is_owner':True,'is_public':False,'identifiers_collection':{'collection_id':'identifiers','entities_count':len(v['entity_ids'])}} for k,v in self.state['lists'].items()],'response_status':200}
    def list_get(self,list_id,after_id=None):
        if list_id not in self.state['lists']: return error('NOT_FOUND','Saved list not found')
        rows=[self.record(i) for i in self.state['lists'][list_id]['entity_ids']]
        page,more=self.page(rows,after_id,self.fixture.get('list_page_size',1000))
        return {'list_id':list_id,'company_identifiers':[ident(r) for r in page],'total_count':len(rows),'next_after_id':uid(page[-1]) if more and page else None,'response_status':200}
    def list_create(self,name):
        if not name.strip(): raise ValidationError('List name cannot be blank')
        self.state['created_count']+=1
        key=str(uuid.uuid5(uuid.NAMESPACE_URL,f'crunchbase-synthetic-list:{name}:{self.state["created_count"]}'))
        self.state['lists'][key]={'name':name,'entity_ids':[]}
        return {'list_id':key,'list_name':name,'response_status':201}
    def list_add_entities(self,list_id,entity_ids):
        if list_id not in self.state['lists']: return error('NOT_FOUND','Saved list not found')
        valid={uid(r) for r in self.rows('organizations')}
        if any(i not in valid for i in entity_ids): raise ValidationError('entity_ids must be known organization UUIDs')
        actual=entity_ids[:-1] if self.fixture.get('partial_add') else entity_ids
        self.state['lists'][list_id]['entity_ids']=list(dict.fromkeys(self.state['lists'][list_id]['entity_ids']+actual))
        if self.fixture.get('uncertain_add') and self.state['call_counts'].get('cb_list_add_entities')==1: return error('SERVICE_UNCERTAIN','Connection ended after submission; commit state unknown to caller')
        return {'list_id':list_id,'submitted_entity_ids':entity_ids,'response_status':200}

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--fixture',required=True); parser.add_argument('--log',required=True); parser.add_argument('--state',required=True); parser.add_argument('--turn',type=int,default=1)
    args=parser.parse_args()
    replay=Replay(json.loads(Path(args.fixture).read_text()),args.state,args.log,args.turn)
    for line in sys.stdin:
        try:
            req=json.loads(line); rid=req.get('id'); method=req.get('method'); params=req.get('params',{})
            if rid is None: continue
            if method=='initialize': result={'protocolVersion':'2024-11-05','capabilities':{'tools':{}},'serverInfo':{'name':'crunchbase-synthetic-replay','version':'1.0.0'}}
            elif method=='ping': result={}
            elif method=='tools/list': result={'tools':TOOLS}
            elif method=='tools/call':
                response=replay.call(params['name'],params.get('arguments',{}))
                result={'content':[{'type':'text','text':json.dumps(response)}],'structuredContent':response,'isError':bool(response.get('error'))}
            else:
                print(json.dumps({'jsonrpc':'2.0','id':rid,'error':{'code':-32601,'message':'Method not found'}}),flush=True); continue
            print(json.dumps({'jsonrpc':'2.0','id':rid,'result':result}),flush=True)
        except Exception as exc:
            print(json.dumps({'jsonrpc':'2.0','id':req.get('id') if 'req' in locals() else None,'error':{'code':-32603,'message':str(exc)}}),flush=True)
if __name__=='__main__': main()
