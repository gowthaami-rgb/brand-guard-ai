# BrandGuard AI

**Brand governance, checked before you publish.**

BrandGuard AI checks marketing content against your organisation's approved brand guidelines *before* it goes live. Every finding shows the exact rule and source evidence behind it, and content moves through a role-based approval workflow.

**Live demo:** https://brand-guard-ai-swart.vercel.app
**API docs:** https://brand-guard-ai-jltn.onrender.com/docs

> The backend runs on a free Render plan and sleeps when idle. The first request after a pause can take 30-60 seconds.

**Demo logins** (password for all: `demo1234`)

| Role | Email | Can do |
|---|---|---|
| Creator | creator@demo.com | Scan content, revise, submit for review |
| Manager | manager@demo.com | Everything a creator can, plus manage guidelines, brand assets, team and rule recommendations |
| Approver | approver@demo.com | Approve, reject or request changes on submissions |

---

## The problem

Teams publish across websites, emails, social posts and documents. Each piece can break brand rules: wrong product naming, off-tone language, unsupported promotional claims, inconsistent prices or dates, and off-brand visuals. Reviews are manual, slow and inconsistent.

## What it does

| Feature | Description |
|---|---|
| **Content scanner** | Paste text or upload `.txt`, `.md`, `.docx` or `.pdf` (5 MB limit, drag and drop). Findings include the quoted text, severity, suggested fix, explanation and source evidence. |
| **AI analysis (Gemini)** | A real LLM checks content against your stored guidelines. Output is validated, so invented rules or quotes that are not in the text are dropped. |
| **Guideline management** | Managers and approvers add terminology, tone and promotional-claim rules, each with priority, approved replacement and source citation. |
| **Review workflow** | Revise and re-scan, submit once findings are resolved, then approve, reject or request changes with comments and a history trail. |
| **Cross-Channel Check** | Compares submissions for conflicting prices, percentages, dates and terminology. Flags differences against approved sources and never assumes which version is wrong. |
| **Brand Intelligence** | Detects repeatedly violated rules and recommends clarifications. Only a manager can publish a revised rule. |
| **Visual Brand Audit** | Checks images for missing alt text, brand-colour share, reference-logo match and a rough contrast heuristic. |
| **Team management** | Managers invite users with a temporary password and see an activity log. |
| **Dashboard** | Live charts, a Knowledge Graph linking guidelines to affected content, and a Settings page showing real AI and storage status. |

### Design principle: the AI is never the source of truth

Guidelines are the ground truth. The model only matches content against them.

- Findings that cite an unknown rule ID are dropped.
- Findings that quote text not present in the content are dropped.
- Evidence always comes from the stored guideline, never from the model.
- Claims that cannot be verified are marked **unverified**, not wrong.
- If the AI is unavailable, the scanner falls back to rule-based checks and labels them as such.

---

## Tech stack

| Layer | Technology |
|---|---|
| Frontend | React 18, TypeScript, Vite, Tailwind CSS, lucide-react |
| Backend | Python, FastAPI, Uvicorn, Pydantic |
| Auth | PyJWT (8-hour tokens), PBKDF2-HMAC-SHA256 password hashing, role checks on every protected route |
| AI | Google Gemini API with model fallback and retries (Anthropic API supported as an alternative) |
| Documents and images | python-docx, pypdf, Pillow, NumPy, OpenCV (headless) |
| Storage | Optional MongoDB (PyMongo), with automatic fallback to a local JSON file |
| Hosting | Vercel (frontend), Render (backend) |

### Architecture

```
Browser (React, Vercel)
        |  HTTPS, JWT bearer token
        v
FastAPI backend (Render)
   |-- Rules engine + role-based workflow
   |-- Gemini API  (analysis; output validated against stored guidelines)
   |-- MongoDB Atlas, or local JSON file as fallback
```

---

## Project structure

```
brandguard/
  backend/
    main.py            FastAPI app: auth, guidelines, scanner, workflow, audits
    requirements.txt
    .env.example
  frontend/
    src/App.tsx        React UI
    package.json
    vite.config.ts
  README.md
```

