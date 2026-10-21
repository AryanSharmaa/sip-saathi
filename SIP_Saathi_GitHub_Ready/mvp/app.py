from __future__ import annotations
import csv, json, os, re, pathlib
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel, Field
from fastapi.middleware.cors import CORSMiddleware

ROOT=pathlib.Path(__file__).resolve().parent
DATA=ROOT.parent/'discovery_engine'
app=FastAPI(title='SIP Saathi | guarded educational prototype',version='0.1.0')
app.add_middleware(CORSMiddleware,allow_origins=[],allow_methods=['GET','POST'],allow_headers=['Content-Type'])
SOURCES={
 'payment':'https://groww.in/help/mutual-funds/order/why-did-my-sip-installment-fail--36',
 'recovery':'https://groww.in/help/mutual-funds/mf-sip/autopay-request-failed---my-primary-account-is-having-insufficient-balance--how-can-i-pay-for-my-upcoming-sips--67',
 'skip':'https://groww.in/help/mutual-funds/mf-sip/how-to-skip-an-sip-instalment--79',
 'mandate':'https://groww.in/help/mutual-funds/mf-sip/how-to-change-autopay---bank-for-sip-on-groww--38',
 'education':'https://investor.sebi.gov.in/iematerial.html',
 'cancellation':'https://groww.in/help/mutual-funds/order/why-was-my-order-cancelled--68'
}
INTENTS=['failed_debit','unclear_status','autopay','nav_date','cashflow','performance','unrelated']
TEMPLATES={
 'failed_debit':('A failed deduction does not by itself tell us whether your SIP is active or cancelled. Groww lists possible payment, mandate, bank-detail and verification issues.','Check the installment status in My SIPs, then review the approved AutoPay and payment status. Groww describes available payment recovery methods; contact support if the status remains unclear.','payment'),
 'unclear_status':('An exchange approval, a debit message and an allotted mutual fund unit are different statuses. I cannot verify your particular transaction.','Check your SIP and order history in the app and the AMC confirmation. Ask Groww support to confirm the exact registration and payment status if the records conflict.','payment'),
 'autopay':('An AutoPay issue may result from the approval status, bank or linkage to a rejected mandate. A sufficient bank balance alone cannot rule out all causes.','In My SIPs, review which AutoPay is connected, then compare it against Groww’s official change-bank / mandate instructions. Do not share banking credentials here.','mandate'),
 'nav_date':('The debit date and the NAV allotment date need not always match. This experience cannot confirm which NAV applies to your transaction.','Check the transaction confirmation, published cut-offs, and Groww support if there is a discrepancy. Do not assume a processing delay means units are lost.','education'),
 'cashflow':('Your ability to cover essential expenses and obligations matters. There is no obligation to keep investing an amount that no longer fits your situation.','Review your budget and short-term needs. If you choose to skip an instalment, Groww documents that option and its timing limits.','skip'),
 'performance':('Mutual fund returns can fluctuate and short periods may disappoint. This assistant cannot tell you whether to continue or stop a particular investment.','Review the product risk and your own goals using SEBI’s investor education resources. For personalised decisions, consult a SEBI-registered investment adviser.','education'),
 'unrelated':('I cannot reliably determine your SIP situation from this description.','Check Groww’s official mutual-fund help centre or seek support. Avoid sharing banking or identity information here.','education')
}

class TextInput(BaseModel):
    text:str=Field(min_length=5,max_length=600)

PRIVATE_PATTERN=re.compile(r'\b[A-Z]{5}[0-9]{4}[A-Z]\b|\b\d{12,18}\b|\b(?:account number|pan number|otp|password|pin)\s*[:=#-]',re.I)
ADVICE_PATTERN=re.compile(r'\b(best fund|which fund|which stocks?|recommend (?:a )?(?:fund|stock)|guarantee(?:d)? returns?|buy or sell|should i buy|specific fund)\b',re.I)

def heuristic(text):
 s=text.lower()
 if re.search(r'nav|allotment',s):return 'nav_date'
 if re.search(r'job|salary|rent|loan|emi|budget|afford|expenses|cash|money for',s):return 'cashflow'
 if re.search(r'returns|negative|loss|market|performance|growth',s):return 'performance'
 if re.search(r'autopay|auto-pay|mandate',s):return 'autopay'
 if re.search(r'failed|missed|not debit|not deducted|payment|insufficient',s):return 'failed_debit'
 if re.search(r'register|status|pending|approved|successful|cancel',s):return 'unclear_status'
 return 'unrelated'

