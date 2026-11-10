#!/usr/bin/env python3
"""Versioned deterministic GTM scoring. Standard library, Python 3.10+. No network."""
from __future__ import annotations
import argparse
import csv
import hashlib
import json
import math
import sys
from datetime import date
from pathlib import Path
from urllib.parse import urlsplit

SCHEMA_VERSION = 1
RUBRIC_VERSION = 'gtm-1'
WEIGHTS = {'growth': 40, 'heat': 30, 'funding': 30}
GROWTH = {'p100_positive_high': 100, 'p200_positive_low': 70, 'p300_neutral': 40,
          'p400_negative_low': 15, 'p500_negative_high': 0}
RAISE = {'p100_positive_high': 75, 'p200_positive_low': 40, 'p300_neutral': 0,
         'p400_negative_low': 0, 'p500_negative_high': 0}
CRM_COLUMNS = {'crm_id':'CRM ID','crm_name':'CRM Account Name','owner':'Owner','open_deals':'Open deals',
               'deal_stage':'Deal stage','open_amount':'Open amount','open_amount_currency':'Open amount currency',
               'open_amount_status':'Open amount status','next_close_date':'Next close date',
               'won_deals':'Won deals','last_won_date':'Last won date','next_step':'Next step'}
NOT_NEW_MONEY = {'secondary_market', 'post_ipo_secondary', 'non_equity_assistance'}


def number(value, field, low=None, high=None):
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (float, int)) or not math.isfinite(value):
        raise ValueError(f'{field} must be a finite number or null')
    if (low is not None and value < low) or (high is not None and value > high):
        raise ValueError(f'{field} outside supported range')
    return value


def iso(value, field, today=None):
    if not isinstance(value, str) or len(value) != 10:
        raise ValueError(f'{field} must be a day-precision ISO date')
    result = date.fromisoformat(value)
    if today and result > today:
        raise ValueError(f'{field} is a future completed-event date')
    return result


def domain(value):
    if not value:
        return ''
    if not isinstance(value, str):
        raise ValueError('domain must be text')
    parsed = urlsplit(value if '://' in value else 'https://' + value)
    if parsed.username or parsed.password:
        raise ValueError('domain must not contain credentials')
    host = (parsed.hostname or '').rstrip('.').lower()
    return host[4:] if host.startswith('www.') else host


def csv_cell(value):
    if isinstance(value, str) and value.lstrip().startswith(('=', '+', '-', '@', '\t', '\r')):
        return "'" + value
    return value


def months_between(event, today):
    return (today.year-event.year)*12 + today.month-event.month - (today.day < event.day)


def normalize(candidate, today):
    c = dict(candidate)
    for field in ('uuid', 'permalink', 'name', 'url'):
        if not isinstance(c.get(field), str) or not c[field].strip():
            raise ValueError(f'every confirmed candidate needs canonical {field}')
    u = urlsplit(c['url'])
    if u.scheme != 'https' or u.hostname not in ('www.crunchbase.com', 'crunchbase.com') or u.path.rstrip('/') != '/organization/' + c['permalink']:
        raise ValueError('url must be the returned Crunchbase organization profile URL')
    c['domain'] = domain(c.get('domain'))
    for field in ('growth_score', 'heat_score'):
        number(c.get(field), field, 0, 100)
    number(c.get('heat_delta'), 'heat_delta', -100, 100)
    for field in ('last_funding_usd', 'last_fund_usd'):
        number(c.get(field), field, 0)
    for field in ('last_funding_at', 'last_fund_at', 'last_leadership_hire', 'created_at', 'closed_on', 'last_layoff_date'):
        if c.get(field) is not None:
            iso(c[field], field, today)
    for field, tiers in (('growth_tier', GROWTH), ('funding_tier', RAISE)):
        if c.get(field) is not None and c[field] not in tiers:
            raise ValueError(f'unrecognized {field}; resolve current connector contract')
    crm = c.get('crm_accounts', [])
    if not isinstance(crm, list): raise ValueError('crm_accounts must be a list')
    by_id = {}
    for account in crm:
        if not isinstance(account, dict) or set(account)-set(CRM_COLUMNS):
            raise ValueError('unsupported CRM passthrough field')
        if not isinstance(account.get('crm_id'), str) or not account['crm_id'].strip():
            raise ValueError('CRM passthrough requires stable crm_id')
        for key, value in account.items():
            if value is not None and not isinstance(value, (str,int,float)):
                raise ValueError('CRM passthrough values must be scalar')
            if isinstance(value, (int,float)): number(value, 'CRM '+key)
        if account['crm_id'] in by_id and by_id[account['crm_id']] != account:
            raise ValueError('conflicting passthrough data for one CRM ID')
        by_id[account['crm_id']] = account
    c['crm_accounts'] = [by_id[key] for key in sorted(by_id)]
    return c