---

## Run locally

**Requirements:** Python 3.11+ and Node.js 18+.

### 1. Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env            # then edit .env
uvicorn main:app --reload --port 8000
```

API docs open at http://localhost:8000/docs.

### 2. Frontend

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173. By default the frontend calls `http://localhost:8000`.

### Environment variables (backend)

| Variable | Required | Description |
|---|---|---|
| `JWT_SECRET` | Yes (production) | Long random string used to sign tokens |
| `GEMINI_API_KEY` | For AI analysis | Google Gemini API key. Without any AI key the scanner uses labelled demo rules |
| `GEMINI_MODEL` | No | Primary Gemini model name |
| `GEMINI_FALLBACK_MODELS` | No | Comma-separated models tried if the primary fails |
| `ANTHROPIC_API_KEY` | No | Alternative AI provider, used only if no Gemini key is set |
| `MONGO_URI` | No | MongoDB connection string. Leave unset to use the local data file |
| `MONGO_DB` | No | Database name (default `brandguard`) |
| `CORS_ORIGINS` | Yes (deployed) | Comma-separated allowed frontend origins, for example `https://your-app.vercel.app` |

### Environment variables (frontend)

| Variable | Description |
|---|---|
| `VITE_API_URL` | Backend base URL, for example `https://your-backend.onrender.com` (no trailing slash, no `/api`). Set at build time. |

---

## Deployment

**Backend (Render, Web Service)**
- Root directory: `backend`
- Build command: `pip install -r requirements.txt`
- Start command: `uvicorn main:app --host 0.0.0.0 --port $PORT`
- Set `JWT_SECRET`, `GEMINI_API_KEY`, `CORS_ORIGINS` and optionally `MONGO_URI`.

**Frontend (Vercel)**
- Root directory: `frontend`
- Framework preset: Vite, build command `npm run build`, output directory `dist`
- Set `VITE_API_URL` to the Render URL, then redeploy so the build picks it up.

---

## API overview

All routes are under `/api` and need a bearer token except `/api/login`. Full interactive docs are at `/docs`.

| Method | Route | Roles |
|---|---|---|
| POST | `/api/login` | Public |
| GET / POST / DELETE | `/api/guidelines` | View: all. Edit: manager, approver |
| POST | `/api/scan` | Creator, manager |
| POST | `/api/upload-text` | Creator, manager |
| GET | `/api/submissions` | All |
| POST | `/api/submissions/{id}/revise` `/submit` | Creator, manager |
| POST | `/api/submissions/{id}/decide` | Approver |
| POST | `/api/cross-check` | All |
| GET / POST | `/api/intelligence` | Manager, approver (publish: manager) |
| GET / POST | `/api/team`, `/api/team/invite` | Manager |
| GET / POST | `/api/brand-assets` | View: all. Edit: manager |
| POST | `/api/visual-audit` | All |
| GET | `/api/ai-status`, `/api/stats` | All |

---

## Known limitations

- Free-tier hosting sleeps when idle. Without MongoDB, data resets when the backend restarts.
- The Visual Brand Audit is approximate: no font recognition, and logo matching uses template matching.
- Scanned PDFs are not supported (no OCR).
- Passwords use a shared salt, which is fine for demo accounts but not for production.
- No automated tests yet.

## Roadmap (Round 3)

1. **Brand-book ingestion:** upload a brand guide PDF and let AI extract rules, with source page and quote, for manager approval.
2. **AI visual and layout audit:** Gemini vision checks logos, colours, typography and contrast, with the problem region highlighted.
3. **Pre-publish integrations:** REST API and webhooks, browser extension, Slack and email approval routing, and a persistent audit trail.

## Team

LIMITLESS - [GOWTHAAMI SM , SATHISH KUMAR S , JEEVASRI J , DHARSHINI P]

## Security note

Never commit `.env` files or API keys. Set secrets as environment variables in Render and Vercel.
