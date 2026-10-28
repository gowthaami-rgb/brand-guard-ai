# BrandGuard AI (lean MVP)
## Run
Backend: `cd backend && pip install -r requirements.txt && JWT_SECRET=<random> uvicorn main:app --reload --port 8000`
Frontend: `cd frontend && npm install && npm run dev` -> http://localhost:5173
Demo logins: creator@demo.com / manager@demo.com / approver@demo.com, password `demo1234`.
## What is real
Auth (JWT) + backend role enforcement, guideline CRUD, rule-based scan, evidence from guideline source, revise/submit/approve workflow.
## Added in v2
Cross-Channel Check (prices, percentages, dates, terminology; flags differences against approved sources, never assumes which is wrong), Brand Intelligence (repeat-violation recommendations; only a manager can publish a revision), Team Management (invite with temporary password, activity log).
## Added in v3
MongoDB persistence (set MONGO_URI; data is saved after every write and reloaded on start) and real LLM analysis (set ANTHROPIC_API_KEY). LLM output is validated: findings citing unknown rules or quotes not in the text are dropped, and evidence is always taken from stored guidelines. Without keys it falls back to the labelled demo rules. Export variables from backend/.env.example before starting (uvicorn does not read .env by itself).
## Added in v4
Upload of .txt/.md/.docx/.pdf (5 MB cap, drag and drop) into the scanner; Visual Brand Audit (alt text, brand-colour share, template-match logo check, rough contrast heuristic). Managers set approved colours and a reference logo. Checks are approximate: no font recognition, no guaranteed logo verification, scanned PDFs unsupported.
## Added in v5
Vibrant redesign (gradient shell, icon sidebar, animated hover states, status chips), Overview charts from live data, Knowledge Graph (guidelines to affected content) and Settings (shows real AI/storage status). Not yet compiled or run by me.
## Not built yet
search/notifications, tests.
# BrandGuard-AI