def observation(c, field, today):
    obs = c.get(field)
    if obs is None:
        return False
    if not isinstance(obs, dict) or obs.get('source') != 'Crunchbase' or obs.get('complete') is not True:
        raise ValueError(f'{field} requires complete Crunchbase provenance')
    if iso(obs.get('as_of'), field + '.as_of') != today:
        raise ValueError(f'{field} must match this run as_of')
    if not isinstance(obs.get('query_scope'), str) or not obs['query_scope'].strip():
        raise ValueError(f'{field} requires query_scope')
    return True


def factor_points(c, today):
    # One returned growth measurement suffices; a missing tier is not numeric zero.
    growth = [v for v in (GROWTH.get(c.get('growth_tier')), c.get('growth_score')) if v is not None]
    heat = c.get('heat_score')
    points = {'growth': sum(growth)/len(growth) if growth else None,
              'heat': max(0, min(100, heat + .5*(c.get('heat_delta') or 0))) if heat is not None else None}
    events = []
    if c.get('last_funding_at') and c.get('last_funding_type') and c['last_funding_type'] not in NOT_NEW_MONEY:
        events.append(iso(c['last_funding_at'], 'last_funding_at', today))
    if c.get('last_fund_at'):
        events.append(iso(c['last_fund_at'], 'last_fund_at', today))
    # A missing completed event is zero only for a fully checked scoped observation.
    history_complete = observation(c, 'funding_observation', today)
    pred_complete = observation(c, 'prediction_observation', today)
    recency = None
    if events:
        m = months_between(max(events), today)
        recency = 100 if m <= 6 else 75 if m <= 12 else 50 if m <= 24 else 25 if m <= 36 else 0
    elif history_complete and c['funding_observation'].get('no_completed_funding') is True:
        recency = 0
    predicted = RAISE.get(c.get('funding_tier'))
    if predicted is None and pred_complete and c['prediction_observation'].get('no_prediction') is True:
        predicted = 0
    # max is established when both components are known, or one reaches the maximum.
    funding = max(recency, predicted) if recency is not None and predicted is not None else (100 if recency == 100 else None)
    if c.get('ipo_status') == 'public':
        funding = 50
    points['funding'] = funding
    points['raise'] = {'p100_positive_high':100, 'p200_positive_low':75, 'p300_neutral':40,
                       'p400_negative_low':15, 'p500_negative_high':0}.get(c.get('funding_tier'))
    return points


def rubric_config(data):
    config = data.get('rubric') or {}
    weights = config.get('weights', WEIGHTS)
    if not isinstance(weights, dict) or not weights or set(weights)-{'growth','heat','funding','raise'}:
        raise ValueError('unsupported weights')
    for key, value in weights.items(): number(value, 'weight '+key, 0)
    if sum(weights.values()) <= 0: raise ValueError('weights must sum to a positive value')
    tiers = config.get('tiers', [70, 50])
    if not isinstance(tiers, list) or len(tiers) != 2: raise ValueError('two tier cutoffs required')
    for t in tiers: number(t, 'tier', 0, 100)
    if tiers[0] <= tiers[1]: raise ValueError('A threshold must exceed B')
    bonus = config.get('customer_bonus', 10)
    number(bonus, 'customer_bonus', 0, 100)
    return {'version': RUBRIC_VERSION, 'weights': weights, 'tiers': tiers, 'customer_bonus': bonus}


