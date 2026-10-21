# SIP Saathi + Discovery Engine — ready to deploy on Render

A working demo site with two pages:

- `/` — SIP Saathi investor support prototype.
- `/discovery` — discovery dashboard and live classifier testing.

This is an **independent Groww-inspired academic prototype**, not Groww's actual service.

## Deploy through the browser (GitHub + Render)

1. Create a new repository on GitHub. Upload the **contents of this folder** so that `render.yaml` is at the repository root. Keep `mvp/` and `discovery_engine/` folder structure intact. Do not upload API keys.
2. Sign in to https://dashboard.render.com/ with GitHub and select **New → Blueprint**, pointing it at the repository's `render.yaml`. Choose the Free service option when offered. Alternatively choose **New → Web Service**, configure:
   - Runtime: Python
   - Build command: `pip install -r mvp/requirements.txt`
   - Start command: `uvicorn mvp.app:app --host 0.0.0.0 --port $PORT`
   - Health check: `/health`
3. Render may request an `OPENAI_API_KEY` because it appears in `render.yaml`. Provide it **only as a secure Render environment variable**, not in GitHub or chat. If you do not have a key yet, remove its block from the YAML and deploy the non-AI fallback first. The app must **not** be presented as a functional AI-native MVP until a genuine AI key and eval measurements are configured.
4. Test `https://YOUR-SITE.onrender.com/` and `https://YOUR-SITE.onrender.com/discovery` in an incognito browser. Both links share one hosted application.

## Run locally

```bash
pip install -r mvp/requirements.txt
uvicorn mvp.app:app --host 127.0.0.1 --port 8000
python -m unittest mvp.test_app -v
```

Visit `http://127.0.0.1:8000` and `/discovery`.

## AI integrity and costs

- Without an AI key, the MVP produces explicitly labelled rule-based demo/fallback responses and the discovery engine labels classifications as a baseline. It does **not** pretend to produce AI outputs.
- With an `OPENAI_API_KEY`, model classification goes through confidence, allowed-intent, grounded evidence, and investment advice/privacy checks. Configure the real model and run `python discovery_engine/engine.py --mode llm` and `python mvp/evaluate_ai.py`, then manually review errors against the 20-item provisional label set before making AI-quality claims.
- Paid LLM API usage can incur charges. Hosting also has limits, and Render Free services sleep when idle. Protect any publicly deployed endpoint against abuse before significant traffic.
- Completing the assignment still requires 5–6 genuine investor interviews and returning tests with at least 3 participants. Do not invent research or evaluation results.
