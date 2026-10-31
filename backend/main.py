"""BrandGuard AI backend (MVP). In-memory store, demo rule engine (NOT a real AI)."""
import io, base64, os, re, time, uuid, hashlib, jwt, json, ssl, certifi, urllib.request, urllib.error
import datetime as dt
import contextvars
from collections import Counter
from fastapi import Request, UploadFile, File, Form
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from fastapi.security import HTTPBearer

try:
    from dotenv import load_dotenv; load_dotenv()
except ImportError: pass
SSL_CTX = ssl.create_default_context(cafile=certifi.where())
SECRET = os.getenv("JWT_SECRET", "dev-only-change-me")
app = FastAPI(title="BrandGuard AI")
app.add_middleware(CORSMiddleware, allow_origins=[o.strip().rstrip("/") for o in os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",") if o.strip()], allow_methods=["*"], allow_headers=["*"])
bearer = HTTPBearer()
h = lambda p: hashlib.pbkdf2_hmac("sha256", p.encode(), b"bg-salt", 100000).hex()
USERS = {"creator@demo.com": ("creator", h("demo1234")), "manager@demo.com": ("manager", h("demo1234")), "approver@demo.com": ("approver", h("demo1234"))}
G4_OLD = r"\b(guaranteed|#1|best in the world|100%)\b"  # \b never matches next to '#' or '%', so '#1' and '100%' were missed
G4_PATTERN = r"(?<!\w)(guaranteed|#1|best in the world|\d+(?:\.\d+)?%)(?!\w)"
G4_SOURCE = "Claims policy v1: guarantees, superlatives and statistics may only be published when an approved, unexpired fact supports them."
GUIDES = [
 dict(id="g1", category="Terminology", priority="high", kind="term", pattern="brandguard ai", fix="BrandGuard AI", source="Naming policy v1: The product is always written 'BrandGuard AI'."),
 dict(id="g2", category="Terminology", priority="medium", kind="term", pattern="brand guard", fix="BrandGuard AI", source="Naming policy v1: The product is always written 'BrandGuard AI'."),
 dict(id="g3", category="Tone and language", priority="low", kind="term", pattern="cheap", fix="affordable", source="Tone guide: avoid 'cheap'; use 'affordable'."),
 dict(id="g4", category="Promotional claims", priority="high", kind="claim", pattern=G4_PATTERN, fix="", source=G4_SOURCE),
]
FACTS = [  # approved facts: the only thing that can support a claim. Replace these samples with your real, owned facts.
 dict(id="f1", statement="100% of pilot reviewers completed onboarding without help.", keywords=["100%", "completed onboarding"], source="Sample pilot survey (replace with your real source)", owner="Product lead (sample)", expires="2027-06-30"),
 dict(id="f2", statement="Ranked #1 in the 2025 regional student showcase.", keywords=["#1", "showcase"], source="Sample award letter (replace with your real source)", owner="Marketing lead (sample)", expires="2026-06-30"),
]
EVID = {"dropped": 0}
AILOG = []  # what was sent to an external AI provider (redacted), newest last
DEBT, DOCS, REWRITES, DRAFTS = [], [], [], {}  # waivers/disputes, replay content, approved rule rewrites, pending drafts
DEBT_THRESHOLD = int(os.getenv("DEBT_THRESHOLD", "3"))
SUBS, LOG, VIOL, RECS, INVITES = {}, [], {}, {}, []
BRAND = {"colors": ["#4F46E5", "#14B8A6"], "logo": None}
def user(c=Depends(bearer)):
    try: return jwt.decode(c.credentials, SECRET, algorithms=["HS256"])
    except Exception: raise HTTPException(401, "Invalid token")
def need(*roles):
    def f(u=Depends(user)):
        if u["role"] not in roles: raise HTTPException(403, "Role not permitted")
        return u
    return f

NOEV = "Evidence not found — manual verification required."
DB = None
STORE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "brandguard_data.json")
if os.getenv("MONGO_URI"):
    try:
        from pymongo import MongoClient
        DB = MongoClient(os.environ["MONGO_URI"], serverSelectionTimeoutMS=8000, tlsCAFile=certifi.where())[os.getenv("MONGO_DB", "brandguard")]
    except Exception as e: print("MongoDB unavailable, using the local data file instead:", e)
def save_file():
    data = {"users": {k: list(v) for k, v in USERS.items()}, "guides": GUIDES, "subs": SUBS, "log": [list(e) for e in LOG], "viol": VIOL, "brand": BRAND, "recs": RECS, "invites": INVITES, "facts": FACTS, "debt": DEBT, "docs": DOCS, "rewrites": REWRITES, "drafts": DRAFTS, "ailog": AILOG}
    with open(STORE + ".tmp", "w") as f: json.dump(data, f, default=str)
    os.replace(STORE + ".tmp", STORE)
def load_file():
    if not os.path.exists(STORE): return
    try: d = json.load(open(STORE))
    except Exception as e: print("Could not read", STORE, e); return
    for k, v in d.get("users", {}).items(): USERS[k] = tuple(v)
    if "guides" in d: GUIDES[:] = d["guides"]
    if "facts" in d: FACTS[:] = d["facts"]
    DEBT[:] = d.get("debt", []); DOCS[:] = d.get("docs", []); REWRITES[:] = d.get("rewrites", []); DRAFTS.clear(); DRAFTS.update(d.get("drafts", {})); AILOG[:] = d.get("ailog", [])
    SUBS.update(d.get("subs", {})); LOG.extend(tuple(e) for e in d.get("log", [])); VIOL.update(d.get("viol", {})); RECS.update(d.get("recs", {})); INVITES.extend(d.get("invites", []))
    if d.get("brand"): BRAND.update(colors=d["brand"]["colors"], logo=d["brand"].get("logo"))
def load():
    global DB
    if DB is not None:
        try:
            for d in DB.users.find(): USERS[d["_id"]] = (d["role"], d["pw"])
            if DB.guides.count_documents({}): GUIDES[:] = list(DB.guides.find({}, {"_id": 0}))
            if DB.facts.count_documents({}): FACTS[:] = list(DB.facts.find({}, {"_id": 0}))
            for d in DB.subs.find({}, {"_id": 0}): SUBS[d["id"]] = d
            LOG.extend(tuple(x["e"]) for x in DB.log.find())
            for d in DB.viol.find(): VIOL[d["_id"]] = d["ids"]
            d = DB.brand.find_one()
            if d: BRAND.update(colors=d["colors"], logo=d.get("logo"))
            for d in DB.recs.find(): RECS[d["_id"]] = {"status": d["status"]}
            d = DB.misc.find_one({"_id": "debt"}) or {}
            DEBT[:] = d.get("debt", []); DOCS[:] = d.get("docs", []); REWRITES[:] = d.get("rewrites", []); DRAFTS.clear(); DRAFTS.update(d.get("drafts", {})); AILOG[:] = d.get("ailog", [])
            return
        except Exception as e: print("MongoDB unavailable, using the local data file instead:", e); DB = None
    load_file()
def persist():
    if DB is None: return save_file()
    for k, (r, pw) in USERS.items(): DB.users.replace_one({"_id": k}, {"_id": k, "role": r, "pw": pw}, upsert=True)
    DB.guides.delete_many({}); GUIDES and DB.guides.insert_many([dict(g) for g in GUIDES])
    DB.facts.delete_many({}); FACTS and DB.facts.insert_many([dict(f) for f in FACTS])
    for k, v in SUBS.items(): DB.subs.replace_one({"id": k}, dict(v), upsert=True)
    DB.log.delete_many({}); LOG and DB.log.insert_many([{"e": list(e)} for e in LOG])
    for k, v in VIOL.items(): DB.viol.replace_one({"_id": k}, {"_id": k, "ids": v}, upsert=True)
    DB.brand.replace_one({"_id": 1}, {"_id": 1, **BRAND}, upsert=True)
    for k, v in RECS.items(): DB.recs.replace_one({"_id": k}, {"_id": k, **v}, upsert=True)
    DB.misc.replace_one({"_id": "debt"}, {"_id": "debt", "debt": DEBT, "docs": DOCS, "rewrites": REWRITES, "drafts": DRAFTS, "ailog": AILOG}, upsert=True)
@app.middleware("http")
async def save_after_writes(req: Request, call_next):
    r = await call_next(req)
    if req.method != "GET" and r.status_code < 400:
        try: persist()
        except Exception as e: print("persist failed:", e)
    return r
def _send(rq, timeout=60):
    try: return json.load(urllib.request.urlopen(rq, timeout=timeout, context=SSL_CTX))
    except urllib.error.HTTPError as e:
        print("AI API error", e.code, e.read().decode(errors="replace")[:600]); raise
def shrink(im, raw, mime, limit=1024):
    """Large photos upload slowly and take the model longer; downscale for the AI call only."""
    if max(im.size) <= limit and len(raw) < 1_500_000: return mime, raw
    c = im.copy(); c.thumbnail((limit, limit)); b = io.BytesIO(); c.save(b, "JPEG", quality=85)
    return "image/jpeg", b.getvalue()