def score_candidate(candidate, today, config):
    c = normalize(candidate, today)
    pts = factor_points(c, today)
    required = [key for key, weight in config['weights'].items() if weight > 0]
    missing = [key for key in required if pts[key] is None]
    # The caller must retain returned similarity evidence; no model-assigned bonus.
    peers = c.get('customer_peer') or []
    if any(not isinstance(p, dict) or not p.get('customer') or p.get('dir') not in ('fwd','rev') or not p.get('shared') for p in peers):
        raise ValueError('customer_peer requires customer, fwd/rev direction and shared micro-industries')
    if any(p['customer'] in (c['uuid'], c['permalink']) for p in peers):
        raise ValueError('an account cannot receive a bonus for being its own customer peer')
    bonus = config['customer_bonus'] if peers else 0
    score = None if missing else int(round(min(100, sum(config['weights'][k]*pts[k] for k in required)/sum(config['weights'].values()) + bonus)))
    closed = c.get('operating_status') == 'closed' or c.get('status') == 'closed'
    tier = None if score is None or closed else 'A' if score >= config['tiers'][0] else 'B' if score >= config['tiers'][1] else 'C'
    flags = []
    if closed: flags.append('closed; review routing')
    if c.get('status') == 'was_acquired': flags.append('acquired; confirm account ownership')
    if c.get('heat_delta') is not None and c['heat_delta'] <= -15: flags.append('media attention falling')
    if c.get('last_layoff_date') and months_between(iso(c['last_layoff_date'], 'last_layoff_date'), today) < 12: flags.append('reported layoffs within 12 months')
    return {**c, 'score': score, 'tier': tier, 'status': 'closed' if closed else 'insufficient_evidence' if missing else 'scored',
            'points': pts, 'customer_bonus': bonus, 'coverage': {'observed':len(required)-len(missing), 'required':len(required), 'missing':missing},
            'risk_flags': flags, 'rubric_version': RUBRIC_VERSION}


def canonical_rows(candidates, today):
    rows = {}
    for candidate in candidates:
        c = normalize(candidate, today)
        if c['uuid'] in rows and rows[c['uuid']] != c:
            raise ValueError('conflicting duplicate canonical UUID; reconcile evidence before scoring')
        rows[c['uuid']] = c
    return list(rows.values())