def llm_classify(text):
 from openai import OpenAI
 client=OpenAI(timeout=18)
 system=('You identify support intent ONLY, not investment advice. Choose one category from '+', '.join(INTENTS)+'. '
   'Return JSON with intent, confidence (0-1), evidence (literal short substring of user message). '
   'When mixed or unclear choose unrelated and low confidence. Never infer account status from text. No recommendations.')
 result=client.chat.completions.create(model=os.getenv('OPENAI_MODEL','gpt-4.1-mini'),temperature=0,
  response_format={'type':'json_object'},messages=[{'role':'system','content':system},{'role':'user','content':text}])
 return json.loads(result.choices[0].message.content)

def response_for(text):
 if PRIVATE_PATTERN.search(text):return {
  'status':'safe_fallback','engine':'privacy_gate','intent':'unrelated','confidence':0,
  'headline':'Please remove personal financial or identity details before continuing.',
  'next_step':'Do not share PAN, account numbers, OTPs, passwords or portfolio screenshots. Try describing the issue without them.',
  'source_url':SOURCES['education'],'quality_gate':'Blocked private-data input','disclaimer':'Education and process guidance only. Not investment advice.'}
 if ADVICE_PATTERN.search(text): return {
  'status':'safe_fallback','engine':'advice_gate','intent':'unrelated','confidence':0,
  'headline':'I cannot suggest funds, stocks or when to buy or sell.',
  'next_step':'Use SEBI education resources to understand risks and consider a registered investment adviser for personal advice.',
  'source_url':SOURCES['education'],'quality_gate':'Investment advice blocked','disclaimer':'Education and process guidance only. Not investment advice.'}
 ai_enabled=bool(os.getenv('OPENAI_API_KEY'))
 engine='OpenAI intent classifier' if ai_enabled else 'offline rules (NO AI KEY)'
 if ai_enabled:
  try:
   pred=llm_classify(text)
   intent=pred.get('intent','unrelated'); conf=float(pred.get('confidence',0)); evidence=str(pred.get('evidence',''))
   # Gate: exact user-grounded explanation, confidence threshold, fixed intent whitelist.
   passed=(intent in INTENTS and conf>=.82 and 0<len(evidence)<=100 and evidence.lower() in text.lower())
   # An investment-priority statement must not be reframed as an instruction to invest.
   if heuristic(text)=='cashflow' and intent!='cashflow':passed=False
  except Exception:
   passed=False; intent='unrelated';conf=0
  if not passed:
   intent='unrelated'; status='safe_fallback'; gate='AI output failed confidence / grounding / consistency check'
  else:status='passed';gate='Intent whitelist + evidence grounding + confidence >= 0.82'
 else:
  intent=heuristic(text);conf=0;status='demo_fallback';gate='Model unavailable: transparent deterministic fallback; AI NOT evaluated'
 a,b,key=TEMPLATES[intent]
 return {'status':status,'engine':engine,'intent':intent,'confidence':round(conf,3),'headline':a,
   'next_step':b,'source_url':SOURCES[key],'quality_gate':gate,
   'disclaimer':'Educational process information only. Not financial or investment advice; no account access or payment action.'}

@app.get('/',response_class=HTMLResponse)
def home():return (ROOT/'static'/'index.html').read_text()
@app.get('/discovery',response_class=HTMLResponse)
def discovery():return (ROOT/'static'/'discovery.html').read_text()
@app.post('/api/triage')
def triage(item:TextInput):return response_for(item.text)
@app.post('/api/discovery/tag')
def tag(item:TextInput):
 from sys import path
 path.insert(0,str(DATA))
 from engine import baseline_tag,llm_tag
 if os.getenv('OPENAI_API_KEY'):
  try:r=llm_tag(item.text);mode='OpenAI classification'
  except Exception:r=baseline_tag(item.text);mode='fallback (AI failed)'
 else:r=baseline_tag(item.text);mode='rule-based baseline, not AI'
 if r.get('confidence',0)<.75:r['needs_review']=True
 return {'mode':mode,**r}
@app.get('/api/discovery/insights')
def insights():
 from collections import Counter
 with (DATA/'conversations.csv').open() as f: rows=list(csv.DictReader(f))
 c=Counter(r['reference_primary_theme'] for r in rows)
 return {'sources':{'Reddit':25,'TradingQ&A':1},'n':len(rows),'counts':dict(c),
  'caveat':'Convenience-sampled self-reports, not representative; labels provisional and require human verification.',
  'examples':[{'id':r['id'],'source':r['source'],'summary':r['researcher_paraphrase'],'url':r['url'],'theme':r['reference_primary_theme']} for r in rows]}
@app.get('/health')
def health():return {'ok':True,'ai_configured':bool(os.getenv('OPENAI_API_KEY'))}
