"""SIP continuation public-feedback discovery engine (pilot):
- CSV ingestion of consented / publicly accessible, researcher-paraphrased units
- multitheme tagging + human-review-first for opportunity discovery
- Optional OpenAI LLM tagging via OPENAI_API_KEY (no silent simulated LLM call)
- 20-item reference-set agreement + uncertainty and abstention reporting
Ethics: Reddit/forum posts are biased and are NOT platform churn data.
"""
from __future__ import annotations
import os,csv,json,re,collections,argparse,pathlib
from typing import Dict
ROOT=pathlib.Path(__file__).resolve().parent
THEMES={
 'payment_failure':'Instalment could not be collected or paid due to technical or mandate failures',
 'status_uncertainty':'Confusion about SIP status, whether registration/payment succeeded, or penalty',
 'trust_reliability':'Perceived reliability, service, transparency, or payment/NAV distrust',
 'expectation_gap':'Performance or compounding did not match expectations',
 'cashflow_stress':'SIP competes with essential needs, income, debts, or buffer',
 'goal_change':'Personal financial priorities or goals changed',
 'social_influence':'Advice or pressure from family, friends, content creators or community',
 'product_literacy':'Misunderstood SIP mechanics, terminology, options, or risk',
}
# Baseline is deliberately simple for transparent validation; NOT an AI quality claim.
KEYWORDS={
 'payment_failure': ['autopay','auto pay','payment fail','debit fail','service error','sip debits','automatically fail','debit did not'],
 'status_uncertainty':['whether','marked failed','registered','registration','uncertain','unclear','not know','could not tell','mismatch','penalt','cancel','status','mandate'],
 'trust_reliability':['distrust','reliability','unresolved','platform','different nav','service'],
 'expectation_gap':['negative returns','small to matter','disappoint','flat returns','underperform','losses','return','grow'],
 'cashflow_stress':['income','salary','loan','debt','savings','funds','ability','charges'],
 'goal_change':['another need','land purchase','redirect','priority','priorities','goal'],
 'social_influence':['recommendation','advisor','family','youtube','reddit','forum','others'],
 'product_literacy':['difference','option','not understand','why','terminology','representation','allocation'],
}

def baseline_tag(text: str)->dict:
 s=text.lower()
 score={k:sum(1 for term in kws if term in s) for k,kws in KEYWORDS.items()}
 rank=sorted(score,key=lambda k:(-score[k],list(THEMES).index(k)))
 if score[rank[0]] == 0:
  return {'theme':'status_uncertainty','confidence':0.0,'needs_review':True,'evidence_span':''}
 k=rank[0]; hit=next((term for term in KEYWORDS[k] if term in s),'')
 return {'theme':k,'confidence':min(.75,.35+.1*score[k]),'needs_review':True,'evidence_span':hit}

def llm_tag(text: str)->dict:
 """Single LLM inference per independent opinion, JSON and confidence gated."""
 from openai import OpenAI
 if not os.getenv('OPENAI_API_KEY'):raise RuntimeError('OPENAI_API_KEY missing: LLM not run; use --mode baseline for transparent exploratory tagging')
 client=OpenAI(timeout=25)
 prompt='Choose the single primary cause from these codes: '+json.dumps(THEMES)+'. Do not infer demographic status or actual churn. Output JSON with theme, confidence (0 to 1), evidence_span (exact brief phrase from input), needs_review (boolean). If ambiguous, set needs_review true and confidence below .7.'
 out=client.chat.completions.create(model=os.getenv('OPENAI_MODEL','gpt-4.1-mini'),temperature=0,response_format={'type':'json_object'},messages=[{'role':'system','content':prompt},{'role':'user','content':text}])
 ob=json.loads(out.choices[0].message.content)
 if ob.get('theme') not in THEMES: raise ValueError('Unknown theme returned')
 ob['confidence']=max(0,min(1,float(ob.get('confidence',0))))
 if ob['confidence']<.75 or not ob.get('evidence_span') or ob['evidence_span'].lower() not in text.lower():ob['needs_review']=True
 return ob

def run(mode='baseline'):
 if mode=='llm' and not os.getenv('OPENAI_API_KEY'):
  raise SystemExit('OPENAI_API_KEY missing; no LLM eval performed (baseline output remains separate)')
 with (ROOT/'conversations.csv').open(newline='') as f:rows=list(csv.DictReader(f))
 predictions=[]
 for r in rows:
  try: ans=(llm_tag if mode=='llm' else baseline_tag)(r['researcher_paraphrase'])
  except Exception as e: ans={'theme':'','confidence':0,'needs_review':True,'error':str(e)}
  predictions.append({**r,'predicted_theme':ans['theme'],'confidence':ans['confidence'],'needs_review':ans['needs_review'],'evidence_span':ans.get('evidence_span',''),'error':ans.get('error','')})
 out=ROOT/f'predictions_{mode}.csv'; cols=list(predictions[0]);
 with out.open('w',newline='') as f:w=csv.DictWriter(f,fieldnames=cols);w.writeheader();w.writerows(predictions)
 gold=predictions[:20];correct=sum(r['predicted_theme']==r['reference_primary_theme'] for r in gold)
 flagged=sum(bool(r['needs_review']) for r in gold)
 totals=collections.Counter(r['reference_primary_theme'] for r in rows)
 metric={'mode':mode,'n_corpus':len(rows),'n_reference':len(gold),'reference_agreement_count':correct,'reference_agreement_pct':round(100*correct/len(gold),1),'reference_review_flags':flagged,'reference_theme_counts':dict(totals),'predictions_csv':str(out),'important':'Provisional researcher labels. Baseline is keyword-based, not LLM performance. No evidence of representative churn rates.'}
 (ROOT/f'eval_{mode}.json').write_text(json.dumps(metric,indent=2));print(json.dumps(metric,indent=2))
 for x in gold:
  if x['reference_primary_theme']!=x['predicted_theme']:print('DISAGREEMENT',x['id'],x['reference_primary_theme'],'vs',x['predicted_theme'])

if __name__=='__main__':
 a=argparse.ArgumentParser();a.add_argument('--mode',choices=['baseline','llm'],default='baseline');run(**vars(a.parse_args()))