def run(data, workflow):
    if not isinstance(data, dict): raise ValueError('input must be an object')
    json.dumps(data, allow_nan=False)
    if not isinstance(data.get('candidates'), list): raise ValueError('candidates must be a list')
    if data.get('schema_version') != SCHEMA_VERSION: raise ValueError('schema_version must be 1')
    run = data.get('run') or {}
    today = iso(run.get('today'), 'run.today')
    if run.get('complete') is not True: raise ValueError('complete retrieval required for this scoring batch')
    if not isinstance(run.get('scope_id'), str) or not run['scope_id'].strip(): raise ValueError('run.scope_id required')
    config = rubric_config(data)
    candidates = canonical_rows(data.get('candidates', []), today)
    crm_owners = {}
    for c in candidates:
        for record in c.get('crm_accounts', []):
            existing = crm_owners.setdefault(record['crm_id'], c['uuid'])
            if existing != c['uuid']: raise ValueError('one CRM ID maps to conflicting canonical organizations')
    ex = data.get('exclude') or {}
    if ex.get('names'): raise ValueError('resolve name exclusions to canonical UUIDs before scoring')
    domains = {domain(v) for v in ex.get('domains', []) if v}
    seed_rows = data.get('seeds', [])
    if not isinstance(seed_rows, list) or any(not isinstance(seed, dict) or not isinstance(seed.get('uuid'), str) or not seed['uuid'] for seed in seed_rows):
        raise ValueError('seeds require canonical UUIDs')
    seeds = {seed['uuid'] for seed in seed_rows}
    seed_keys = seeds | {seed['permalink'] for seed in seed_rows if seed.get('permalink')}
    for c in candidates:
        similar = c.get('similar', [])
        if not isinstance(similar, list): raise ValueError('similar must be a list')
        for evidence in similar:
            if not isinstance(evidence, dict) or evidence.get('seed') not in seed_keys or evidence.get('dir') not in ('fwd','rev') or not isinstance(evidence.get('shared'), list) or not evidence['shared'] or any(not isinstance(v,str) or not v for v in evidence['shared']):
                raise ValueError('similarity requires an accepted canonical seed, direction and shared micro-industries')
            number(evidence.get('score'), 'similarity score', 0, 100)
    if run.get('mode') in ('lookalike','mixed') and not seeds: raise ValueError('lookalike modes require accepted canonical seeds')
    removed, rows = [], []
    for c in candidates:
        if workflow == 'prospect-finder' and (c['uuid'] in seeds or c['uuid'] in ex.get('uuids', []) or c['permalink'] in ex.get('permalinks', []) or (c['domain'] and c['domain'] in domains)):
            removed.append(c['uuid']); continue
        r = score_candidate(c, today, config)
        if workflow == 'prospect-finder' and run.get('mode') == 'lookalike' and not any(x.get('shared') for x in c.get('similar', [])):
            removed.append(c['uuid']); continue
        rows.append(r)
    rows.sort(key=lambda r: (r['status'] != 'scored', r['score'] is None, -(r['score'] or 0), r['name'].casefold(), r['uuid']))
    ranked = 0
    for row in rows:
        if row['status'] == 'scored': ranked += 1; row['rank'] = ranked
        else: row['rank'] = None
    count = run.get('count', max(1, len(rows)))
    if isinstance(count, bool) or not isinstance(count, int) or count < 1: raise ValueError('run.count must be positive integer')
    # Preserve all reconciled inputs for prioritization, including unscored accounts.
    selected = rows[:count] if workflow == 'prospect-finder' else rows
    if workflow == 'prospect-finder' and run.get('mode') == 'mixed':
        look_count = run.get('lookalike_count')
        if isinstance(look_count, bool) or not isinstance(look_count, int) or not 0 <= look_count <= count:
            raise ValueError('mixed mode requires accepted lookalike_count between zero and count')
        looks = [r for r in rows if any(x.get('shared') for x in r.get('similar', []))]
        icps = [r for r in rows if not any(x.get('shared') for x in r.get('similar', []))]
        chosen = {r['uuid'] for r in looks[:look_count] + icps[:count-look_count]}
        selected = [r for r in rows if r['uuid'] in chosen]
    scope = {'scope_id':run['scope_id'], 'definition':data.get('definition'), 'exclude':{k:sorted(set(v)) for k,v in ex.items()},
             'seeds':sorted(seeds), 'mode':run.get('mode')}
    if workflow == 'account-prioritizer': scope['book'] = sorted(r['uuid'] for r in rows)
    return {'schema_version':1, 'rubric_version':RUBRIC_VERSION, 'workflow':workflow, 'as_of':today.isoformat(),
            'scope_id':run['scope_id'], 'scope':scope, 'rubric':config, 'complete':True, 'input_count':len(candidates),
            'excluded_uuids':removed, 'eligible_count':len(rows), 'shown':len(selected),
            'pool_scored_count':sum(r['status']=='scored' for r in rows),
            'pool_unscored_count':sum(r['status']=='insufficient_evidence' for r in rows),
            'scored_count':sum(r['status']=='scored' for r in selected),
            'unscored_count':sum(r['status']=='insufficient_evidence' for r in selected), 'rows':selected, 'scope_rows':rows,
            'list_uuids':[r['uuid'] for r in selected if r['status']=='scored']}


def write_csv(path, rows, output_format='csv'):
    if output_format not in ('csv','clay','crm','hubspot'): raise ValueError('unsupported export format')
    columns = ['UUID','Permalink','Name','Domain','Tier','Score','Status','Rank','Group','Coverage','Missing factors','Crunchbase profile'] + list(CRM_COLUMNS.values())
    with Path(path).open('w', encoding='utf-8-sig', newline='') as out:
        mappings = {
            'csv': {},
            'clay': {'UUID':'Crunchbase UUID','Tier':'CB Tier','Score':'CB Score','Status':'CB Score Status','Coverage':'CB Coverage'},
            'crm': {'UUID':'Crunchbase_UUID__c','Tier':'CB_Tier__c','Score':'CB_Score__c','Status':'CB_Score_Status__c','Coverage':'CB_Coverage__c','Crunchbase profile':'Crunchbase_Profile__c','CRM ID':'Id'},
            'hubspot': {'UUID':'Crunchbase UUID','Tier':'CB Tier','Score':'CB Score','Status':'CB Score Status','Coverage':'CB Coverage','CRM ID':'Record ID'},
        }
        writer = csv.writer(out); writer.writerow([mappings[output_format].get(c,c) for c in columns])
        for r in rows:
            base = [r['uuid'],r['permalink'],r['name'],r['domain'],r['tier'],r['score'],r['status'],r['rank'],r.get('segment',''),f"{r['coverage']['observed']}/{r['coverage']['required']}",', '.join(r['coverage']['missing']),r['url']]
            # Separate CRM records stay separate; never merge distinct CRM IDs by company name.
            for crm in r.get('crm_accounts') or [{}]:
                writer.writerow([csv_cell(v) for v in base + [crm.get(key) for key in CRM_COLUMNS]])