def ai_configured(): return bool(os.getenv("GEMINI_API_KEY") or os.getenv("ANTHROPIC_API_KEY"))
def _call_ai_raw(prompt, image=None):
    """image = (mime_type, bytes). Uses Gemini when GEMINI_API_KEY is set, otherwise Anthropic. Returns None if no key."""
    gk = os.getenv("GEMINI_API_KEY")
    if gk:
        parts = [{"text": prompt}]
        if image: parts.append({"inline_data": {"mime_type": image[0], "data": base64.b64encode(image[1]).decode()}})
        body = json.dumps({"contents": [{"parts": parts}], "generationConfig": {"responseMimeType": "application/json"}}).encode()
        models = [os.getenv("GEMINI_MODEL", "gemini-3.8-flash")] + [m.strip() for m in os.getenv("GEMINI_FALLBACK_MODELS", "gemini-3.5-flash,gemini-flash-latest").split(",") if m.strip()]
        last = None
        for model in dict.fromkeys(models):
            for attempt in range(2):
                rq = urllib.request.Request("https://generativelanguage.googleapis.com/v1beta/models/" + model + ":generateContent", method="POST",
                    headers={"x-goog-api-key": gk, "content-type": "application/json"}, data=body)
                try: return _send(rq, 90 if image else 45)["candidates"][0]["content"]["parts"][0]["text"]
                except urllib.error.HTTPError as e:
                    last = e
                    if e.code in (429, 500, 503) and attempt == 0: time.sleep(2); continue
                    print(f"Gemini model {model} failed ({e.code}); trying next model if any"); break
                except (TimeoutError, urllib.error.URLError, ConnectionError) as e:
                    last = e; print(f"Gemini model {model} timed out or was unreachable ({e}); trying next model if any"); break
        raise last
    ak = os.getenv("ANTHROPIC_API_KEY")
    if not ak: return None
    content = [{"type": "text", "text": prompt}]
    if image: content.insert(0, {"type": "image", "source": {"type": "base64", "media_type": image[0], "data": base64.b64encode(image[1]).decode()}})
    rq = urllib.request.Request("https://api.anthropic.com/v1/messages", method="POST",
        headers={"x-api-key": ak, "anthropic-version": "2023-06-01", "content-type": "application/json"},
        data=json.dumps({"model": os.getenv("ANTHROPIC_MODEL", "claude-sonnet-5-5"), "max_tokens": 2000, "messages": [{"role": "user", "content": content}]}).encode())
    return _send(rq)["content"][0]["text"]
# ---------------------------------------------------------------------------------------------
# Privacy and confidentiality layer. EVERY call to an external AI provider goes through call_ai():
#   1. the content's confidentiality tier is checked (a tier the organisation has not allowed is never sent),
#   2. personal data and secrets that match known patterns are replaced by placeholders before sending,
#   3. what was actually sent (redacted) is written to an audit log that managers and approvers can read.
# ---------------------------------------------------------------------------------------------
TIERS = ("public", "internal", "restricted")
AI_TIERS = {t.strip() for t in os.getenv("AI_ALLOWED_TIERS", "public,internal").split(",") if t.strip()} & set(TIERS)
AI_CTX = contextvars.ContextVar("ai_ctx", default={"tier": "internal", "user": "system", "sid": ""})
def tier_ok(t): return t in AI_TIERS
def _luhn(digits):
    t, alt = 0, False
    for ch in reversed(digits):
        d = int(ch)
        if alt: d = d * 2 - 9 if d * 2 > 9 else d * 2
        t += d; alt = not alt
    return t % 10 == 0
