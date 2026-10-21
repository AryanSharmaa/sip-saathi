"""REAL model gate evaluation against 20 frozen, independently verified gold items.
Do not run without OPENAI_API_KEY; avoid misleading zero-key fallback accuracy.
"""
import os,sys,csv,pathlib,json
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
from mvp.app import response_for
p=pathlib.Path(__file__).resolve().parents[1]
rows=list(csv.DictReader(open(p/'discovery_engine/conversations.csv')))[:20]
allowed={
 'payment_failure':{'failed_debit','autopay'},'status_uncertainty':{'unclear_status','failed_debit','autopay','nav_date'},
 'trust_reliability':{'nav_date','unclear_status','failed_debit'},'expectation_gap':{'performance'},
 'cashflow_stress':{'cashflow'},'goal_change':{'cashflow'},'social_influence':{'unrelated','performance'},
 'product_literacy':{'unrelated','unclear_status','nav_date'}
}
if not os.getenv('OPENAI_API_KEY'):
 print('PENDING: OPENAI_API_KEY missing. No live model calls and no AI quality result.');raise SystemExit(2)
results=[]
for row in rows:
 out=response_for(row['researcher_paraphrase'])
 gold=row['reference_primary_theme'];actual=out['intent'];passed=out['status']=='passed'
 results.append({'id':row['id'],'reference_theme':gold,'allowed_support_intents':','.join(sorted(allowed[gold])), 'model_intent':actual,'gate_passed':passed,'intent_acceptable':actual in allowed[gold], 'quality_gate':out['quality_gate']})
correct=sum(r['intent_acceptable'] for r in results)
coverage=sum(r['gate_passed'] for r in results)
with open(p/'mvp/ai_eval_actual.csv','w',newline='') as f:w=csv.DictWriter(f,fieldnames=list(results[0]));w.writeheader();w.writerows(results)
print(json.dumps({'evaluated':len(results),'acceptable_intents':correct,'acceptable_pct':round(100*correct/len(results),1),'gate_accepted':coverage,'gate_acceptance_pct':round(100*coverage/len(results),1),'caveat':'Reference categories mapped to several permissible support intents; inspect errors manually.'},indent=2))