def state_diff(result, state):
    fingerprint = hashlib.sha256(json.dumps({'scope':result['scope'],'rubric':result['rubric'],'workflow':result['workflow']},sort_keys=True).encode()).hexdigest()
    if state is not None and (state.get('schema_version') != 1 or not isinstance(state.get('accounts'), dict)):
        raise ValueError('unsupported or corrupted state; preserve file and establish a new baseline explicitly')
    if state is not None and iso(state.get('as_of'), 'state.as_of') > iso(result['as_of'], 'as_of'):
        raise ValueError('state is newer than this run')
    reset = state is None or state.get('fingerprint') != fingerprint
    if state is not None:
        if state.get('rubric_version') != RUBRIC_VERSION: raise ValueError('unsupported state rubric version')
        stored_config = rubric_config({'rubric':state.get('rubric')})
        if not isinstance(state.get('fingerprint'), str) or len(state['fingerprint']) != 64:
            raise ValueError('corrupted state fingerprint')
        for identity, row in state['accounts'].items():
            if not isinstance(identity, str) or not isinstance(row, dict) or row.get('status') not in ('scored','closed','insufficient_evidence') or row.get('tier') not in ('A','B','C',None):
                raise ValueError('corrupted account state')
            value = number(row.get('score'), 'state score', 0, 100)
            if row['status'] == 'scored':
                if value is None: raise ValueError('scored state needs a score')
                expected = 'A' if value >= stored_config['tiers'][0] else 'B' if value >= stored_config['tiers'][1] else 'C'
                if row.get('tier') != expected: raise ValueError('state tier disagrees with score')
            elif row.get('tier') is not None or (row['status'] == 'insufficient_evidence' and value is not None):
                raise ValueError('unscored/closed state has invalid eligibility')
    old = {} if reset else state['accounts']
    accounts = {r['uuid']:{'tier':r['tier'],'score':r['score'],'status':r['status'],
                          'points':r['points'], 'coverage':r['coverage'], 'customer_bonus':r['customer_bonus'],
                          'facts':{k:r.get(k) for k in ('growth_tier','growth_score','heat_score','heat_delta','funding_tier','last_funding_at','last_fund_at','operating_status','last_layoff_date')}}
                for r in result['scope_rows']}
    changes = [] if reset else [{'uuid':k,'before':old.get(k),'after':v} for k,v in accounts.items() if old.get(k) != v]
    return {'baseline':reset,'changes':changes,'removed_uuids':sorted(set(old)-set(accounts))}, {'schema_version':1,'rubric_version':RUBRIC_VERSION,'fingerprint':fingerprint,'as_of':result['as_of'],'rubric':result['rubric'],'accounts':accounts}


def main(workflow):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['score'])
    parser.add_argument('--input', required=True); parser.add_argument('--csv'); parser.add_argument('--state')
    parser.add_argument('--format', choices=['csv','clay','crm','hubspot'], default='csv')
    parser.add_argument('--write-state', action='store_true')
    args = parser.parse_args()
    try:
        data = json.loads(Path(args.input).read_text())
        result = run(data, workflow)
        next_state = None
        if args.state:
            path = Path(args.state)
            state = json.loads(path.read_text()) if path.exists() else None
            result['monitoring'], next_state = state_diff(result, state)
        elif args.write_state:
            raise ValueError('--write-state requires --state')
        # Validate serialized output before any state mutation.
        json.dumps(result, allow_nan=False)
        if args.csv:
            Path(args.csv).parent.mkdir(parents=True, exist_ok=True)
            write_csv(args.csv, result['rows'], args.format); result['export_format'] = args.format; result['csv'] = str(Path(args.csv).resolve())
        # Deliver and flush the full result before advancing monitoring state.
        # A broken output pipe must leave the previous baseline intact.
        print(json.dumps(result, indent=2, allow_nan=False), flush=True)
        if next_state and args.write_state:
            path.parent.mkdir(parents=True, exist_ok=True)
            temp = path.with_suffix(path.suffix+'.tmp'); temp.write_text(json.dumps(next_state,sort_keys=True,indent=2)+'\n'); temp.replace(path)
    except (ValueError, TypeError, KeyError, OSError) as exc:
        print('error: '+str(exc), file=sys.stderr); return 2
    return 0
