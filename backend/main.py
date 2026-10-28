"""BrandGuard AI backend (MVP). In-memory store, demo rule engine (NOT a real AI)."""
import io, base64, os, re, time, uuid, hashlib, jwt, json, ssl, certifi, urllib.request, urllib.error
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
GUIDES = [
 dict(id="g1", category="Terminology", priority="high", kind="term", pattern="brandguard ai", fix="BrandGuard AI", source="Naming policy v1: The product is always written 'BrandGuard AI'."),
 dict(id="g2", category="Terminology", priority="medium", kind="term", pattern="brand guard", fix="BrandGuard AI", source="Naming policy v1: The product is always written 'BrandGuard AI'."),
 dict(id="g3", category="Tone and language", priority="low", kind="term", pattern="cheap", fix="affordable", source="Tone guide: avoid 'cheap'; use 'affordable'."),
 dict(id="g4", category="Promotional claims", priority="high", kind="claim", pattern=r"\b(guaranteed|#1|best in the world|100%)\b", fix="", source=""),
]
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
    data = {"users": {k: list(v) for k, v in USERS.items()}, "guides": GUIDES, "subs": SUBS, "log": [list(e) for e in LOG], "viol": VIOL, "brand": BRAND, "recs": RECS, "invites": INVITES}
    with open(STORE + ".tmp", "w") as f: json.dump(data, f, default=str)
    os.replace(STORE + ".tmp", STORE)
def load_file():
    if not os.path.exists(STORE): return
    try: d = json.load(open(STORE))
    except Exception as e: print("Could not read", STORE, e); return
    for k, v in d.get("users", {}).items(): USERS[k] = tuple(v)
    if "guides" in d: GUIDES[:] = d["guides"]
    SUBS.update(d.get("subs", {})); LOG.extend(tuple(e) for e in d.get("log", [])); VIOL.update(d.get("viol", {})); RECS.update(d.get("recs", {})); INVITES.extend(d.get("invites", []))
    if d.get("brand"): BRAND.update(colors=d["brand"]["colors"], logo=d["brand"].get("logo"))
def load():
    global DB
    if DB is not None:
        try:
            for d in DB.users.find(): USERS[d["_id"]] = (d["role"], d["pw"])
            if DB.guides.count_documents({}): GUIDES[:] = list(DB.guides.find({}, {"_id": 0}))
            for d in DB.subs.find({}, {"_id": 0}): SUBS[d["id"]] = d
            LOG.extend(tuple(x["e"]) for x in DB.log.find())
            for d in DB.viol.find(): VIOL[d["_id"]] = d["ids"]
            d = DB.brand.find_one()
            if d: BRAND.update(colors=d["colors"], logo=d.get("logo"))
            for d in DB.recs.find(): RECS[d["_id"]] = {"status": d["status"]}
            return
        except Exception as e: print("MongoDB unavailable, using the local data file instead:", e); DB = None
    load_file()
def persist():
    if DB is None: return save_file()
    for k, (r, pw) in USERS.items(): DB.users.replace_one({"_id": k}, {"_id": k, "role": r, "pw": pw}, upsert=True)
    DB.guides.delete_many({}); GUIDES and DB.guides.insert_many([dict(g) for g in GUIDES])
    for k, v in SUBS.items(): DB.subs.replace_one({"id": k}, dict(v), upsert=True)
    DB.log.delete_many({}); LOG and DB.log.insert_many([{"e": list(e)} for e in LOG])
    for k, v in VIOL.items(): DB.viol.replace_one({"_id": k}, {"_id": k, "ids": v}, upsert=True)
    DB.brand.replace_one({"_id": 1}, {"_id": 1, **BRAND}, upsert=True)
    for k, v in RECS.items(): DB.recs.replace_one({"_id": k}, {"_id": k, **v}, upsert=True)
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
def shrink(im, raw, mime, limit=1600):
    """Large photos upload slowly and take the model longer; downscale for the AI call only."""
    if max(im.size) <= limit and len(raw) < 1_500_000: return mime, raw
    c = im.copy(); c.thumbnail((limit, limit)); b = io.BytesIO(); c.save(b, "JPEG", quality=85)
    return "image/jpeg", b.getvalue()
def ai_configured(): return bool(os.getenv("GEMINI_API_KEY") or os.getenv("ANTHROPIC_API_KEY"))
def call_ai(prompt, image=None):
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
                try: return _send(rq, 45)["candidates"][0]["content"]["parts"][0]["text"]
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
def llm_analyse(text):
    """Real LLM call. Output is validated: unknown guideline ids and quotes not in the text are dropped; evidence always comes from stored guidelines."""
    rules = [{"id": g["id"], "rule": g["pattern"], "approved": g["fix"], "kind": g["kind"], "source": g["source"]} for g in GUIDES]
    prompt = ("Check CONTENT against RULES only. Return JSON array only, no prose. Each item: guideline (rule id), original (exact quote from CONTENT), "
      "status ('contradicted' or 'unverified'), suggestion (replacement text, or '' if none), explanation, confidence ('low'|'medium'|'high'). "
      "Do not invent rules, facts or evidence. Unverifiable claims are 'unverified', never false.\nRULES: " + json.dumps(rules) + "\nCONTENT: " + text)
    raw = call_ai(prompt)
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
def run_analysis(text):
    try:
        r = llm_analyse(text)
        if r is not None: return r, "llm"
    except Exception as e: print("LLM failed, falling back:", e)
    return analyse(text), "demo-rules"