def _digits(m): return re.sub(r"\D", "", m)
PII_RULES = [  # (type, pattern, optional validator). Order matters: the most specific patterns run first.
    ("EMAIL", re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"), None),
    ("API_KEY", re.compile(r"\b(?:AIza[0-9A-Za-z_-]{30,}|sk-[A-Za-z0-9_-]{20,}|gh[pousr]_[A-Za-z0-9]{30,}|AKIA[0-9A-Z]{16})\b"), None),
    ("SECRET", re.compile(r"(?i)\b(?:api[_ -]?key|secret|token|password|passwd)\b\s*[:=]\s*\S+"), None),
    ("PAN", re.compile(r"\b[A-Z]{5}\d{4}[A-Z]\b"), None),
    ("CARD", re.compile(r"\b(?:\d[ -]?){12,18}\d\b"), lambda m: 13 <= len(_digits(m)) <= 19 and _luhn(_digits(m))),
    ("AADHAAR", re.compile(r"(?<![\d]\s)(?<!\d)\d{4}\s\d{4}\s\d{4}(?!\s?\d)"), None),
    ("SSN", re.compile(r"\b\d{3}-\d{2}-\d{4}\b"), None),
    ("IP", re.compile(r"\b(?:(?:25[0-5]|2[0-4]\d|1?\d?\d)\.){3}(?:25[0-5]|2[0-4]\d|1?\d?\d)\b"), None),
    ("PHONE", re.compile(r"(?<![\w#$£€%.,/-])\+?\(?\d[\d\s().-]{8,18}\d(?![\w%])"), lambda m: 10 <= len(_digits(m)) <= 15),
]
def redact(text):
    """Replace personal data and secrets with placeholders. Returns (clean_text, vault, counts). Pattern-based only: it does not detect names or street addresses."""
    vault, counts = {}, {}
    for kind, rx, ok in PII_RULES:
        def sub(m, kind=kind, ok=ok):
            if ok and not ok(m.group(0)): return m.group(0)
            ph = next((k for k, v in vault.items() if v == m.group(0)), None)
            if not ph:
                counts[kind] = counts.get(kind, 0) + 1; ph = f"[{kind}_{counts[kind]}]"; vault[ph] = m.group(0)
            return ph
        text = rx.sub(sub, text)
    return text, vault, counts
def restore(text, vault):
    for ph, orig in reversed(list(vault.items())): text = text.replace(ph, orig)  # outer placeholders first, so nested ones resolve
    return text
def ai_log(**kw):
    AILOG.append(dict(id=uuid.uuid4().hex[:8], ts=time.time(), **kw)); del AILOG[:-500]
def call_ai(prompt, image=None, purpose="analysis"):
    """The only way the backend talks to an AI provider. Returns None when no key is set or the content's tier is not allowed to leave."""
    ctx = AI_CTX.get(); provider = "gemini" if os.getenv("GEMINI_API_KEY") else "anthropic" if os.getenv("ANTHROPIC_API_KEY") else None
    if not provider: return None
    base = dict(user=ctx["user"], sid=ctx["sid"], tier=ctx["tier"], purpose=purpose, provider=provider)
    if not tier_ok(ctx["tier"]):
        ai_log(**base, status="blocked", reason=f"'{ctx['tier']}' content is not allowed to leave the system", chars=0, image=bool(image), redactions={}, sha256="", sent=""); return None
    clean, vault, counts = redact(prompt)
    meta = dict(**base, chars=len(clean), image=bool(image), redactions=counts, sha256=hashlib.sha256(clean.encode()).hexdigest()[:16], sent=clean[:1500])
    try: raw = _call_ai_raw(clean, image)
    except Exception as e: ai_log(**meta, status="failed", reason=str(e)[:160]); raise
    ai_log(**meta, status="sent", reason="Images are sent as uploaded and cannot be redacted." if image else ""); return restore(raw, vault) if raw else raw
def llm_analyse(text):
    """Real LLM call. Output is validated: unknown guideline ids and quotes not in the text are dropped; evidence always comes from stored guidelines."""
    rules = [{"id": g["id"], "rule": g["pattern"], "approved": g["fix"], "kind": g["kind"], "source": g["source"]} for g in GUIDES]
    prompt = ("Check CONTENT against RULES only. Return JSON array only, no prose. Each item: guideline (rule id), original (exact quote from CONTENT), "
      "status ('contradicted' or 'unverified'), suggestion (replacement text, or '' if none), explanation, confidence ('low'|'medium'|'high'). "
      "Do not invent rules, facts or evidence. Unverifiable claims are 'unverified', never false.\nRULES: " + json.dumps(rules) + "\nCONTENT: " + text)
    raw = call_ai(prompt, purpose="scan analysis")
    if raw is None: return None
    items = json.loads(re.sub(r"```(?:json)?", "", raw).strip())
    if isinstance(items, dict): items = next((v for v in items.values() if isinstance(v, list)), [])
    byid, out = {g["id"]: g for g in GUIDES}, []
    for i in items:
        if not isinstance(i, dict): continue
        g = byid.get(i.get("guideline"))
        if not g or not i.get("original") or i["original"] not in text: continue
        claim = g["kind"] == "claim"
        out.append(dict(guideline=g["id"], category=g["category"], original=i["original"], severity="high" if claim else g["priority"],
          status="unverified" if i.get("status") == "unverified" else "contradicted", title=f"Rule: {g['pattern']}"[:80], suggestion=i.get("suggestion", ""),
          evidence=g["source"] or NOEV, explanation=i.get("explanation", ""), confidence=i.get("confidence", "unknown")))
    return out
def fact_state(f):
    try: left = (dt.date.fromisoformat(f["expires"]) - dt.date.today()).days
    except Exception: return "expired"
    return "expired" if left < 0 else "expiring" if left <= 30 else "approved"
def sentence_of(text, quote):
    for part in re.split(r"(?<=[.!?])\s+|\n+", text):
        if quote.lower() in part.lower(): return part
    return text
def fact_cite(f): return dict(type="fact", id=f["id"], label=f"Fact {f['id']}: {f['statement']}", source=f["source"], owner=f["owner"], expires=f["expires"], state=fact_state(f))
def rule_cite(g): return dict(type="rule", id=g["id"], label=f"Rule {g['id']} ({g['category']}): {g['pattern']}", source=g["source"] or "No source document attached to this rule", state="approved")
def claim_support(text, quote):
    """Deterministic, no AI: a claim is supported only by an approved, unexpired fact that mentions that claim and whose keywords ALL appear in the same sentence."""
    sent = sentence_of(text, quote).lower()
    q = quote.lower()  # the fact must actually mention the claim it supports (a fact about "12 countries" cannot back up "guaranteed")
    hit = [f for f in FACTS if f.get("keywords") and all(k.strip().lower() in sent for k in f["keywords"]) and q in (f["statement"] + " " + " ".join(f["keywords"])).lower()]
    return next((f for f in hit if fact_state(f) != "expired"), None), [f for f in hit if fact_state(f) == "expired"]
def sentence_at(text, pos):
    for m in re.finditer(r"[^.!?\n]+[.!?]*", text):
        if m.start() <= pos < m.end(): return m.group(0).strip()
    return text
def sentences_for(found, text):
    """The sentence each finding really sits in (the k-th finding for a phrase maps to its k-th occurrence)."""
    seen, out = {}, []
    for x in found:
        key = (x.get("guideline"), x["original"].lower()); k = seen.get(key, 0); seen[key] = k + 1
        hits = [m.start() for m in re.finditer(re.escape(x["original"]), text, re.I)]
        out.append(sentence_at(text, hits[min(k, len(hits) - 1)]) if hits else text)
    return out
def has_exception(g, sentence):
    sent = " " + norm(sentence) + " "
    return any(n and (" " + n + " ") in sent for n in (norm(e) for e in g.get("exceptions", [])))
def finalize(found, text, guides=None):
    """Evidence gate for both engines. Every finding leaves with a citation to an approved rule or fact. Supported claims are removed (not a problem);
    unsupported claims are labelled UNVERIFIED and never carry a rewrite that states a fact; a finding that cannot cite an existing rule is dropped."""
    byid, out = {g["id"]: g for g in (guides or GUIDES)}, []
    for x, sent in zip(found, sentences_for(found, text)):
        g = byid.get(x.get("guideline"))
        if not g: EVID["dropped"] += 1; continue
        if has_exception(g, sent): continue  # a manager-approved exception: the rule does not apply in this context
        x["sentence"] = sent
        if g["kind"] == "claim":
            fact, expired = claim_support(text, x["original"])
            if fact: continue
            x.update(verification="UNVERIFIED", status="unverified", severity="high", suggestion="")
            if expired:
                e = expired[0]; x["citation"] = fact_cite(e); x["title"] = "UNVERIFIED claim: the supporting fact has expired"
                x["evidence"] = f"Fact {e['id']} would support this claim but expired on {e['expires']}. Ask {e['owner']} to renew it, or remove the claim."
            else:
                x["citation"] = rule_cite(g); x["title"] = "UNVERIFIED claim: no approved fact supports it"
                x["evidence"] = "No approved fact supports this claim, so it is UNVERIFIED and must not be published as a fact. Remove it, or ask a manager to add an approved fact."
        else:
            x.update(verification="VERIFIED", citation=rule_cite(g), evidence=g["source"] or f"Rule {g['id']} (no source document attached)")
        out.append(x)
    return out
def verified_claims(text):
    out, seen = [], set()
    for g in GUIDES:
        if g["kind"] != "claim": continue
        try: hits = list(re.finditer(g["pattern"], text, re.I))
        except re.error: continue
        for m in hits:
            fact, _ = claim_support(text, m.group(0))
            if fact and m.start() not in seen: seen.add(m.start()); out.append(dict(original=m.group(0), sentence=sentence_of(text, m.group(0)), citation=fact_cite(fact)))
    return out
STOP = set("the and for with that this your you our are was were will can has have not its into from they them then than also been being over under about more most some such only very just".split())
CLAIMY = {"best", "guaranteed", "fastest", "leading", "proven", "unmatched", "revolutionary", "number", "greatest", "perfect", "always", "never"}
def terms(t): return {w for w in re.findall(r"[a-z0-9]+", t.lower()) if len(w) >= 4 and w not in STOP}
def norm(t): return " ".join(re.findall(r"[a-z0-9]+", t.lower()))
def nums(t): return set(re.findall(r"\d[\d.,]*%?|#\d+", t.lower()))
def words(t): return set(re.findall(r"[a-z#]+", t.lower()))
def apply_fix(text, original, suggestion): return re.subn(re.escape(original), lambda m: suggestion, text, flags=re.I)
def lock_check(x, text, purpose, g):
    """Intent Lock, deterministic part: would this fix still serve the creator's audience, message and call to action? Every check is explainable."""
    orig, sug = x["original"], x["suggestion"]
    fixed, n = apply_fix(text, orig, sug); before = sentence_of(text, orig); after = apply_fix(before, orig, sug)[0]
    sanctioned = bool(g and g["kind"] == "term" and g["fix"] and sug == g["fix"])  # the brand's own approved replacement
    swapped = terms(orig) if sanctioned else set(); tt, ft = terms(text), terms(fixed)
    def lost(field, skip):
        want = terms(purpose.get(field, "")) & tt
        return want, sorted(t for t in want if t not in ft and t not in skip)
    checks, ded = [], 0
    def add(name, status, detail, pts=0):
        nonlocal ded; ded += pts; checks.append(dict(name=name, status=status, detail=detail))
    cta = purpose.get("cta", "").strip()
    if not cta: add("Call to action", "n/a", "No call to action given.")
    else:
        want, gone = lost("cta", swapped)
        if gone: add("Call to action", "fail", "This fix removes " + ", ".join(gone) + " from your call to action.", 50)
        elif norm(cta) in norm(text) and norm(cta) not in norm(fixed): add("Call to action", "warn", "Your call to action is reworded by this fix.", 20)
        else: add("Call to action", "pass", "Call to action kept.")
    for field, name, skip in (("message", "Core message", swapped), ("audience", "Audience", set())):
        if not purpose.get(field, "").strip(): add(name, "n/a", f"No {name.lower()} given."); continue
        want, gone = lost(field, skip)
        if not gone: add(name, "pass", f"{name} kept.")
        else: add(name, "fail" if len(gone) / len(want) >= 0.5 else "warn", f"This fix removes {', '.join(gone)} from your {name.lower()}.", round(50 * len(gone) / len(want)))
    new_nums, new_claims = nums(fixed) - nums(text), (words(fixed) & CLAIMY) - words(text)
    if new_nums or new_claims: add("No new claims", "fail", "This fix adds " + ", ".join(sorted(new_nums | new_claims)) + ", which your original did not say.", 50)
    else: add("No new claims", "pass", "No new numbers or claims added.")
    if len(before) >= 20 and abs(len(after) - len(before)) / len(before) > 0.5: add("Size of change", "warn", "This fix changes the sentence length by more than half.", 10)
    return dict(score=max(0, 100 - ded), before=before, after=after, occurrences=n, checks=checks, ai=None, purpose_given=any(v.strip() for v in purpose.values()))
def lock_verdict(k): return "blocked" if k["score"] < 60 else "check" if k["score"] < 85 or any(c["status"] == "warn" for c in k["checks"]) else "keeps"
def ai_judge(found, purpose):
    """Optional second opinion from the AI. It can only LOWER a score, never raise it, so it can only make the lock stricter."""
    items = [dict(id=str(i), before=x["lock"]["before"], after=x["lock"]["after"]) for i, x in enumerate(found) if x.get("lock") and x["lock"]["score"] >= 60]
    if not items or not ai_configured(): return
    prompt = ("You judge whether a suggested wording fix keeps the creator's original purpose.\n"
      f"PURPOSE: audience={purpose.get('audience') or 'not given'}; core message={purpose.get('message') or 'not given'}; call to action={purpose.get('cta') or 'not given'}.\n"
      "For each item compare BEFORE and AFTER. Penalise any change of audience, message or call to action, a tone shift, or any new factual claim.\n"
      'Return JSON only: [{"id": "0", "score": 0-100 (100 = purpose fully kept), "reason": "max 20 words"}].\nITEMS: ' + json.dumps(items))
    try:
        raw = call_ai(prompt, purpose="intent judge")
        if raw is None: return
        res = json.loads(re.sub(r"```(?:json)?", "", raw).strip())
        if isinstance(res, dict): res = next((v for v in res.values() if isinstance(v, list)), [])
        by = {str(r.get("id")): r for r in res if isinstance(r, dict)}
    except Exception as e: print("Intent judge failed:", e); return
    for i, x in enumerate(found):
        r, k = by.get(str(i)), x.get("lock")
        if not (k and r): continue
        try: sc = max(0, min(100, int(r.get("score"))))
        except (TypeError, ValueError): continue
        k["ai"] = dict(score=sc, reason=str(r.get("reason", ""))[:160]); k["score"] = min(k["score"], sc)
        k["checks"].append(dict(name="AI judge", status="fail" if sc < 60 else "warn" if sc < 85 else "pass", detail=k["ai"]["reason"] or f"Scored {sc}/100"))
def apply_lock(found, text, purpose, guides=None, use_ai=True):
    """Runs before any suggestion is shown. A blocked fix is never offered: it is kept only as blocked_suggestion so the creator can see why."""
    byid = {g["id"]: g for g in (guides or GUIDES)}
    for x in found:
        if x.get("suggestion"): x["lock"] = lock_check(x, text, purpose, byid.get(x["guideline"]))
    if use_ai: ai_judge(found, purpose)
    for x in found:
        k = x.get("lock")
        if not k: continue
        k["verdict"] = lock_verdict(k)
        if k["verdict"] == "blocked": x["blocked_suggestion"], x["suggestion"] = x["suggestion"], ""
    return found
def backfill():
    for g in GUIDES:  # migrate saved copies of the old claim rule
        if g["id"] == "g4" and g["pattern"] == G4_OLD: g["pattern"] = G4_PATTERN
        if g["id"] == "g4" and not g["source"]: g["source"] = G4_SOURCE
    for sub in SUBS.values():
        if any("citation" not in x for x in sub.get("findings", [])): sub["findings"] = finalize(sub["findings"], sub["text"])
        if "verified" not in sub: sub["verified"] = verified_claims(sub["text"])
def run_analysis(text):
    try:
        r = llm_analyse(text)
        if r is not None: return finalize(r, text), "llm"
    except Exception as e: print("LLM failed, falling back:", e)
    return finalize(analyse(text), text), ("demo-rules" if tier_ok(AI_CTX.get()["tier"]) else "restricted-rules")
load(); backfill()
class Login(BaseModel): email: str; password: str
class Guide(BaseModel): category: str; priority: str = "medium"; kind: str = "term"; pattern: str; fix: str = ""; source: str = ""; guidance: str = ""; exceptions: list[str] = []
class Scan(BaseModel): title: str; channel: str = "website"; text: str; audience: str = ""; message: str = ""; cta: str = ""; tier: str = "internal"
@app.post("/api/login")
def login(b: Login):
    u = USERS.get(b.email)
    if not u or u[1] != h(b.password): raise HTTPException(401, "Bad credentials")
    return {"token": jwt.encode({"sub": b.email, "role": u[0], "exp": time.time() + 28800}, SECRET), "role": u[0]}
@app.get("/api/guidelines")
def guides(u=Depends(user)): return GUIDES
@app.post("/api/guidelines")
def add_guide(g: Guide, u=Depends(need("manager", "approver"))):
    d = {**g.model_dump(), "id": uuid.uuid4().hex[:6], "version": 1}; GUIDES.append(d); LOG.append((u["sub"], "guideline+", d["id"])); return d
@app.delete("/api/guidelines/{gid}")
def del_guide(gid: str, u=Depends(need("manager", "approver"))):
    GUIDES[:] = [g for g in GUIDES if g["id"] != gid]; return {"ok": True}
def analyse(text, guides=None):
    out = []
    for g in (guides or GUIDES):
        for m in re.finditer(g["pattern"] if g["kind"] == "claim" else re.escape(g["pattern"]), text, re.I):
            if g["kind"] == "term" and m.group(0) == g["fix"]: continue
            claim = g["kind"] == "claim"
            out.append(dict(guideline=g["id"], category=g["category"], original=m.group(0),
              severity="high" if claim else g["priority"], status="unverified" if claim else "contradicted",
              title="Possibly unsupported claim" if claim else f"Use '{g['fix']}'",
              suggestion=g["fix"], evidence=g["source"] or "Evidence not found — manual verification required.",
              explanation="Matched demo rule; not a real AI analysis."))
    return out
@app.post("/api/scan")
def scan(b: Scan, u=Depends(need("creator", "manager"))):
    if b.tier not in TIERS: raise HTTPException(400, "Tier must be one of: " + ", ".join(TIERS))
    sid = uuid.uuid4().hex[:8]; AI_CTX.set(dict(tier=b.tier, user=u["sub"], sid=sid)); f, mode = run_analysis(b.text)
    purpose = dict(audience=b.audience.strip(), message=b.message.strip(), cta=b.cta.strip()); apply_lock(f, b.text, purpose)
    for x in f: VIOL.setdefault(x['guideline'], []).append(sid)
    high = [x for x in f if x["severity"] == "high"]
    SUBS[sid] = dict(id=sid, title=b.title, channel=b.channel, original=b.text, text=b.text, findings=f, mode=mode,
      status="Changes Required" if f else "Draft", needs_human=bool(high),
      risk=f"{len(high)} high, {len(f)-len(high)} other finding(s)", history=[("scan", u["sub"], time.time())], comments=[], verified=verified_claims(b.text), purpose=purpose, tier=b.tier, owner=u["sub"])
    return SUBS[sid]
def can_see(u, s):
    """Restricted submissions are visible only to the person who created them, managers and approvers."""
    owner = s.get("owner") or (s["history"][0][1] if s.get("history") else "")
    return s.get("tier", "internal") != "restricted" or u["role"] in ("manager", "approver") or u["sub"] == owner
def sub_or_404(sid, u):
    s = SUBS.get(sid)
    if not s: raise HTTPException(404, "Submission not found")
    if not can_see(u, s): raise HTTPException(403, "This submission is restricted")
    return s
@app.get("/api/submissions")
def subs(u=Depends(user)): return [s for s in SUBS.values() if can_see(u, s)]
class TierIn(BaseModel): tier: str
@app.post("/api/submissions/{sid}/tier")
def set_tier(sid: str, b: TierIn, u=Depends(need("manager"))):
    s = sub_or_404(sid, u)
    if b.tier not in TIERS: raise HTTPException(400, "Tier must be one of: " + ", ".join(TIERS))
    LOG.append((u["sub"], "tier", f'{sid}:{s.get("tier", "internal")}->{b.tier}')); s["tier"] = b.tier; return s

class FactIn(BaseModel): statement: str; keywords: str; source: str; owner: str; expires: str
def future_date(v):
    try: d = dt.date.fromisoformat(v)
    except ValueError: raise HTTPException(400, "Expiry date must look like 2027-06-30")
    if d < dt.date.today(): raise HTTPException(400, "Expiry date must be in the future")
    return d.isoformat()
@app.get("/api/facts")
def facts(u=Depends(user)): return [{**f, "state": fact_state(f)} for f in FACTS]
@app.post("/api/facts")
def add_fact(b: FactIn, u=Depends(need("manager", "approver"))):
    kws = [k.strip() for k in b.keywords.split(",") if k.strip()]
    if not (b.statement.strip() and kws and b.source.strip() and b.owner.strip()): raise HTTPException(400, "Statement, keywords, source and owner are all required")
    d = dict(id="f" + uuid.uuid4().hex[:5], statement=b.statement.strip(), keywords=kws, source=b.source.strip(), owner=b.owner.strip(), expires=future_date(b.expires))
    FACTS.append(d); LOG.append((u["sub"], "fact+", d["id"])); return {**d, "state": fact_state(d)}
class Renew(BaseModel): expires: str
@app.post("/api/facts/{fid}/renew")
def renew_fact(fid: str, b: Renew, u=Depends(need("manager", "approver"))):
    f = next((x for x in FACTS if x["id"] == fid), None)
    if not f: raise HTTPException(404, "Fact not found")
    f["expires"] = future_date(b.expires); LOG.append((u["sub"], "fact-renew", fid)); return {**f, "state": fact_state(f)}
@app.delete("/api/facts/{fid}")
def del_fact(fid: str, u=Depends(need("manager", "approver"))):
    FACTS[:] = [f for f in FACTS if f["id"] != fid]; LOG.append((u["sub"], "fact-", fid)); return {"ok": True}
@app.get("/api/evidence-report")
def evidence_report(u=Depends(user)):
    fs = [x for sub in SUBS.values() for x in sub["findings"]]; cited = [x for x in fs if (x.get("citation") or {}).get("id")]; states = [fact_state(f) for f in FACTS]
    return dict(submissions=len(SUBS), findings=len(fs), cited=len(cited), uncited=len(fs) - len(cited), unverified=sum(1 for x in fs if x.get("verification") == "UNVERIFIED"),
      verified_claims=sum(len(sub.get("verified", [])) for sub in SUBS.values()), facts=len(FACTS), facts_expired=states.count("expired"), facts_expiring=states.count("expiring"), dropped_by_gate=EVID["dropped"])
DEMO_SET = ["Brand Guard is a cheap tool for brand teams.", "Our product is guaranteed to fix every campaign.", "100% of pilot reviewers completed onboarding without help.",
  "Ranked #1 in the 2025 regional student showcase.", "BrandGuard AI helps teams check content before publishing.", "Brand Guard is the #1 cheap tool and 100% accurate."]
@app.get("/api/evidence-demo")
def evidence_demo(u=Depends(user)):
    rows = [dict(text=t, findings=(f := finalize(analyse(t), t)), verified=verified_claims(t)) for t in DEMO_SET]
    fs = [x for r in rows for x in r["findings"]]
    return dict(engine="rules (deterministic, repeatable)", rows=rows, findings=len(fs), uncited=sum(1 for x in fs if not (x.get("citation") or {}).get("id")),
      unverified=sum(1 for x in fs if x.get("verification") == "UNVERIFIED"), verified_claims=sum(len(r["verified"]) for r in rows))
GOLD_GUIDES = [  # fixed rule set for the golden test set, independent of the live guidelines. t3, t4, t6 and t7 are deliberately risky test rules.
 dict(id="t1", category="Terminology", priority="high", kind="term", pattern="brand guard", fix="BrandGuard AI", source="Naming policy"),
 dict(id="t2", category="Tone", priority="low", kind="term", pattern="cheap", fix="affordable", source="Tone guide"),
 dict(id="t3", category="Test: audience swap", priority="low", kind="term", pattern="students", fix="users", source="Test rule"),
 dict(id="t5", category="Terminology", priority="low", kind="term", pattern="sign up", fix="register", source="Style guide"),
 dict(id="t6", category="Test: adds a claim", priority="low", kind="term", pattern="fast", fix="the fastest in the world", source="Test rule"),
 dict(id="t7", category="Test: meaning shift", priority="low", kind="term", pattern="quick", fix="instant", source="Test rule"),
]
def P(a="", m="", c=""): return dict(audience=a, message=m, cta=c)
GOLDEN = [  # gold = a person's judgement of whether the fix keeps the creator's purpose
 dict(id="c1", text="Brand Guard helps marketing teams check content before it goes live.", purpose=P("marketing teams", "check content before it goes live"), gold={"brand guard": True}),
 dict(id="c2", text="Try our cheap plan today and sign up before Friday.", purpose=P("small businesses", "try an affordable plan", "sign up before Friday"), gold={"cheap": True, "sign up": True}),
 dict(id="c3", text="Brand Guard is a cheap tool for brand teams.", purpose=P("brand teams", "a cheap tool for brand teams"), gold={"brand guard": True, "cheap": True}),
 dict(id="c4", text="Calling all students: join our design sprint on Saturday.", purpose=P("students", "join our design sprint", "join our design sprint on Saturday"), gold={"students": False}),
 dict(id="c5", text="Get a free demo this week.", purpose=P("retail managers", "free demo this week", "Get a free demo"), gold={"free demo": False}, ai_fixes=[("t2", "free demo", "demo")]),  # a simulated AI rewrite that drops a word from the CTA
 dict(id="c6", text="Our scanner is fast and accurate.", purpose=P("content teams", "a fast and accurate scanner"), gold={"fast": False}),
 dict(id="c7", text="Brand Guard checks every channel. Brand Guard never sleeps.", purpose=P("campaign managers", "checks every channel"), gold={"brand guard": True}),
 dict(id="c8", text="Students love it: sign up for the beta.", purpose=P("students", "sign up for the beta", "sign up for the beta"), gold={"students": False, "sign up": True}),
 dict(id="c9", text="Get a quick answer in minutes.", purpose=P("support agents", "get a quick answer in minutes"), gold={"quick": False}, known_gap="'instant' overstates 'in minutes'. The deterministic checks cannot see a meaning shift; the AI judge is what covers this."),
 dict(id="c10", text="Join the cheap and cheerful Brand Guard community.", purpose=P("new members", "join the Brand Guard community"), gold={"cheap": True, "brand guard": True}),
 dict(id="c11", text="Pick the economical plan for small teams.", purpose=P("small teams", "an economical plan for small teams"), gold={"economical": True}, ai_fixes=[("t2", "economical", "cost-effective")]),  # a simulated AI rewrite that is fine but not the approved wording
]
@app.get("/api/intent-eval")
def intent_eval(u=Depends(user)):
    rows = []
    for c in GOLDEN:
        ai = [dict(guideline=g, category="AI proposal", original=o, severity="low", status="contradicted", title="AI-proposed rewrite", suggestion=sg, evidence="") for g, o, sg in c.get("ai_fixes", [])]
        f = apply_lock(finalize(analyse(c["text"], GOLD_GUIDES) + ai, c["text"], GOLD_GUIDES), c["text"], c["purpose"], GOLD_GUIDES, use_ai=False)
        for x in f:
            k = x.get("lock")
            if not k: continue
            keeps = c["gold"].get(x["original"].lower()); allowed = k["verdict"] != "blocked"
            rows.append(dict(case=c["id"], text=c["text"], original=x["original"], suggestion=x["suggestion"] or x.get("blocked_suggestion", ""), score=k["score"], verdict=k["verdict"],
              allowed=allowed, gold_keeps=keeps, correct=(allowed == keeps), known_gap=c.get("known_gap", "") if keeps is False and allowed else ""))
    acc = [r for r in rows if r["allowed"]]; kept = [r for r in acc if r["gold_keeps"]]; bad = [r for r in rows if not r["gold_keeps"]]
    pct = round(100 * len(kept) / len(acc), 1) if acc else None
    return dict(engine="deterministic checks only (AI judge off, repeatable)", fixes=len(rows), accepted=len(acc), accepted_keep_purpose=len(kept), pct=pct, target=90, met=bool(acc) and pct >= 90,
      bad_fixes=len(bad), bad_blocked=sum(1 for r in bad if not r["allowed"]), good_blocked=sum(1 for r in rows if r["gold_keeps"] and not r["allowed"]), rows=rows)
class Contest(BaseModel): index: int; kind: str; reason: str
@app.post("/api/submissions/{sid}/contest")
def contest(sid: str, b: Contest, u=Depends(need("creator", "manager"))):
    s = sub_or_404(sid, u)
    if b.kind not in ("waiver", "dispute"): raise HTTPException(400, "Kind must be waiver or dispute")
    if len(b.reason.strip()) < 5: raise HTTPException(400, "Please give a reason (at least 5 characters)")
    if not 0 <= b.index < len(s["findings"]): raise HTTPException(400, "Unknown finding")
    x = s["findings"][b.index]
    if x.get("contest"): raise HTTPException(400, "This finding is already contested")
    ev = dict(id=uuid.uuid4().hex[:8], guideline=x["guideline"], kind=b.kind, sub=sid, original=x["original"], sentence=x.get("sentence") or sentence_of(s["text"], x["original"]),
      reason=b.reason.strip(), by=u["sub"], ts=time.time(), status="open", demo=False)
    DEBT.append(ev); x["contest"] = dict(kind=b.kind, reason=ev["reason"], by=u["sub"], event=ev["id"], ts=ev["ts"], status="open"); s["needs_human"] = True
    LOG.append((u["sub"], "contest-" + b.kind, f'{sid}:{x["guideline"]}')); return s
def docs_corpus():
    docs = [dict(id=sub["id"], text=sub["original"], ts=(sub["history"][0][2] if sub.get("history") else 0)) for sub in SUBS.values()]
    return docs + [dict(id=d["id"], text=d["text"], ts=d["ts"]) for d in DOCS]
def rule_events(g): return [e for e in DEBT if e["guideline"] == g["id"] and e["status"] != "withdrawn"]
def rule_debt(g): return [e for e in rule_events(g) if e["ts"] >= g.get("rewritten_ts", 0)]
def exposure(g, docs):
    try: return sum(1 for d in docs if re.search(g["pattern"] if g["kind"] == "claim" else re.escape(g["pattern"]), d["text"], re.I))
    except re.error: return 0
def rule_matches(g, text): return finalize(analyse(text, [g]), text, [g])
def classify(g):
    """Every past place the rule fires: 'contested' = people waived or disputed it (open or granted); 'violation' = a real violation it must keep catching."""
    ev = {(e["sub"], e["original"].lower(), norm(e.get("sentence", ""))): e for e in rule_events(g)}; rows = []
    for d in docs_corpus():
        for x in rule_matches(g, d["text"]):
            e = ev.get((d["id"], x["original"].lower(), norm(x["sentence"])))
            rows.append(dict(doc=d["id"], sentence=x["sentence"], original=x["original"], was="contested" if e and e["status"] in ("open", "granted") else "violation", event=e["kind"] if e else ""))
    return rows
def backtest(g, g_new):
    """Replays all past content through the old and the proposed rule. A rewrite passes only if it drops contested findings and loses no real violation."""
    rows, newc = classify(g), Counter()
    for d in docs_corpus():
        for x in rule_matches(g_new, d["text"]): newc[(d["id"], x["original"].lower(), norm(x["sentence"]))] += 1
    out = []
    for r in rows:
        key = (r["doc"], r["original"].lower(), norm(r["sentence"])); still = newc[key] > 0
        if still: newc[key] -= 1
        out.append({**r, "still_flagged": still})
    ct, tv = [r for r in out if r["was"] == "contested"], [r for r in out if r["was"] == "violation"]
    sm = dict(contested_total=len(ct), contested_removed=sum(1 for r in ct if not r["still_flagged"]), true_total=len(tv), true_kept=sum(1 for r in tv if r["still_flagged"]), new_matches=sum(newc.values()))
    sm["true_lost"] = sm["true_total"] - sm["true_kept"]; sm["avoided_pct"] = round(100 * sm["contested_removed"] / sm["contested_total"], 1) if sm["contested_total"] else None
    sm["passed"] = sm["true_lost"] == 0 and sm["new_matches"] == 0 and sm["contested_removed"] >= 1; sm["rows"] = out; return sm
GLUE = set("a an the is are was were be been of to in on at for and or it its this that as by with from".split())
def candidate_exceptions(contested, protected):
    """Deterministic: phrases around the flagged term that show up in at least two contested cases and in no real violation."""
    cnt = {}
    for e in contested:
        toks, ot = re.findall(r"[a-z0-9]+", e["sentence"].lower()), re.findall(r"[a-z0-9]+", e["original"].lower())
        at = [i for i in range(len(toks) - len(ot) + 1) if ot and toks[i:i + len(ot)] == ot]
        if not at: continue
        i = at[0]; j = i + len(ot); seen = set()
        for L in (1, 2):
            for ph in (toks[max(0, i - L):j], toks[i:j + L]):
                if len(ph) > len(ot) and (set(ph) - set(ot)) - GLUE: seen.add(" ".join(ph))  # needs a meaningful word, not just "<term> is"
        for ph in seen: cnt.setdefault(ph, set()).add(e["id"])
    need, prot = (2 if len(contested) >= 2 else 1), [" " + norm(t) + " " for t in protected]
    ok = {ph: ids for ph, ids in cnt.items() if len(ids) >= need and not any((" " + ph + " ") in p for p in prot)}
    chosen, covered = [], set()
    for ph in sorted(ok, key=lambda p: (-len(ok[p]), len(p.split()), p)):
        if ok[ph] - covered: chosen.append(ph); covered |= ok[ph]
        if len(chosen) == 5: break
    return chosen
def draft_guidance(g, ex, contested):
    base = f"Use '{g['fix']}' instead of '{g['pattern']}'." if g.get("fix") else f"Avoid '{g['pattern']}'."
    plain = base + (f" This rule does not apply in: {', '.join(ex)}." if ex else "") + f" Clarified after {len(contested)} waivers and disputes."
    if not ai_configured(): return plain, "rules"
    try:
        raw = call_ai(purpose="rule drafting", prompt="You help a brand manager clarify a style rule that people keep disputing. The exceptions below are already tested; do not change them. "
          f"RULE: replace '{g['pattern']}' with '{g.get('fix') or '(no fix)'}'. EXCEPTIONS: {json.dumps(ex)}. WHY PEOPLE CONTESTED IT: {json.dumps([e['reason'] for e in contested][:8])}. "
          'Write the clearer rule text in plain language, at most 40 words, mentioning the exceptions. Return JSON only: {"guidance": "..."}')
        t = json.loads(re.sub(r"```(?:json)?", "", raw or "").strip()).get("guidance", "").strip() if raw else ""
        if t and len(t) <= 400: return t, "ai"
    except Exception as e: print("Guidance drafting failed:", e)
    return plain, "rules"
def with_edits(g, exceptions, guidance): return {**g, "exceptions": [e.strip() for e in exceptions if e.strip()][:8], "guidance": guidance.strip()[:400]}
def rule_view(g):
    evs = rule_events(g); debt = rule_debt(g); rw = next((r for r in reversed(REWRITES) if r["guideline"] == g["id"]), None); imp = None
    if rw:
        docs = docs_corpus(); side = lambda sel, ds: (lambda n, ex: dict(events=n, exposure=ex, rate=round(n / ex, 2) if ex else None))(sum(1 for e in evs if sel(e["ts"])), exposure(g, ds))
        b, a = side(lambda t: t < rw["ts"], [d for d in docs if d["ts"] < rw["ts"]]), side(lambda t: t >= rw["ts"], [d for d in docs if d["ts"] >= rw["ts"]])
        imp = dict(version=rw["version"], at=rw["ts"], before=b, after=a, verdict="waiting" if a["exposure"] < 2 else "no-baseline" if b["rate"] is None else "fewer" if (a["rate"] or 0) < b["rate"] else "not-fewer")
    return dict(id=g["id"], category=g["category"], pattern=g["pattern"], fix=g.get("fix", ""), version=g.get("version", 1), guidance=g.get("guidance", ""), exceptions=g.get("exceptions", []),
      waivers=sum(1 for e in evs if e["kind"] == "waiver"), disputes=sum(1 for e in evs if e["kind"] == "dispute"), granted=sum(1 for e in evs if e["status"] == "granted"), denied=sum(1 for e in evs if e["status"] == "denied"),
      debt=len(debt), flagged=len(debt) >= DEBT_THRESHOLD, has_draft=g["id"] in DRAFTS, impact=imp,
      recent=[dict(kind=e["kind"], reason=e["reason"], status=e["status"], sentence=e["sentence"], demo=e.get("demo", False)) for e in sorted(debt, key=lambda e: -e["ts"])[:5]])
@app.get("/api/debt")
def debt_report(u=Depends(need("manager", "approver"))):
    rules = [rule_view(g) for g in GUIDES]
    return dict(threshold=DEBT_THRESHOLD, rules=rules, drafts=DRAFTS, rewrites=REWRITES, demo_loaded=bool(DOCS), flagged=sum(1 for r in rules if r["flagged"]),
      waivers=sum(r["waivers"] for r in rules), disputes=sum(r["disputes"] for r in rules))
def rule_or_404(gid):
    g = next((x for x in GUIDES if x["id"] == gid), None)
    if not g: raise HTTPException(404, "Unknown guideline")
    return g
@app.post("/api/debt/{gid}/draft")
def debt_draft(gid: str, u=Depends(need("manager"))):
    g = rule_or_404(gid); debt = rule_debt(g); AI_CTX.set(dict(tier="internal", user=u["sub"], sid=""))
    if len(debt) < DEBT_THRESHOLD: raise HTTPException(400, f"Not flagged yet: {len(debt)} of {DEBT_THRESHOLD} waivers and disputes")
    contested = [e for e in debt if e["status"] in ("open", "granted")]
    ex = candidate_exceptions(contested, [r["sentence"] for r in classify(g) if r["was"] == "violation"])
    text, engine = draft_guidance(g, ex, contested); new = with_edits(g, ex, text)
    DRAFTS[gid] = dict(guideline=gid, ts=time.time(), by=u["sub"], engine=engine, based_on=len(debt), reasons=[e["reason"] for e in debt][:8],
      current=dict(exceptions=g.get("exceptions", []), guidance=g.get("guidance", "")), proposed=dict(exceptions=new["exceptions"], guidance=new["guidance"]), backtest=backtest(g, new))
    LOG.append((u["sub"], "debt-draft", gid)); return DRAFTS[gid]
class Edits(BaseModel): exceptions: list[str] = []; guidance: str = ""
@app.post("/api/debt/{gid}/backtest")
def debt_backtest(gid: str, b: Edits, u=Depends(need("manager"))):
    g = rule_or_404(gid); return backtest(g, with_edits(g, b.exceptions, b.guidance))
@app.post("/api/debt/{gid}/approve")
def debt_approve(gid: str, b: Edits, u=Depends(need("manager"))):
    g = rule_or_404(gid)
    if gid not in DRAFTS: raise HTTPException(400, "Draft a rewrite first")
    new = with_edits(g, b.exceptions, b.guidance); bt = backtest(g, new)
    if not bt["passed"]: raise HTTPException(400, f"Rewrite not approved: it would lose {bt['true_lost']} real violation(s), add {bt['new_matches']} new finding(s) and remove {bt['contested_removed']} contested one(s). Edit it and test again.")
    g.setdefault("history", []).append(dict(version=g.get("version", 1), exceptions=g.get("exceptions", []), guidance=g.get("guidance", ""), pattern=g["pattern"], fix=g.get("fix", ""), ts=time.time(), by=u["sub"]))
    now = time.time(); g.update(exceptions=new["exceptions"], guidance=new["guidance"], version=g.get("version", 1) + 1, rewritten_ts=now, rewritten_by=u["sub"])
    REWRITES.append(dict(id=uuid.uuid4().hex[:6], guideline=gid, version=g["version"], ts=now, by=u["sub"], exceptions=g["exceptions"], guidance=g["guidance"], backtest={k: v for k, v in bt.items() if k != "rows"}))
    DRAFTS.pop(gid, None); LOG.append((u["sub"], "debt-approve", gid)); return rule_view(g)
@app.delete("/api/debt/{gid}/draft")
def debt_discard(gid: str, u=Depends(need("manager"))): DRAFTS.pop(gid, None); LOG.append((u["sub"], "debt-discard", gid)); return {"ok": True}
DEMO_DEBT = [("cheap", [
  ("Unlike cheap imitations, our scanner is built for brand teams.", "dispute", "granted", "Comparing against rivals, not describing our product."),
  ("Our plan is not cheap, it is worth every rupee.", "waiver", "granted", "Quoting a customer who said it is not cheap."),
  ("Do not settle for cheap imitations of real brand tools.", "dispute", "granted", "Warning against copycats; the word is not about us."),
  ("It is not cheap, but it pays for itself in a week.", "waiver", "open", "Honest pricing message: we want to say it is not cheap."),
  ("Try our cheap plan today.", None, "", ""),
  ("A cheap and fast way to scan your posts.", "waiver", "denied", "Short on time, needs to go out today."),
  ("Get the cheap tier now.", None, "", "")]),
 ("brand guard", [
  ("Contract signed with Brand Guard Ltd on Monday.", "dispute", "granted", "Legal entity name must stay as registered."),
  ("Brand Guard Ltd is registered in Chennai.", "dispute", "granted", "Registered company name, cannot be changed."),
  ("Invoice from Brand Guard Ltd is attached.", "waiver", "open", "Finance document uses the legal name."),
  ("Brand Guard Ltd will attend the summit.", "waiver", "granted", "Event organiser lists the legal name."),
  ("Meet Brand Guard at the summit.", None, "", ""),
  ("Brand Guard helps teams stay on brand.", None, "", "")])]
@app.post("/api/debt-demo")
def debt_demo(u=Depends(need("manager"))):
    if DOCS: raise HTTPException(409, "Demo history is already loaded")
    now, n = time.time(), 0
    for pattern, items in DEMO_DEBT:
        g = next((x for x in GUIDES if x["pattern"].lower() == pattern and x["kind"] == "term"), None)
        if not g: continue
        for text, kind, status, reason in items:
            n += 1; did = f"d{n}"; ts = now - (40 - n) * 3600 * 24 / 2; DOCS.append(dict(id=did, text=text, ts=ts, demo=True))
            if kind: DEBT.append(dict(id=f"e{n}", guideline=g["id"], kind=kind, sub=did, original=re.search(re.escape(pattern), text, re.I).group(0), sentence=text, reason=reason, by="creator@demo.com", ts=ts, status=status, demo=True))
    if not DOCS: raise HTTPException(400, "Demo history needs the default 'cheap' or 'Brand Guard' rule")
    LOG.append((u["sub"], "debt-demo", str(len(DOCS)))); return {"docs": len(DOCS), "events": sum(1 for e in DEBT if e.get("demo"))}
@app.delete("/api/debt-demo")
def debt_demo_clear(u=Depends(need("manager"))):
    DOCS.clear(); DEBT[:] = [e for e in DEBT if not e.get("demo")]; LOG.append((u["sub"], "debt-demo-clear", "")); return {"ok": True}
class Fix(BaseModel): text: str; accepted: dict | None = None
@app.post("/api/submissions/{sid}/revise")
def revise(sid: str, b: Fix, u=Depends(need("creator", "manager"))):
    s = sub_or_404(sid, u); old = {}; AI_CTX.set(dict(tier=s.get("tier", "internal"), user=u["sub"], sid=sid))
    for x in s["findings"]:
        if x.get("contest"): old.setdefault((x["guideline"], x["original"].lower()), []).append(x["contest"])
    s["text"] = b.text; s["findings"], s["mode"] = run_analysis(b.text); s["verified"] = verified_claims(b.text); apply_lock(s["findings"], b.text, s.get("purpose", {}))
    for x in s["findings"]:  # a contest follows its finding through rescans; one whose finding is now fixed is withdrawn and no longer counts as debt
        c = old.get((x["guideline"], x["original"].lower()))
        if c: x["contest"] = c.pop(0)
    for cs in old.values():
        for c in cs:
            for e in DEBT:
                if e["id"] == c.get("event") and e["status"] == "open": e["status"] = "withdrawn"
    if b.accepted: LOG.append((u["sub"], "fix-accepted", f'{sid}:{b.accepted.get("guideline", "")}:{b.accepted.get("verdict", "")}:{b.accepted.get("score", "")}'))
    s["status"] = "Changes Required" if s["findings"] else "Draft"; s["history"].append(("revise", u["sub"], time.time())); return s
@app.post("/api/submissions/{sid}/submit")
def submit(sid: str, u=Depends(need("creator", "manager"))):
    s = sub_or_404(sid, u)
    if [x for x in s["findings"] if not x.get("contest") or x["contest"]["status"] == "denied"]: raise HTTPException(400, "Fix every finding, or contest it with a reason, first")
    if s["findings"]: s["needs_human"] = True
    s["status"] = "Pending Review"; s["history"].append(("submit", u["sub"], time.time())); return s
class Decision(BaseModel): decision: str; comment: str = ""
@app.post("/api/submissions/{sid}/decide")
def decide(sid: str, b: Decision, u=Depends(need("approver"))):
    s = sub_or_404(sid, u)
    if s["status"] != "Pending Review": raise HTTPException(400, "Not pending review")
    s["status"] = {"approve": "Approved", "reject": "Rejected", "changes": "Changes Required"}[b.decision]
    verdict = "granted" if b.decision == "approve" else "denied"  # approving a submission grants the waivers and upholds the disputes in it
    for x in s["findings"]:
        if x.get("contest") and x["contest"]["status"] == "open": x["contest"]["status"] = verdict
    for e in DEBT:
        if e["sub"] == sid and e["status"] == "open": e["status"] = verdict; e["decided_by"] = u["sub"]
    s["comments"].append((u["sub"], b.comment)); s["history"].append((b.decision, u["sub"], time.time())); return s
@app.get("/api/ai-status")
def ai_status(u=Depends(user)): return {"llm_configured": ai_configured(), "mongo": DB is not None, "provider": "gemini" if os.getenv("GEMINI_API_KEY") else "anthropic" if os.getenv("ANTHROPIC_API_KEY") else None, "ai_allowed_tiers": sorted(AI_TIERS), "tiers": list(TIERS)}
TIER_INFO = {"public": "Already public or approved for publishing. May be sent to the AI provider after redaction.",
  "internal": "Normal working drafts. May be sent to the AI provider after redaction (default).",
  "restricted": "Confidential. Never sent to any AI provider: scanned with rule-based checks only, and visible only to its creator, managers and approvers."}
@app.get("/api/ai-disclosure")
def ai_disclosure(u=Depends(user)):
    p = "gemini" if os.getenv("GEMINI_API_KEY") else "anthropic" if os.getenv("ANTHROPIC_API_KEY") else None
    sent = [e for e in AILOG if e["status"] == "sent"]
    return dict(ai_enabled=bool(p), provider={"gemini": "Google Gemini API", "anthropic": "Anthropic API"}.get(p, "None (rule-based checks only)"),
      what_is_sent="The text you scan (and, for the visual audit, the uploaded image) plus the guideline rules, so the model can compare them. Nothing else from your account is sent.",
      redaction=dict(applied_before_every_send=True, detects=["email addresses", "phone numbers", "payment card numbers (checksum-verified)", "Aadhaar, PAN and US SSN numbers", "IP addresses", "API keys and 'password: ...' style secrets"],
        cannot_detect=["personal names", "street addresses", "free-text personal details", "text inside images (images are sent as uploaded)"]),
      tiers=[dict(tier=t, ai_allowed=tier_ok(t), description=TIER_INFO[t]) for t in TIERS],
      human_control="The system never publishes or edits your content. A person approves or rejects every submission.",
      retention="BrandGuard keeps a redacted audit log of each AI call (see /api/ai-log). The provider's own retention is governed by its API terms.",
      totals=dict(sent=len(sent), blocked=sum(1 for e in AILOG if e["status"] == "blocked"), failed=sum(1 for e in AILOG if e["status"] == "failed"), items_redacted=sum(sum(e["redactions"].values()) for e in sent)))
class PreviewIn(BaseModel): text: str
@app.post("/api/privacy-preview")
def privacy_preview(b: PreviewIn, u=Depends(user)):
    """Shows exactly what would be replaced before anything is sent. Nothing is sent or stored."""
    clean, _, counts = redact(b.text); return dict(redacted=clean, counts=counts, total=sum(counts.values()))
@app.get("/api/ai-log")
def ai_log_view(limit: int = 100, u=Depends(need("manager", "approver"))):
    return dict(entries=list(reversed(AILOG))[:max(1, min(limit, 500))], total=len(AILOG), allowed_tiers=sorted(AI_TIERS))
@app.get("/api/stats")
def stats(u=Depends(user)):
    c = {}
    for s in SUBS.values(): c[s["status"]] = c.get(s["status"], 0) + 1
    return {"total": len(SUBS), "by_status": c, "demo_data": False}

class Cross(BaseModel): ids: list[str]
PAT = {"price": r"[$£€]\s?\d[\d,]*(?:\.\d+)?", "percent": r"\d+(?:\.\d+)?\s?%", "date": r"\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b|\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]* \d{1,2}\b"}
@app.post("/api/cross-check")
def cross(b: Cross, u=Depends(user)):
    sel = [SUBS[i] for i in b.ids if i in SUBS and can_see(u, SUBS[i])]
    if len(sel) < 2: raise HTTPException(400, "Select at least two submissions")
    out = []
    for kind, rx in PAT.items():
        vals = {s["id"]: sorted(set(re.findall(rx, s["text"], re.I))) for s in sel}
        flat = {v for x in vals.values() for v in x}
        if len(flat) > 1:
            refs = [g["source"] for g in GUIDES if g["source"] and any(v in g["source"] for v in flat)]
            out.append(dict(kind=kind, values=vals, reference=refs[0] if refs else "Evidence not found — manual verification required.",
              action="Values differ across content. Not assumed wrong: confirm against the approved source."))
    for g in GUIDES:
        if g["kind"] == "term":
            used = {s["id"]: g["pattern"] in s["text"].lower() for s in sel}
            if any(used.values()) and not all(used.values()): out.append(dict(kind="terminology", values={k: ["uses variant" if v else "not used"] for k, v in used.items()}, reference=g["source"] or "Evidence not found — manual verification required.", action=f"Check use of '{g['pattern']}' vs approved '{g['fix']}'."))
    return {"compared": [s["id"] for s in sel], "findings": out, "engine": "demo-rules"}
@app.get("/api/intelligence")
def intel(u=Depends(need("manager", "approver"))):
    items = []
    for g in GUIDES:
        n = len(VIOL.get(g["id"], []))
        if n >= 2:
            st = RECS.get(g["id"], {"status": "pending"})
            items.append(dict(guideline=g["id"], rule=g["pattern"], category=g["category"], count=n, examples=VIOL[g["id"]][:3], status=st["status"],
              proposal=f"Rule '{g['pattern']}' was violated in {n} scans. Consider clarifying it with examples.", source=g["source"]))
    counts = {g["id"]: len(VIOL.get(g["id"], [])) for g in GUIDES}
    return {"violation_counts": counts, "recommendations": items}
class Rec(BaseModel): action: str; source: str = ""
@app.post("/api/intelligence/{gid}")
def rec(gid: str, b: Rec, u=Depends(need("manager"))):
    g = next((x for x in GUIDES if x["id"] == gid), None)
    if not g: raise HTTPException(404, "Unknown guideline")
    if b.action == "accept": g["source"] = b.source or g["source"]; RECS[gid] = {"status": "published"}
    elif b.action == "reject": RECS[gid] = {"status": "rejected"}
    else: raise HTTPException(400, "Bad action")
    LOG.append((u["sub"], "rec-" + b.action, gid)); return RECS[gid]
class Invite(BaseModel): email: str; role: str
@app.post("/api/team/invite")
def invite(b: Invite, u=Depends(need("manager"))):
    if b.role not in ("creator", "manager", "approver") or "@" not in b.email: raise HTTPException(400, "Invalid email or role")
    if b.email in USERS: raise HTTPException(400, "User exists")
    USERS[b.email] = (b.role, h("changeme123")); INVITES.append(b.email); LOG.append((u["sub"], "invite", b.email)); return {"ok": True, "temp_password": "changeme123"}
@app.get("/api/team")
def team(u=Depends(need("manager"))): return {"users": [{"email": k, "role": v[0]} for k, v in USERS.items()], "activity": LOG[-50:]}

MAXB = 5 * 1024 * 1024
async def read_limited(f, exts):
    ext = os.path.splitext(f.filename or "")[1].lower()
    if ext not in exts: raise HTTPException(400, "Unsupported type. Allowed: " + ", ".join(exts))
    d = await f.read(MAXB + 1)
    if len(d) > MAXB: raise HTTPException(413, "File is over 5 MB")
    return ext, d
@app.post("/api/upload-text")
async def upload_text(file: UploadFile = File(...), u=Depends(need("creator", "manager"))):
    ext, d = await read_limited(file, [".txt", ".md", ".docx", ".pdf"])
    try:
        if ext in (".txt", ".md"): t = d.decode("utf-8", "replace")
        elif ext == ".docx":
            import docx; t = "\n".join(p.text for p in docx.Document(io.BytesIO(d)).paragraphs)
        else:
            from pypdf import PdfReader; t = "\n".join(p.extract_text() or "" for p in PdfReader(io.BytesIO(d)).pages)
    except Exception: raise HTTPException(400, "Could not read this file")
    if not t.strip(): raise HTTPException(400, "No text found (scanned PDFs need OCR, which is not supported)")
    return {"text": t[:20000]}
@app.get("/api/brand-assets")
def get_brand(u=Depends(user)): return {"colors": BRAND["colors"], "has_logo": bool(BRAND["logo"])}
@app.post("/api/brand-assets")
async def set_brand(colors: str = Form(""), logo: UploadFile = File(None), u=Depends(need("manager"))):
    cs = [c.strip().upper() for c in colors.split(",") if c.strip()]
    if any(not re.fullmatch(r"#[0-9A-F]{6}", c) for c in cs): raise HTTPException(400, "Colours must look like #4F46E5")
    if cs: BRAND["colors"] = cs
    if logo is not None and logo.filename:
        _, d = await read_limited(logo, [".png", ".jpg", ".jpeg"]); BRAND["logo"] = base64.b64encode(d).decode()
    LOG.append((u["sub"], "brand-assets", "")); return {"ok": True}
@app.post("/api/visual-audit")
async def visual_audit(file: UploadFile = File(...), alt: str = Form(""), tier: str = Form("internal"), u=Depends(user)):
    if tier not in TIERS: raise HTTPException(400, "Tier must be one of: " + ", ".join(TIERS))
    AI_CTX.set(dict(tier=tier, user=u["sub"], sid=""))
    ext, d = await read_limited(file, [".png", ".jpg", ".jpeg", ".webp"])
    import numpy as np
    try:
        from PIL import Image; im = Image.open(io.BytesIO(d)).convert("RGB")
    except Exception: raise HTTPException(400, "This is not a valid image")
    F, sm = [], np.asarray(im.resize((120, 120))).reshape(-1, 3).astype(float)
    if not alt.strip(): F.append(dict(category="Accessibility", severity="medium", title="Missing alternative text", detail="No alt text was provided for this image."))
    if sm.mean(axis=1).std() < 25: F.append(dict(category="Accessibility", severity="low", title="Possible low overall contrast", detail="Brightness varies little across the image. This is a rough heuristic, not a WCAG test."))
    cols = [np.array([int(c[i:i + 2], 16) for i in (1, 3, 5)]) for c in BRAND["colors"]]
    share = float((np.min([np.linalg.norm(sm - c, axis=1) for c in cols], axis=0) < 60).mean())
    if share < 0.02: F.append(dict(category="Visual identity", severity="medium", title="Few brand colours detected", detail=f"About {share:.0%} of sampled pixels are close to the approved colours (approximate)."))
    logo = {"checked": False, "note": "No reference logo uploaded; logo check skipped."}
    if BRAND["logo"]:
        try:
            import cv2
            g = cv2.cvtColor(np.asarray(im), cv2.COLOR_RGB2GRAY)
            tpl = cv2.imdecode(np.frombuffer(base64.b64decode(BRAND["logo"]), np.uint8), cv2.IMREAD_GRAYSCALE); best = 0.0
            for fr in (0.1, 0.15, 0.2, 0.3, 0.4):
                w = int(g.shape[1] * fr); h = int(tpl.shape[0] * w / tpl.shape[1])
                if w < 8 or h < 8 or h > g.shape[0]: continue
                best = max(best, float(cv2.matchTemplate(g, cv2.resize(tpl, (w, h)), cv2.TM_CCOEFF_NORMED).max()))
            logo = {"checked": True, "score": round(best, 2), "found": best >= 0.6, "note": "Template matching: fails on rotation, recolouring or heavy distortion."}
            if best < 0.6: F.append(dict(category="Visual identity", severity="medium", title="Approved logo not detected", detail=f"Best match score {best:.2f} (threshold 0.60). Verify manually."))
        except Exception: logo = {"checked": False, "note": "Logo check failed (OpenCV unavailable?)."}
    extra = {"ai_used": False, "extracted_text": "", "text_findings": [], "observations": []}
    if ai_configured() and not tier_ok(tier): extra["ai_blocked"] = f"AI analysis skipped: {tier} images are never sent to an AI provider."
    elif ai_configured():
        try:
            media = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".webp": "image/webp"}[ext]
            prompt = ('Return JSON only: {"text": "all text visible in the image, exactly as written", "observations": ["short factual notes about the logo, colours, claims or accessibility visible in the image"]}. '
                      'Describe only what is visible. If unsure, say so. Do not invent text.')
            raw = call_ai(prompt, shrink(im, d, media), purpose="image analysis")
            j = json.loads(re.sub(r"```(?:json)?", "", raw).strip())
            txt = str(j.get("text", ""))[:5000]
            tf, _ = run_analysis(txt) if txt.strip() else ([], "")
            extra = {**extra, "ai_used": True, "extracted_text": txt, "text_findings": tf, "observations": [str(x)[:300] for x in j.get("observations", [])[:8]]}
        except Exception as e: print("Image AI analysis failed:", e)
    return {**extra, "findings": F, "colour_match": share, "brand_colours": BRAND["colors"], "logo": logo, "limits": "Approximate checks only. No font recognition and no guaranteed logo verification."}
