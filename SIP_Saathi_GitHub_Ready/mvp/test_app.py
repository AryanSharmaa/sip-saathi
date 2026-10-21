"""Local checks, separate from LLM output quality measurement."""
import unittest
from fastapi.testclient import TestClient
from mvp.app import app,response_for

class QualityGateTests(unittest.TestCase):
 def setUp(self):self.c=TestClient(app)
 def test_routes(self):
  self.assertEqual(self.c.get('/health').status_code,200)
  self.assertIn('SIP Saathi',self.c.get('/').text)
  self.assertIn('Public-feedback discovery engine',self.c.get('/discovery').text)
  self.assertEqual(self.c.get('/api/discovery/insights').json()['n'],26)
 def test_private_data_block(self):
  v=response_for('My PAN is ABCDE1234F what now')
  self.assertEqual(v['status'],'safe_fallback');self.assertIn('private',v['quality_gate'].lower())
 def test_advice_block(self):
  v=response_for('Can you recommend a fund for me?')
  self.assertEqual(v['status'],'safe_fallback');self.assertIn('funds',v['headline'])
 def test_cashflow_does_not_pressure(self):
  v=response_for('My salary was delayed and I need to skip SIP for rent')
  self.assertEqual(v['intent'],'cashflow');self.assertIn('skip',v['next_step'].lower())
  self.assertNotIn('must continue',v['next_step'].lower())
 def test_limited_sourced_content(self):
  for query in ['My debit failed and I have enough balance','The NAV date is not same as SIP date','My SIP status is pending']:
   v=response_for(query)
   self.assertTrue(v['source_url'].startswith('https://'))
   self.assertIn('not',v['disclaimer'].lower())
 def test_tagging_endpoint(self):
  v=self.c.post('/api/discovery/tag',json={'text':'My SIP mandate was rejected and payment failed.'})
  self.assertEqual(v.status_code,200)
  self.assertIn('needs_review',v.json())
 def test_payload_limits(self):
  self.assertEqual(self.c.post('/api/triage',json={'text':'x'}).status_code,422)
  self.assertEqual(self.c.post('/api/triage',json={'text':'a'*601}).status_code,422)
if __name__=='__main__':unittest.main()