load()
class Login(BaseModel): email: str; password: str
class Guide(BaseModel): category: str; priority: str = "medium"; kind: str = "term"; pattern: str; fix: str = ""; source: str = ""
class Scan(BaseModel): title: str; channel: str = "website"; text: str
@app.post("/api/login")
def login(b: Login):
    u = USERS.get(b.email)
    if not u or u[1] != h(b.password): raise HTTPException(401, "Bad credentials")
    return {"token": jwt.encode({"sub": b.email, "role": u[0], "exp": time.time() + 28800}, SECRET), "role": u[0]}
@app.get("/api/guidelines")
def guides(u=Depends(user)): return GUIDES
@app.post("/api/guidelines")
def add_guide(g: Guide, u=Depends(need("manager", "approver"))):
    d = {**g.model_dump(), "id": uuid.uuid4().hex[:6]}; GUIDES.append(d); LOG.append((u["sub"], "guideline+", d["id"])); return d
@app.delete("/api/guidelines/{gid}")
def del_guide(gid: str, u=Depends(need("manager", "approver"))):
    GUIDES[:] = [g for g in GUIDES if g["id"] != gid]; return {"ok": True}
def analyse(text):
    out = []
    for g in GUIDES:
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
    f, mode = run_analysis(b.text); sid = uuid.uuid4().hex[:8]
    for x in f: VIOL.setdefault(x['guideline'], []).append(sid)
    high = [x for x in f if x["severity"] == "high"]
    SUBS[sid] = dict(id=sid, title=b.title, channel=b.channel, original=b.text, text=b.text, findings=f, mode=mode,
      status="Changes Required" if f else "Draft", needs_human=bool(high),
      risk=f"{len(high)} high, {len(f)-len(high)} other finding(s)", history=[("scan", u["sub"], time.time())], comments=[])
    return SUBS[sid]
@app.get("/api/submissions")
def subs(u=Depends(user)): return list(SUBS.values())
class Fix(BaseModel): text: str
@app.post("/api/submissions/{sid}/revise")
def revise(sid: str, b: Fix, u=Depends(need("creator", "manager"))):
    s = SUBS[sid]; s["text"] = b.text; s["findings"], s["mode"] = run_analysis(b.text)
    s["status"] = "Changes Required" if s["findings"] else "Draft"; s["history"].append(("revise", u["sub"], time.time())); return s
@app.post("/api/submissions/{sid}/submit")
def submit(sid: str, u=Depends(need("creator", "manager"))):
    s = SUBS[sid]
    if s["findings"]: raise HTTPException(400, "Resolve findings first")
    s["status"] = "Pending Review"; s["history"].append(("submit", u["sub"], time.time())); return s
class Decision(BaseModel): decision: str; comment: str = ""
@app.post("/api/submissions/{sid}/decide")
def decide(sid: str, b: Decision, u=Depends(need("approver"))):
    s = SUBS[sid]
    if s["status"] != "Pending Review": raise HTTPException(400, "Not pending review")
    s["status"] = {"approve": "Approved", "reject": "Rejected", "changes": "Changes Required"}[b.decision]
    s["comments"].append((u["sub"], b.comment)); s["history"].append((b.decision, u["sub"], time.time())); return s
@app.get("/api/ai-status")
def ai_status(u=Depends(user)): return {"llm_configured": ai_configured(), "mongo": DB is not None}
@app.get("/api/stats")
def stats(u=Depends(user)):
    c = {}
    for s in SUBS.values(): c[s["status"]] = c.get(s["status"], 0) + 1
    return {"total": len(SUBS), "by_status": c, "demo_data": False}

class Cross(BaseModel): ids: list[str]
PAT = {"price": r"[$£€]\s?\d[\d,]*(?:\.\d+)?", "percent": r"\d+(?:\.\d+)?\s?%", "date": r"\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b|\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]* \d{1,2}\b"}
@app.post("/api/cross-check")
def cross(b: Cross, u=Depends(user)):
    sel = [SUBS[i] for i in b.ids if i in SUBS]
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
async def visual_audit(file: UploadFile = File(...), alt: str = Form(""), u=Depends(user)):
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
    if ai_configured():
        try:
            media = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".webp": "image/webp"}[ext]
            prompt = ('Return JSON only: {"text": "all text visible in the image, exactly as written", "observations": ["short factual notes about the logo, colours, claims or accessibility visible in the image"]}. '
                      'Describe only what is visible. If unsure, say so. Do not invent text.')
            raw = call_ai(prompt, shrink(im, d, media))
            j = json.loads(re.sub(r"```(?:json)?", "", raw).strip())
            txt = str(j.get("text", ""))[:5000]
            tf, _ = run_analysis(txt) if txt.strip() else ([], "")
            extra = {"ai_used": True, "extracted_text": txt, "text_findings": tf, "observations": [str(x)[:300] for x in j.get("observations", [])[:8]]}
        except Exception as e: print("Image AI analysis failed:", e)
    return {**extra, "findings": F, "colour_match": share, "brand_colours": BRAND["colors"], "logo": logo, "limits": "Approximate checks only. No font recognition and no guaranteed logo verification."}