import { useEffect, useState } from "react";
import { LayoutDashboard, BookOpen, ScanSearch, CheckCircle2, LogOut, Menu, GitCompare, Lightbulb, Users, Image as ImageIcon, ShieldCheck, Network, BadgeCheck, Lock, Gauge, Settings as Cog } from "lucide-react";
const API = (import.meta.env.VITE_API_URL || "http://localhost:8000").replace(/\/$/, "") + "/api";
let token = sessionStorage.getItem("bg_token") || "";
const api = async (p: string, m = "GET", b?: unknown) => {
  const r = await fetch(API + p, { method: m, headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` }, body: b ? JSON.stringify(b) : undefined });
  if (r.status === 401 && token) { sessionStorage.clear(); window.location.reload(); }
  if (!r.ok) throw new Error((await r.json()).detail || "Request failed");
  return r.json();
};
const upl = async (p: string, fd: FormData) => { const r = await fetch(API + p, { method: "POST", headers: { Authorization: `Bearer ${token}` }, body: fd }); if (r.status === 401 && token) { sessionStorage.clear(); window.location.reload(); } if (!r.ok) throw new Error((await r.json()).detail || "Upload failed"); return r.json(); };
const card = "bg-white/90 border border-white rounded-2xl p-5 shadow-lg shadow-indigo-500/5 transition hover:-translate-y-0.5 hover:shadow-xl hover:shadow-indigo-500/10";
const btn = "px-4 py-2 rounded-xl bg-gradient-to-r from-indigo-600 to-cyan-500 text-white text-sm font-medium shadow-md shadow-indigo-500/30 transition hover:brightness-110 active:scale-95 disabled:opacity-50";
const sev: Record<string, string> = { high: "bg-red-100 text-red-700", medium: "bg-amber-100 text-amber-700", low: "bg-sky-100 text-sky-700" };

export default function App() {
  const [role, setRole] = useState(sessionStorage.getItem("bg_role") || ""); const [page, setPage] = useState("Overview"); const [open, setOpen] = useState(false);
  const [email, setEmail] = useState("creator@demo.com"); const [pw, setPw] = useState("demo1234"); const [err, setErr] = useState("");
  const login = async () => { try { const r = await api("/login", "POST", { email, password: pw }); token = r.token; sessionStorage.setItem("bg_token", r.token); sessionStorage.setItem("bg_role", r.role); setRole(r.role); } catch (e) { setErr((e as Error).message); } };
  if (!role) return (
    <div className="min-h-screen grid place-items-center p-4 bg-gradient-to-br from-indigo-600 via-violet-500 to-cyan-400"><div className={card + " w-full max-w-sm space-y-3"}>
      <h1 className="text-2xl font-bold">BrandGuard AI</h1><p className="text-sm text-slate-700">Brand governance, checked before you publish.</p>
      <select className="w-full border rounded-xl p-2" aria-label="Demo account" value={email} onChange={e => setEmail(e.target.value)}>
        {["creator", "manager", "approver"].map(r => <option key={r}>{r}@demo.com</option>)}</select>
      <input className="w-full border rounded-xl p-2" type="password" value={pw} onChange={e => setPw(e.target.value)} aria-label="Password" />
      {err && <p className="text-red-600 text-sm" role="alert">{err}</p>}
      <button className={btn + " w-full"} onClick={login}>Sign in</button>
      <p className="text-xs text-slate-700">Demo accounts, password demo1234.</p></div></div>);
  const nav = [["Overview", LayoutDashboard], ["Brand Guidelines", BookOpen], ["Approved Facts", BadgeCheck], ["Content Scanner", ScanSearch], ["Intent Lock", Lock], ["Cross-Channel Check", GitCompare], ["Visual Brand Audit", ImageIcon], ["Review & Approvals", CheckCircle2], ["Brand Intelligence", Lightbulb], ["Guideline Debt", Gauge], ["Knowledge Graph", Network], ["Team Management", Users], ["Settings", Cog]] as const;
  const hidden: Record<string, string[]> = { creator: ["Brand Intelligence", "Guideline Debt", "Team Management"], manager: [], approver: ["Content Scanner", "Team Management"] };
  const items = nav.filter(([n]) => !(hidden[role] ?? []).includes(n));
  return (<div className="min-h-screen md:flex md:p-4 md:gap-4"><a href="#main" className="sr-only focus:not-sr-only focus:absolute focus:z-50 focus:bg-white focus:p-2 focus:rounded">Skip to main content</a>
    <aside className={`${open ? "block" : "hidden"} md:flex md:flex-col w-full md:w-64 shrink-0 bg-white/90 md:rounded-3xl shadow-xl shadow-indigo-500/10 p-4 space-y-1 md:sticky md:top-4 md:h-[calc(100vh-2rem)] overflow-auto`}>
      <div className="flex items-center gap-3 mb-4"><div className="w-10 h-10 rounded-xl bg-gradient-to-br from-indigo-600 to-cyan-400 grid place-items-center text-white"><ShieldCheck size={20} /></div><b className="text-lg">BrandGuard <span className="text-[10px] bg-indigo-100 text-indigo-700 rounded px-1.5">AI</span></b></div>
      {items.map(([n, I]) => <button key={n} aria-current={page === n ? "page" : undefined} onClick={() => { setPage(n); setOpen(false); }} className={`flex gap-3 items-center w-full text-left px-3 py-2.5 rounded-xl text-sm font-medium transition ${page === n ? "bg-gradient-to-r from-indigo-600 to-cyan-500 text-white shadow-md shadow-indigo-500/30" : "text-slate-800 hover:bg-indigo-50 hover:translate-x-0.5"}`}><I size={18} />{n}</button>)}
      <div className="md:mt-auto pt-4"><button onClick={() => { sessionStorage.clear(); token = ""; setRole(""); setPage("Overview"); }} className="flex gap-2 items-center px-3 py-2 text-sm text-slate-700 hover:text-slate-800"><LogOut size={16} />Sign out ({role})</button></div>
    </aside>
    <main id="main" tabIndex={-1} className="fade flex-1 min-w-0 p-4 md:p-6 space-y-4"><div className="flex items-center gap-3"><button className="md:hidden" onClick={() => setOpen(!open)} aria-label="Menu"><Menu /></button><div><p className="text-xs text-slate-700">Governance › {page}</p><h2 className="text-2xl font-bold">{page}</h2></div></div>
      {page === "Overview" && <Overview go={p => setPage((hidden[role] ?? []).includes(p) ? "Review & Approvals" : p)} />}{page === "Brand Guidelines" && <Guidelines role={role} />}{page === "Approved Facts" && <Facts role={role} />}{page === "Intent Lock" && <IntentPage />}{page === "Guideline Debt" && <DebtPage role={role} />}
      {page === "Content Scanner" && <Scanner role={role} />}{page === "Review & Approvals" && <Review role={role} />}{page === "Cross-Channel Check" && <Cross />}{page === "Visual Brand Audit" && <Visual role={role} />}{page === "Brand Intelligence" && <Intel role={role} />}{page === "Team Management" && <Team role={role} />}{page === "Knowledge Graph" && <Graph />}{page === "Settings" && <SettingsPage role={role} />}</main></div>);
}
const col: Record<string, string> = { Approved: "#10B981", "Pending Review": "#6366F1", "Changes Required": "#F59E0B", Rejected: "#94A3B8", Draft: "#22D3EE" };
const chipCls: Record<string, string> = { Approved: "bg-emerald-100 text-emerald-700", "Pending Review": "bg-indigo-100 text-indigo-700", "Changes Required": "bg-amber-100 text-amber-700", Rejected: "bg-slate-200 text-slate-800", Draft: "bg-cyan-100 text-cyan-700" };
const Chip = ({ s }: { s: string }) => <span className={`text-xs font-medium px-2.5 py-0.5 rounded-full ${chipCls[s] || ""}`}>{s}</span>;
const TIERS = ["public", "internal", "restricted"];
const tierCls: Record<string, string> = { public: "bg-emerald-100 text-emerald-700", internal: "bg-sky-100 text-sky-700", restricted: "bg-red-100 text-red-700" };
const TIER_TEXT: Record<string, string> = { public: "Public: already approved for publishing. Checked by AI after personal data is removed.", internal: "Internal: a normal working draft. Checked by AI after personal data is removed.", restricted: "Restricted: confidential. Never sent to any AI provider; rule-based checks only, and visible only to you, managers and approvers." };
const TierChip = ({ t }: { t?: string }) => <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${tierCls[t || "internal"]}`}>{t || "internal"}</span>;
const TierPick = ({ v, on }: { v: string; on: (t: string) => void }) => <label className="text-xs block">Confidentiality tier
  <select className="block border rounded-xl p-2 text-sm mt-1" value={v} onChange={e => on(e.target.value)}>{TIERS.map(t => <option key={t} value={t}>{t}</option>)}</select>
  <span className="block text-slate-700 mt-1">{TIER_TEXT[v]}</span></label>;
function Overview({ go }: { go: (p: string) => void }) {
  const [subs, setSubs] = useState<any[]>([]); useEffect(() => { api("/submissions").then(setSubs); }, []);
  const by: Record<string, number> = {}; subs.forEach(s => by[s.status] = (by[s.status] || 0) + 1);
  const viol: Record<string, number> = {}; subs.forEach(s => s.findings.forEach((f: any) => viol[f.guideline] = (viol[f.guideline] || 0) + 1));
  const T = subs.length, R = 52, C = 2 * Math.PI * R; let off = 0; const max = Math.max(1, ...Object.values(viol));
  const stats = [["Total content", T, "from-indigo-500 to-violet-500", ScanSearch], ["Need changes", by["Changes Required"] || 0, "from-amber-400 to-orange-500", Lightbulb], ["Pending approval", by["Pending Review"] || 0, "from-sky-500 to-cyan-400", CheckCircle2], ["Approved", by["Approved"] || 0, "from-emerald-500 to-teal-400", ShieldCheck]] as const;
  return <div className="space-y-4">
    <div className="rounded-3xl p-6 text-white bg-gradient-to-r from-indigo-600 via-violet-500 to-cyan-400 shadow-xl shadow-indigo-500/20 flex flex-wrap items-center justify-between gap-3"><div><h3 className="text-xl font-bold">Keep every message on brand</h3><p className="text-sm opacity-90">Scan content, review evidence, approve with confidence.</p></div><button onClick={() => go("Content Scanner")} className="px-4 py-2 rounded-xl bg-white text-indigo-700 font-semibold transition hover:scale-105 active:scale-95">Scan New Content</button></div>
    <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">{stats.map(([l, v, g, I]) => <div key={l} className={card}><div className={`w-9 h-9 rounded-xl bg-gradient-to-br ${g} grid place-items-center text-white mb-2`}><I size={18} /></div><p className="text-xs text-slate-700">{l}</p><p className="text-3xl font-bold">{v}</p></div>)}</div>
    <div className="grid md:grid-cols-2 gap-4">
      <div className={card}><b>Submissions by status</b>{T ? <div className="flex items-center gap-4 mt-3"><svg viewBox="0 0 140 140" className="w-36 h-36 shrink-0" role="img" aria-label="Submissions by status">{Object.entries(by).map(([k, v]) => { const l = v / T * C; const e = <circle key={k} r={R} cx="70" cy="70" fill="none" stroke={col[k]} strokeWidth="18" strokeDasharray={`${l} ${C - l}`} strokeDashoffset={-off} transform="rotate(-90 70 70)" />; off += l; return e; })}<text x="70" y="76" textAnchor="middle" fontSize="24" fontWeight="700" fill="#172033">{T}</text></svg><div className="text-sm space-y-1">{Object.entries(by).map(([k, v]) => <div key={k}><span className="inline-block w-2 h-2 rounded-full mr-2" style={{ background: col[k] }} />{k} ({v})</div>)}</div></div> : <p className="text-sm text-slate-700 mt-3">Scan content to see this chart.</p>}</div>
      <div className={card}><b>Violations by rule</b>{Object.keys(viol).length ? <div className="flex items-end gap-3 h-36 mt-3">{Object.entries(viol).map(([k, v]) => <div key={k} className="flex-1 text-center text-xs"><div>{v}</div><div className="rounded-t-lg bg-gradient-to-t from-indigo-600 to-cyan-400 transition-all duration-700" style={{ height: `${(v / max) * 100}px`, minHeight: 4 }} /><div className="text-slate-700">{k}</div></div>)}</div> : <p className="text-sm text-slate-700 mt-3">No violations recorded yet.</p>}</div></div>
    <div className={card}><b>Recent content activity</b>{subs.length ? subs.slice(-5).reverse().map(s => <div key={s.id} className="flex justify-between items-center py-2 border-t first:border-0 text-sm"><span>{s.title}</span><Chip s={s.status} /></div>) : <p className="text-sm text-slate-700 mt-2">No activity yet.</p>}</div></div>;
}
const Cite = ({ c }: { c?: any }) => !c ? <p className="text-xs text-red-700">No citation</p> : <p className="text-xs text-slate-700">Cites {c.label} · source: {c.source}{c.type === "fact" && <> · owner: {c.owner} · expires {c.expires}{c.state === "expired" && <b className="text-red-700"> (EXPIRED)</b>}</>}</p>;
const factCls: Record<string, string> = { approved: "bg-emerald-100 text-emerald-700", expiring: "bg-amber-100 text-amber-700", expired: "bg-red-100 text-red-700" };
function Facts({ role }: { role: string }) {
  const [l, setL] = useState<any[]>([]); const [rep, setRep] = useState<any>(); const [demo, setDemo] = useState<any>(); const [err, setErr] = useState("");
  const empty = { statement: "", keywords: "", source: "", owner: "", expires: "" }; const [f, setF] = useState(empty); const [ren, setRen] = useState<Record<string, string>>({});
  const load = () => { api("/facts").then(setL); api("/evidence-report").then(setRep); }; useEffect(() => { load(); }, []);
  const can = role !== "creator";
  const run = async (fn: () => Promise<any>) => { try { setErr(""); await fn(); load(); } catch (e) { setErr((e as Error).message); } };
  const tiles = rep ? [["Findings cited", `${rep.cited} of ${rep.findings}`], ["Uncited findings", rep.uncited], ["UNVERIFIED claims", rep.unverified], ["Verified claims", rep.verified_claims], ["Expired facts", rep.facts_expired]] : [];
  return <div className="space-y-3">
    <div className={card + " space-y-2"}><b>Evidence report</b><p className="text-xs text-slate-700">Every finding must cite an approved rule or fact. A claim with no valid fact is labelled UNVERIFIED and is never shown as a fact.</p>
      <div className="grid grid-cols-2 md:grid-cols-5 gap-2">{tiles.map(([k, v]) => <div key={String(k)} className="border rounded-xl p-2 text-center"><p className="text-xs text-slate-700">{k}</p><p className={`text-xl font-bold ${k === "Uncited findings" ? (v === 0 ? "text-emerald-600" : "text-red-600") : ""}`}>{v}</p></div>)}</div>
      <button className={btn} onClick={() => run(async () => setDemo(await api("/evidence-demo")))}>Run demo set</button>
      {demo && <div className="text-sm space-y-2"><p><b>Demo set:</b> {demo.findings} findings, <b className={demo.uncited === 0 ? "text-emerald-600" : "text-red-600"}>{demo.uncited} uncited</b>, {demo.unverified} UNVERIFIED, {demo.verified_claims} verified claims. Engine: {demo.engine}.</p>
        {demo.rows.map((r: any, i: number) => <div key={i} className="border rounded-xl p-2 space-y-1"><p>“{r.text}”</p>
          {r.findings.map((x: any, j: number) => <div key={j} className="pl-3 border-l-2 border-slate-200"><p className="text-xs">{x.verification === "UNVERIFIED" && <b className="text-red-700">UNVERIFIED </b>}{x.title}</p><Cite c={x.citation} /></div>)}
          {r.verified.map((v: any, j: number) => <div key={j} className="pl-3 border-l-2 border-emerald-300"><p className="text-xs"><b className="text-emerald-700">Verified </b>“{v.original}”</p><Cite c={v.citation} /></div>)}
          {!r.findings.length && !r.verified.length && <p className="text-xs text-slate-700">No findings.</p>}</div>)}</div>}</div>
    {err && <p className="text-red-600 text-sm" role="alert">{err}</p>}
    {can ? <div className={card + " grid gap-2 md:grid-cols-2"}><b className="md:col-span-2">Add an approved fact</b>
      <input className="border rounded-xl p-2 text-sm md:col-span-2" placeholder="Approved statement, e.g. 100% of pilot reviewers completed onboarding without help." aria-label="Approved statement" value={f.statement} onChange={e => setF({ ...f, statement: e.target.value })} />
      <input className="border rounded-xl p-2 text-sm" placeholder="Keywords, comma separated" aria-label="Keywords" value={f.keywords} onChange={e => setF({ ...f, keywords: e.target.value })} />
      <input className="border rounded-xl p-2 text-sm" placeholder="Source document" aria-label="Source document" value={f.source} onChange={e => setF({ ...f, source: e.target.value })} />
      <input className="border rounded-xl p-2 text-sm" placeholder="Owner (who answers for this fact)" aria-label="Owner" value={f.owner} onChange={e => setF({ ...f, owner: e.target.value })} />
      <input type="date" className="border rounded-xl p-2 text-sm" aria-label="Expiry date" value={f.expires} onChange={e => setF({ ...f, expires: e.target.value })} />
      <button className={btn} onClick={() => run(async () => { await api("/facts", "POST", f); setF(empty); })}>Add fact</button>
      <p className="text-xs text-slate-700 md:col-span-2">A claim such as “100%” or “#1” is supported only when the fact mentions that claim and every keyword appears in the same sentence. Use distinctive phrases, not single common words.</p></div>
      : <p className="text-sm text-slate-700">Creators can view approved facts; managers and approvers maintain them.</p>}
    {l.map(x => <div key={x.id} className={card + " space-y-1"}><div className="flex justify-between gap-2"><div><b>{x.statement}</b> <span className={`text-xs px-2 rounded ${factCls[x.state] || ""}`}>{x.state}</span> <span className="text-xs px-2 rounded bg-indigo-100 text-indigo-700">{x.id}</span></div>
      {can && <button className="text-sm text-red-600" onClick={() => run(() => api("/facts/" + x.id, "DELETE"))}>Delete</button>}</div>
      <p className="text-xs text-slate-700">Keywords: {x.keywords.join(", ")} · Source: {x.source} · Owner: {x.owner} · Expires {x.expires}</p>
      {can && <div className="flex gap-2 items-center"><input type="date" className="border rounded-xl p-1 text-xs" aria-label={`New expiry date for ${x.id}`} value={ren[x.id] || ""} onChange={e => setRen({ ...ren, [x.id]: e.target.value })} /><button className="text-sm text-indigo-600 disabled:opacity-40" disabled={!ren[x.id]} onClick={() => run(() => api(`/facts/${x.id}/renew`, "POST", { expires: ren[x.id] }))}>Renew</button></div>}</div>)}</div>;
}
const Mark = ({ text, hit, cls }: { text: string; hit: string; cls: string }) => { const i = hit ? text.toLowerCase().indexOf(hit.toLowerCase()) : -1; return i < 0 ? <>{text}</> : <>{text.slice(0, i)}<mark className={cls}>{text.slice(i, i + hit.length)}</mark>{text.slice(i + hit.length)}</>; };
const lockCls: Record<string, string> = { keeps: "bg-emerald-100 text-emerald-700", check: "bg-amber-100 text-amber-700", blocked: "bg-red-100 text-red-700" };
const lockText: Record<string, string> = { keeps: "Keeps your purpose", check: "Check before accepting", blocked: "Blocked: would change your purpose" };
function LockPanel({ x }: { x: any }) {
  const k = x.lock; if (!k) return null; const sug = x.suggestion || x.blocked_suggestion || "";
  return <div className="border rounded-xl p-2 space-y-1 bg-slate-50"><p className="text-xs"><b>Intent Lock</b> <span className={`px-2 py-0.5 rounded ${lockCls[k.verdict] || ""}`}>{lockText[k.verdict]}</span> · Purpose score <b>{k.score}/100</b>{k.occurrences > 1 && ` · applies in ${k.occurrences} places`}{!k.purpose_given && " · no purpose given, safety checks only"}</p>
    <div className="grid md:grid-cols-2 gap-2 text-xs"><div className="border rounded-lg p-2 bg-white"><p className="text-slate-600 mb-1">Before</p><p><Mark text={k.before} hit={x.original} cls="bg-red-100 line-through" /></p></div>
      <div className="border rounded-lg p-2 bg-white"><p className="text-slate-600 mb-1">{k.verdict === "blocked" ? "After (not offered)" : "After"}</p><p><Mark text={k.after} hit={sug} cls="bg-emerald-100" /></p></div></div>
    <ul className="text-xs list-disc pl-4">{k.checks.filter((c: any) => c.status !== "n/a").map((c: any) => <li key={c.name} className={c.status === "fail" ? "text-red-700" : c.status === "warn" ? "text-amber-700" : "text-slate-700"}><b>{c.name}</b> ({c.status}): {c.detail}</li>)}</ul>
    {k.ai ? <p className="text-xs">AI judge: {k.ai.score}/100 · {k.ai.reason}</p> : <p className="text-xs text-slate-600">AI judge not used for this fix.</p>}</div>;
}
function IntentPage() {
  const [d, setD] = useState<any>(); const [err, setErr] = useState("");
  useEffect(() => { api("/intent-eval").then(setD).catch(e => setErr(e.message)); }, []);
  const tiles = d ? [["Accepted fixes that keep purpose", d.pct === null ? "n/a" : `${d.pct}%`], ["Target", "at least 90%"], ["Bad fixes blocked", `${d.bad_blocked} of ${d.bad_fixes}`], ["Good fixes wrongly blocked", d.good_blocked]] : [];
  return <div className="space-y-3"><div className={card + " space-y-2"}><b>Intent Lock</b>
    <p className="text-sm text-slate-700">Before a suggested fix is shown, it is checked against the creator's audience, core message and call to action. A fix that would change the purpose is blocked and never offered. Add your purpose on the Content Scanner page.</p>
    <p className="text-xs text-slate-700">Checks: call to action kept, core message kept, audience kept, no new numbers or claims, size of change. If an AI key is set, an AI judge gives a second opinion that can only make the lock stricter.</p></div>
    {err && <p className="text-red-600 text-sm" role="alert">{err}</p>}
    {d && <div className={card + " space-y-2"}><b>Golden test set result</b>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-2">{tiles.map(([k, v]) => <div key={String(k)} className="border rounded-xl p-2 text-center"><p className="text-xs text-slate-700">{k}</p><p className={`text-xl font-bold ${k === "Accepted fixes that keep purpose" ? (d.met ? "text-emerald-600" : "text-red-600") : ""}`}>{v}</p></div>)}</div>
      <p className="text-xs text-slate-700">{d.accepted_keep_purpose} of {d.accepted} accepted fixes keep the original purpose, out of {d.fixes} labelled fixes. Engine: {d.engine}. This is a starter set written by the team: add real cases before relying on the number.</p>
      <div className="overflow-x-auto"><table className="w-full text-xs"><thead><tr className="text-left text-slate-700"><th className="p-1">Case</th><th className="p-1">Change</th><th className="p-1">Score</th><th className="p-1">Lock says</th><th className="p-1">Person says</th><th className="p-1">Match</th></tr></thead>
        <tbody>{d.rows.map((r: any, i: number) => <tr key={i} className="border-t"><td className="p-1">{r.case}</td><td className="p-1">“{r.original}” → “{r.suggestion}”</td><td className="p-1">{r.score}</td><td className="p-1"><span className={`px-2 rounded ${lockCls[r.verdict] || ""}`}>{r.verdict}</span></td><td className="p-1">{r.gold_keeps ? "keeps purpose" : "changes purpose"}</td><td className="p-1">{r.correct ? "✓" : <span className="text-red-700">miss{r.known_gap && `: ${r.known_gap}`}</span>}</td></tr>)}</tbody></table></div></div>}</div>;
}
const impactText: Record<string, string> = { fewer: "Fewer waivers ✓", waiting: "Waiting for more new content", "not-fewer": "No improvement yet", "no-baseline": "No baseline to compare" };
function Replay({ b }: { b: any }) {
  return <div className="text-xs space-y-1"><p><b>Replay on past content:</b> <span className={`px-2 rounded ${b.passed ? "bg-emerald-100 text-emerald-700" : "bg-red-100 text-red-700"}`}>{b.passed ? "Safe to approve" : "Not safe to approve"}</span></p>
    <p>Contested findings avoided: <b>{b.contested_removed} of {b.contested_total}</b>{b.avoided_pct !== null && ` (${b.avoided_pct}%)`} · Real violations still caught: <b>{b.true_kept} of {b.true_total}</b> · New findings added: <b>{b.new_matches}</b></p>
    <div className="overflow-x-auto"><table className="w-full"><thead><tr className="text-left text-slate-700"><th className="p-1">Past content</th><th className="p-1">Was</th><th className="p-1">With rewrite</th></tr></thead>
      <tbody>{b.rows.map((r: any, i: number) => <tr key={i} className="border-t"><td className="p-1">{r.sentence}</td><td className="p-1">{r.was === "contested" ? `contested (${r.event || "?"})` : "real violation"}</td>
        <td className="p-1">{r.still_flagged ? <span className={r.was === "violation" ? "text-emerald-700" : "text-amber-700"}>still flagged</span> : <span className={r.was === "violation" ? "text-red-700 font-bold" : "text-emerald-700"}>{r.was === "violation" ? "LOST" : "no longer flagged"}</span>}</td></tr>)}</tbody></table></div></div>;
}
function DebtPage({ role }: { role: string }) {
  const [d, setD] = useState<any>(); const [err, setErr] = useState(""); const [busy, setBusy] = useState("");
  const [edit, setEdit] = useState<Record<string, { ex: string; g: string }>>({}); const [bt, setBt] = useState<Record<string, any>>({});
  const load = () => api("/debt").then(setD).catch(e => setErr(e.message)); useEffect(() => { load(); }, []);
  const can = role === "manager";
  const run = async (key: string, fn: () => Promise<any>) => { setBusy(key); setErr(""); try { await fn(); await load(); } catch (e) { setErr((e as Error).message); } setBusy(""); };
  const drop = (k: string) => { setEdit(p => { const n = { ...p }; delete n[k]; return n; }); setBt(p => { const n = { ...p }; delete n[k]; return n; }); };
  const cur = (gid: string, dr: any) => edit[gid] ?? { ex: dr.proposed.exceptions.join(", "), g: dr.proposed.guidance };
  const body = (gid: string, dr: any) => { const e = cur(gid, dr); return { exceptions: e.ex.split(",").map(x => x.trim()).filter(Boolean), guidance: e.g }; };
  if (!d) return err ? <p className="text-red-600 text-sm" role="alert">{err}</p> : <p className="text-sm text-slate-700">Loading…</p>;
  return <div className="space-y-3"><div className={card + " space-y-2"}><b>Guideline Debt</b>
    <p className="text-sm text-slate-700">Every waiver and dispute is a sign a rule may be unclear. A rule with {d.threshold} or more is flagged. A manager can draft a clearer rewrite, replay it against past content, and approve it only if it keeps catching real violations.</p>
    <div className="grid grid-cols-2 md:grid-cols-4 gap-2">{[["Rules flagged", d.flagged], ["Waivers", d.waivers], ["Disputes", d.disputes], ["Flag threshold", d.threshold]].map(([k, v]) => <div key={String(k)} className="border rounded-xl p-2 text-center"><p className="text-xs text-slate-700">{k}</p><p className="text-xl font-bold">{v}</p></div>)}</div>
    {can && <div className="flex gap-2 items-center flex-wrap"><button className={btn} disabled={d.demo_loaded || busy === "demo"} onClick={() => run("demo", () => api("/debt-demo", "POST"))}>Load demo history</button>{d.demo_loaded && <button className="text-sm text-red-600" onClick={() => run("demo", () => api("/debt-demo", "DELETE"))}>Clear demo history</button>}
      <span className="text-xs text-slate-700">Demo history is sample data (past waivers and disputes) so you can show the loop. It is labelled and removable.</span></div>}</div>
    {err && <p className="text-red-600 text-sm" role="alert">{err}</p>}
    {d.rules.map((r: any) => <div key={r.id} className={card + " space-y-2"}>
      <div className="flex justify-between gap-2 flex-wrap"><div><b>{r.category}: {r.pattern}</b>{r.fix && ` → ${r.fix}`} <span className="text-xs px-2 rounded bg-indigo-100 text-indigo-700">v{r.version}</span> <span className={`text-xs px-2 rounded ${r.flagged ? "bg-red-100 text-red-700" : "bg-emerald-100 text-emerald-700"}`}>{r.flagged ? "Flagged" : "OK"}</span></div>
        <p className="text-sm">{r.waivers} waivers · {r.disputes} disputes · debt {r.debt}/{d.threshold}</p></div>
      {r.exceptions.length > 0 && <p className="text-xs text-slate-700">Exceptions: {r.exceptions.join(", ")}</p>}{r.guidance && <p className="text-xs">{r.guidance}</p>}
      {r.recent.map((e: any, i: number) => <p key={i} className="text-xs text-slate-700">{e.kind} ({e.status}){e.demo ? " [demo]" : ""}: {e.reason} — “{e.sentence}”</p>)}
      {r.flagged && can && !r.has_draft && <button className={btn} disabled={busy === r.id} onClick={() => run(r.id, () => api(`/debt/${r.id}/draft`, "POST"))}>Draft a clearer rewrite</button>}
      {r.has_draft && (() => { const dr = d.drafts[r.id]; const e = cur(r.id, dr); const edited = !!edit[r.id]; const b = edited ? bt[r.id] : dr.backtest;
        return <div className="border rounded-xl p-3 space-y-2 bg-slate-50"><p className="text-sm"><b>Draft rewrite</b> <span className="text-xs text-slate-700">(wording by {dr.engine === "ai" ? "AI" : "rules"}; exceptions found from {dr.based_on} waivers and disputes)</span></p>
          <label className="text-xs block">Exceptions (comma separated)<input className="w-full border rounded-xl p-2 text-sm" value={e.ex} disabled={!can} onChange={ev => { setEdit({ ...edit, [r.id]: { ...e, ex: ev.target.value } }); setBt(p => { const n = { ...p }; delete n[r.id]; return n; }); }} /></label>
          <label className="text-xs block">Clearer rule text<textarea className="w-full border rounded-xl p-2 text-sm" rows={2} value={e.g} disabled={!can} onChange={ev => { setEdit({ ...edit, [r.id]: { ...e, g: ev.target.value } }); setBt(p => { const n = { ...p }; delete n[r.id]; return n; }); }} /></label>
          {b ? <Replay b={b} /> : <p className="text-xs text-amber-700">You changed the draft. Test it against past content again before approving.</p>}
          {can && <div className="flex gap-2 flex-wrap items-center"><button className={btn} onClick={() => run("t" + r.id, async () => setBt({ ...bt, [r.id]: await api(`/debt/${r.id}/backtest`, "POST", body(r.id, dr)) }))}>Test against past content</button>
            <button className={btn} disabled={!b || !b.passed} onClick={() => run("a" + r.id, async () => { await api(`/debt/${r.id}/approve`, "POST", body(r.id, dr)); drop(r.id); })}>Approve rewrite</button>
            <button className="text-sm text-red-600" onClick={() => run("x" + r.id, async () => { await api(`/debt/${r.id}/draft`, "DELETE"); drop(r.id); })}>Discard</button></div>}</div>; })()}
      {r.impact && <p className="text-xs border-t pt-2"><b>After the rewrite (v{r.impact.version}):</b> waivers and disputes per piece of content that mentions this rule. Before {r.impact.before.events} of {r.impact.before.exposure}{r.impact.before.rate !== null && ` (${r.impact.before.rate})`}, after {r.impact.after.events} of {r.impact.after.exposure}{r.impact.after.rate !== null && ` (${r.impact.after.rate})`}. <b className={r.impact.verdict === "fewer" ? "text-emerald-700" : "text-slate-700"}>{impactText[r.impact.verdict]}</b></p>}</div>)}</div>;
}
function Graph() {
  const [g, setG] = useState<any[]>([]); const [subs, setSubs] = useState<any[]>([]);
  useEffect(() => { api("/guidelines").then(setG); api("/submissions").then(setSubs); }, []);
  return <div className="space-y-3"><div className={card}><b>Brand → Guidelines → Content</b><p className="text-sm text-slate-700">If a rule changes, these submissions may be affected.</p></div>
    {g.map(x => { const a = subs.filter(s => s.findings.some((f: any) => f.guideline === x.id)); return <div key={x.id} className={card}><b>{x.category}</b> <span className="text-xs px-2 rounded bg-indigo-100 text-indigo-700">{x.id}</span><p className="text-sm">{x.pattern} {x.fix && `→ ${x.fix}`}</p><p className="text-xs text-slate-700">Linked content: {a.length ? a.map(s => s.title).join(", ") : "none yet"}</p></div>; })}</div>;
}
function SettingsPage({ role }: { role: string }) {
  const [s, setS] = useState<any>(); useEffect(() => { api("/ai-status").then(setS).catch(() => {}); }, []);
  return <div className="space-y-3"><div className={card}><b>Profile</b><p className="text-sm">Role: {role}</p></div><div className={card}><b>AI provider</b><p className="text-sm">{s?.llm_configured ? "AI model connected (key held on the backend)." : "No API key set: scans use the labelled demo rules."}</p></div><div className={card}><b>Storage</b><p className="text-sm">{s?.mongo ? "MongoDB connected." : "In-memory only; data resets on restart."}</p></div><PrivacyPanel role={role} /></div>;
}
function PrivacyPanel({ role }: { role: string }) {
  const [d, setD] = useState<any>(); const [log, setLog] = useState<any>(); const [err, setErr] = useState(""); const staff = role !== "creator";
  useEffect(() => { api("/ai-disclosure").then(setD).catch(e => setErr(e.message)); if (staff) api("/ai-log").then(setLog).catch(e => setErr(e.message)); }, []);
  if (!d) return err ? <p className="text-red-600 text-sm" role="alert">{err}</p> : null;
  const tiles = [["Sent to AI", d.totals.sent], ["Blocked (restricted)", d.totals.blocked], ["Failed", d.totals.failed], ["Items redacted", d.totals.items_redacted]];
  return <div className="space-y-3">
    <div className={card + " space-y-2"}><b>AI disclosure</b>
      <p className="text-sm">AI provider: <b>{d.provider}</b>. {d.what_is_sent}</p><p className="text-sm">{d.human_control}</p><p className="text-xs text-slate-700">{d.retention}</p>
      <div className="grid md:grid-cols-2 gap-2 text-xs"><div className="border rounded-xl p-2"><b>Removed before sending</b><ul className="list-disc pl-4">{d.redaction.detects.map((x: string) => <li key={x}>{x}</li>)}</ul></div>
        <div className="border rounded-xl p-2"><b>Not detected: keep these out of AI scans</b><ul className="list-disc pl-4">{d.redaction.cannot_detect.map((x: string) => <li key={x}>{x}</li>)}</ul></div></div></div>
    <div className={card + " space-y-2"}><b>Confidentiality tiers</b>{d.tiers.map((t: any) => <p key={t.tier} className="text-sm"><TierChip t={t.tier} /> {t.ai_allowed ? "AI allowed" : "AI blocked"}: {t.description}</p>)}</div>
    <div className="grid grid-cols-2 md:grid-cols-4 gap-2">{tiles.map(([k, v]) => <div key={String(k)} className={card + " text-center"}><p className="text-xs text-slate-700">{k}</p><p className="text-2xl font-bold">{v}</p></div>)}</div>
    {staff && log && <div className={card + " space-y-2"}><b>AI send log</b><p className="text-xs text-slate-700">Every call to an AI provider, newest first. Only the redacted text is stored. {log.total} entries (last 500 kept).</p>
      {!log.entries.length && <p className="text-sm text-slate-700">No AI calls yet.</p>}
      <div className="overflow-x-auto"><table className="w-full text-xs"><thead><tr className="text-left text-slate-700"><th className="p-1">When</th><th className="p-1">User</th><th className="p-1">Tier</th><th className="p-1">Purpose</th><th className="p-1">Result</th><th className="p-1">Redacted</th><th className="p-1">What was sent</th></tr></thead>
        <tbody>{log.entries.map((e: any) => <tr key={e.id} className="border-t align-top"><td className="p-1">{new Date(e.ts * 1000).toLocaleString()}</td><td className="p-1">{e.user}</td><td className="p-1"><TierChip t={e.tier} /></td><td className="p-1">{e.purpose}</td>
          <td className="p-1"><span className={e.status === "sent" ? "text-emerald-700" : e.status === "blocked" ? "text-red-700" : "text-amber-700"}>{e.status}</span>{e.reason && <span className="block text-slate-600">{e.reason}</span>}</td>
          <td className="p-1">{Object.keys(e.redactions).length ? Object.entries(e.redactions).map(([k, v]) => `${k} ${v}`).join(", ") : "none"}</td>
          <td className="p-1">{e.sent ? <details><summary className="cursor-pointer text-indigo-600">{e.chars} chars · {e.sha256}</summary><pre className="whitespace-pre-wrap max-w-md">{e.sent}</pre></details> : "nothing sent"}</td></tr>)}</tbody></table></div></div>}
    {err && <p className="text-red-600 text-sm" role="alert">{err}</p>}</div>;
}
function Guidelines({ role }: { role: string }) {
  const [g, setG] = useState<any[]>([]); const [f, setF] = useState({ category: "Terminology", priority: "medium", kind: "term", pattern: "", fix: "", source: "" });
  const [err, setErr] = useState(""); const load = () => api("/guidelines").then(setG); useEffect(() => { load(); }, []);
  const can = role !== "creator";
  return <div className="space-y-3">{can ? <div className={card + " grid gap-2 md:grid-cols-3"}>
    {(["pattern", "fix", "source"] as const).map(k => <input key={k} className="border rounded-xl p-2 text-sm" aria-label={k} placeholder={k} value={f[k]} onChange={e => setF({ ...f, [k]: e.target.value })} />)}
    <button className={btn} onClick={async () => { try { await api("/guidelines", "POST", f); setF({ ...f, pattern: "", fix: "", source: "" }); load(); } catch (e) { setErr((e as Error).message); } }}>Add rule</button>
    {err && <p className="text-red-600 text-sm">{err}</p>}</div> : <p className="text-sm text-slate-700">Creators can view guidelines; managers edit them.</p>}
    {g.map(x => <div key={x.id} className={card + " flex justify-between gap-3"}><div><b>{x.category}</b> <span className={`text-xs px-2 rounded ${sev[x.priority] || ""}`}>{x.priority}</span>{x.version > 1 && <span className="text-xs px-2 rounded bg-indigo-100 text-indigo-700"> v{x.version}</span>}
      <p className="text-sm">{x.pattern} {x.fix && `→ ${x.fix}`}</p><p className="text-xs text-slate-700">{x.source || "No source document"}</p>{x.guidance && <p className="text-xs">{x.guidance}</p>}{x.exceptions?.length > 0 && <p className="text-xs text-slate-700">Exceptions: {x.exceptions.join(", ")}</p>}</div>
      {can && <button className="text-sm text-red-600" onClick={async () => { await api("/guidelines/" + x.id, "DELETE"); load(); }}>Delete</button>}</div>)}</div>;
}
function Findings({ s, onFix, onContest }: { s: any; onFix: (t: string, accepted?: any) => void; onContest: (i: number, kind: string, reason: string) => void }) {
  const [ct, setCt] = useState<{ i: number; kind: string } | null>(null); const [why, setWhy] = useState("");
  const contestUi = (x: any, i: number) => x.contest ? <p className="text-xs border rounded-lg p-2 bg-slate-50"><b>{x.contest.kind === "waiver" ? "Waiver requested" : "Rule disputed"}</b> ({x.contest.status}): {x.contest.reason}</p>
    : ct?.i === i ? <div className="space-y-1"><input className="w-full border rounded-xl p-2 text-xs" placeholder={ct.kind === "waiver" ? "Why does this need to be published as written?" : "Why is this rule unclear or wrong here?"} aria-label="Reason" value={why} onChange={e => setWhy(e.target.value)} />
      <div className="flex gap-2 items-center"><button className={btn} disabled={why.trim().length < 5} onClick={() => { onContest(i, ct.kind, why); setCt(null); setWhy(""); }}>Send {ct.kind}</button><button className="text-xs" onClick={() => setCt(null)}>Cancel</button></div></div>
    : <div className="flex gap-3 text-xs"><button className="text-amber-700" onClick={() => setCt({ i, kind: "waiver" })}>Request waiver</button><button className="text-slate-700" onClick={() => setCt({ i, kind: "dispute" })}>Dispute this rule</button></div>;
  const [text, setText] = useState(s.text); useEffect(() => setText(s.text), [s.text]);
  return <div className="space-y-2"><p className="text-sm">Status: <Chip s={s.status} /> · Risk: {s.risk} · Tier: <TierChip t={s.tier} /> · Engine: {s.mode === "llm" ? "AI model (validated against your guidelines)" : s.mode === "restricted-rules" ? "rule-based checks only (restricted content is never sent to an AI)" : "demo rules (not real AI)"}{s.needs_human && " · human approval required"}</p>
    {s.findings.map((x: any, i: number) => <div key={i} className="border rounded-xl p-3 text-sm space-y-1"><b>{x.title}</b> <span className={`text-xs px-2 rounded ${sev[x.severity]}`}>{x.severity}</span> <i className="text-xs">{x.status}</i>{x.verification === "UNVERIFIED" && <span className="text-xs font-bold px-2 py-0.5 rounded bg-red-600 text-white">UNVERIFIED</span>}
      <p>Original: “{x.original}”</p><p className="text-slate-800">Evidence: {x.evidence}</p><Cite c={x.citation} />{x.confidence && <p className="text-xs">Confidence: {x.confidence}</p>}{x.explanation && <p className="text-xs">{x.explanation}</p>}
      <LockPanel x={x} />{x.suggestion && <button className="text-indigo-600" onClick={() => onFix(s.text.replace(new RegExp(x.original.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"), "gi"), () => x.suggestion), { guideline: x.guideline, verdict: x.lock?.verdict || "", score: x.lock?.score ?? "" })}>{x.lock?.verdict === "check" ? "Accept after review" : "Accept suggestion"}</button>}{contestUi(x, i)}</div>)}
    {s.verified?.length > 0 && <div className="border border-emerald-200 bg-emerald-50 rounded-xl p-3 text-sm space-y-1"><b>Verified claims (backed by an approved fact)</b>{s.verified.map((v: any, i: number) => <div key={i}><p>“{v.original}” in: {v.sentence}</p><Cite c={v.citation} /></div>)}</div>}
    <textarea className="w-full border rounded-xl p-2 text-sm" rows={4} value={text} onChange={e => setText(e.target.value)} aria-label="Edit content" />
    <button className={btn} onClick={() => onFix(text)}>Rescan edited text</button></div>;
}
function Scanner({ role }: { role: string }) {
  const [t, setT] = useState(""); const [text, setText] = useState(""); const [s, setS] = useState<any>(); const [err, setErr] = useState(""); const [busy, setBusy] = useState(false);
  const [aud, setAud] = useState(""); const [msg, setMsg] = useState(""); const [cta, setCta] = useState("");
  const [tier, setTier] = useState("internal"); const [pv, setPv] = useState<any>(); const [dis, setDis] = useState<any>(); useEffect(() => { api("/ai-disclosure").then(setDis).catch(() => {}); }, []);
  const run = async (fn: () => Promise<any>) => { setBusy(true); setErr(""); try { setS(await fn()); } catch (e) { setErr((e as Error).message); } setBusy(false); };
  const run0 = async (fn: () => Promise<any>) => { setErr(""); try { await fn(); } catch (e) { setErr((e as Error).message); } };
  const up = async (f?: File) => { if (!f) return; const fd = new FormData(); fd.append("file", f); try { setErr(""); setText((await upl("/upload-text", fd)).text); } catch (e) { setErr((e as Error).message); } };
  if (role === "approver") return <p className="text-sm">Approvers review submissions under Review & Approvals.</p>;
  return <div className={card + " space-y-3"}><input className="w-full border rounded-xl p-2" aria-label="Content title" placeholder="Content title" value={t} onChange={e => setT(e.target.value)} />
    <div className="grid md:grid-cols-3 gap-2"><input className="border rounded-xl p-2 text-sm" placeholder="Audience, e.g. first-year students" aria-label="Audience" value={aud} onChange={e => setAud(e.target.value)} /><input className="border rounded-xl p-2 text-sm" placeholder="Core message" aria-label="Core message" value={msg} onChange={e => setMsg(e.target.value)} /><input className="border rounded-xl p-2 text-sm" placeholder="Call to action, e.g. Sign up today" aria-label="Call to action" value={cta} onChange={e => setCta(e.target.value)} /></div>
    <p className="text-xs text-slate-700">Intent Lock uses these to make sure every suggested fix still serves your purpose. Leave them blank to run only the basic safety checks.</p>
    <TierPick v={tier} on={x => { setTier(x); setPv(undefined); }} />
    {dis && <p className="text-xs text-slate-700" role="note">{!dis.ai_enabled ? "No AI key is set, so only rule-based checks run." : tier === "restricted" ? "Restricted content is never sent to an AI provider. Only rule-based checks run." : `Your text is sent to ${dis.provider} after emails, phone numbers, card numbers, IDs and keys are replaced with placeholders. Names and addresses are not detected, so mark such content Restricted.`}</p>}
    <div onDragOver={e => e.preventDefault()} onDrop={e => { e.preventDefault(); up(e.dataTransfer.files[0]); }} className="border-2 border-dashed rounded-xl p-4 text-sm text-slate-700">Drop a .txt, .md, .docx or .pdf (max 5 MB), or <input type="file" accept=".txt,.md,.docx,.pdf" onChange={e => up(e.target.files?.[0])} /></div>
    <textarea className="w-full border rounded-xl p-2" rows={5} aria-label="Content to scan" placeholder="Paste content, e.g. Brand Guard is the #1 cheap tool." value={text} onChange={e => { setText(e.target.value); setPv(undefined); }} />
    {tier !== "restricted" && <div className="space-y-1"><button type="button" className="text-sm text-indigo-600 disabled:opacity-40" disabled={!text} onClick={() => run0(async () => setPv(await api("/privacy-preview", "POST", { text })))}>Preview what will be removed before AI</button>
      {pv && <div className="border rounded-xl p-2 text-xs bg-slate-50 space-y-1" role="status"><p><b>{pv.total ? `${pv.total} item(s) would be replaced: ${Object.entries(pv.counts).map(([k, v]) => `${k} ${v}`).join(", ")}` : "No personal data patterns found."}</b></p><p className="whitespace-pre-wrap">{pv.redacted}</p></div>}</div>}
    <button className={btn} disabled={busy || !text || !t} onClick={() => run(() => api("/scan", "POST", { title: t, text, audience: aud, message: msg, cta, tier }))}>{busy ? "Scanning…" : "Scan content"}</button>
    {err && <p className="text-red-600 text-sm" role="alert">{err}</p>}
    {s && <Findings s={s} onFix={(txt, accepted) => run(() => api(`/submissions/${s.id}/revise`, "POST", { text: txt, accepted }))} onContest={(i, kind, reason) => run(() => api(`/submissions/${s.id}/contest`, "POST", { index: i, kind, reason }))} />}
    {s && s.findings.every((x: any) => x.contest && x.contest.status !== "denied") && <button className={btn} onClick={() => run(() => api(`/submissions/${s.id}/submit`, "POST"))}>Submit for review</button>}</div>;
}
function Review({ role }: { role: string }) {
  const [l, setL] = useState<any[]>([]); const [err, setErr] = useState(""); const load = () => api("/submissions").then(setL); useEffect(() => { load(); }, []);
  const d = async (id: string, decision: string) => { try { await api(`/submissions/${id}/decide`, "POST", { decision }); load(); } catch (e) { setErr((e as Error).message); } };
  return <div className="space-y-3">{err && <p className="text-red-600 text-sm">{err}</p>}{!l.length && <p className="text-sm text-slate-700">No submissions yet. Scan some content first.</p>}
    {l.map(s => <div key={s.id} className={card + " flex justify-between items-center"}><div><b>{s.title}</b> <TierChip t={s.tier} /><p className="text-xs"><Chip s={s.status} /> {s.risk}</p>{role === "manager" && <select className="border rounded-lg p-1 text-xs mt-1" aria-label={`Confidentiality tier for ${s.title}`} value={s.tier || "internal"} onChange={async e => { try { await api(`/submissions/${s.id}/tier`, "POST", { tier: e.target.value }); load(); } catch (x) { setErr((x as Error).message); } }}>{TIERS.map(t => <option key={t} value={t}>{t}</option>)}</select>}{s.findings.filter((x: any) => x.contest).map((x: any, j: number) => <p key={j} className="text-xs text-amber-800">{x.contest.kind === "waiver" ? "Waiver" : "Dispute"} on “{x.original}” ({x.contest.status}): {x.contest.reason}</p>)}{role === "approver" && s.status === "Pending Review" && s.findings.some((x: any) => x.contest) && <p className="text-xs text-slate-700">Approving grants these waivers and upholds these disputes.</p>}</div>
      {role === "approver" && s.status === "Pending Review" && <div className="flex gap-2"><button className={btn} onClick={() => d(s.id, "approve")}>Approve</button><button className="text-sm text-amber-700" onClick={() => d(s.id, "changes")}>Request changes</button><button className="text-sm text-red-600" onClick={() => d(s.id, "reject")}>Reject</button></div>}</div>)}</div>;
}

function Cross() {
  const [l, setL] = useState<any[]>([]); const [sel, setSel] = useState<string[]>([]); const [r, setR] = useState<any>(); const [err, setErr] = useState("");
  useEffect(() => { api("/submissions").then(setL); }, []);
  const run = async () => { try { setErr(""); setR(await api("/cross-check", "POST", { ids: sel })); } catch (e) { setErr((e as Error).message); } };
  return <div className="space-y-3"><div className={card}><p className="text-sm mb-2">Pick two or more submissions from the same campaign.</p>
    {!l.length && <p className="text-sm text-slate-700">No submissions yet.</p>}
    {l.map(s => <label key={s.id} className="flex gap-2 text-sm"><input type="checkbox" checked={sel.includes(s.id)} onChange={e => setSel(e.target.checked ? [...sel, s.id] : sel.filter(i => i !== s.id))} />{s.title} ({s.channel})</label>)}
    <button className={btn + " mt-3"} disabled={sel.length < 2} onClick={run}>Compare</button>{err && <p className="text-red-600 text-sm">{err}</p>}</div>
    {r && (!r.findings.length ? <p className="text-sm">No inconsistencies found by the demo rules.</p> : r.findings.map((f: any, i: number) => <div key={i} className={card + " text-sm space-y-1"}><b>{f.kind}</b>
      {Object.entries(f.values).map(([id, v]) => <p key={id}>{l.find(x => x.id === id)?.title}: {(v as string[]).join(", ") || "none"}</p>)}
      <p className="text-slate-800">Approved reference: {f.reference}</p><p>{f.action}</p></div>))}</div>;
}
function Intel({ role }: { role: string }) {
  const [d, setD] = useState<any>(); const [src, setSrc] = useState<Record<string, string>>({}); const [err, setErr] = useState("");
  const load = () => api("/intelligence").then(setD).catch(e => setErr(e.message)); useEffect(() => { load(); }, []);
  const act = async (id: string, action: string) => { try { await api("/intelligence/" + id, "POST", { action, source: src[id] || "" }); load(); } catch (e) { setErr((e as Error).message); } };
  if (role === "creator") return <p className="text-sm">Managers and approvers only.</p>;
  const max = Math.max(1, ...Object.values((d?.violation_counts || {}) as Record<string, number>));
  return <div className="space-y-3">{err && <p className="text-red-600 text-sm">{err}</p>}
    <div className={card}><b className="text-sm">Violations per rule (this session)</b>{Object.entries(d?.violation_counts || {}).map(([k, v]) => <div key={k} className="flex items-center gap-2 text-xs"><span className="w-10">{k}</span><div className="h-3 bg-indigo-500 rounded" style={{ width: `${(Number(v) / max) * 100}%` }} />{String(v)}</div>)}</div>
    {d?.recommendations.map((r: any) => <div key={r.guideline} className={card + " text-sm space-y-2"}><p>{r.proposal} <i>({r.status})</i></p><p className="text-xs">Example submissions: {r.examples.join(", ")}</p>
      {role === "manager" && r.status === "pending" && <><textarea className="w-full border rounded-xl p-2" rows={2} defaultValue={r.source} onChange={e => setSrc({ ...src, [r.guideline]: e.target.value })} aria-label="Edit proposed guideline text" />
        <button className={btn} onClick={() => act(r.guideline, "accept")}>Publish revision</button> <button className="text-red-600" onClick={() => act(r.guideline, "reject")}>Reject</button></>}</div>)}
    {d && !d.recommendations.length && <p className="text-sm text-slate-700">No rule has repeated violations yet.</p>}</div>;
}
function Team({ role }: { role: string }) {
  const [d, setD] = useState<any>(); const [em, setEm] = useState(""); const [ro, setRo] = useState("creator"); const [msg, setMsg] = useState("");
  const load = () => api("/team").then(setD).catch(() => {}); useEffect(() => { load(); }, []);
  if (role !== "manager") return <p className="text-sm">Managers only.</p>;
  return <div className="space-y-3"><div className={card + " flex flex-wrap gap-2"}><input className="border rounded-xl p-2 text-sm" aria-label="Email" placeholder="email" value={em} onChange={e => setEm(e.target.value)} />
    <select className="border rounded-xl p-2 text-sm" aria-label="Role" value={ro} onChange={e => setRo(e.target.value)}>{["creator", "manager", "approver"].map(r => <option key={r}>{r}</option>)}</select>
    <button className={btn} onClick={async () => { try { const r = await api("/team/invite", "POST", { email: em, role: ro }); setMsg(`Created. Temporary password: ${r.temp_password}`); setEm(""); load(); } catch (e) { setMsg((e as Error).message); } }}>Invite</button>{msg && <p className="text-sm w-full">{msg}</p>}</div>
    <div className={card + " text-sm"}>{d?.users.map((u: any) => <p key={u.email}>{u.email} — {u.role}</p>)}<p className="font-medium mt-3">Activity</p>{d?.activity.map((a: any, i: number) => <p key={i} className="text-xs">{a.join(" · ")}</p>)}</div></div>;
}

function Visual({ role }: { role: string }) {
  const [file, setFile] = useState<File>(); const [alt, setAlt] = useState(""); const [r, setR] = useState<any>(); const [err, setErr] = useState(""); const [busy, setBusy] = useState(false);
  const [tier, setTier] = useState("internal"); const [b, setB] = useState<any>(); const [cols, setCols] = useState(""); const [logo, setLogo] = useState<File>(); const [msg, setMsg] = useState("");
  const load = () => api("/brand-assets").then(x => { setB(x); setCols(x.colors.join(", ")); }); useEffect(() => { load(); }, []);
  const audit = async () => { if (!file) return; setBusy(true); setErr(""); const fd = new FormData(); fd.append("file", file); fd.append("alt", alt); fd.append("tier", tier); try { setR(await upl("/visual-audit", fd)); } catch (e) { setErr((e as Error).message); } setBusy(false); };
  const save = async () => { const fd = new FormData(); fd.append("colors", cols); if (logo) fd.append("logo", logo); try { await upl("/brand-assets", fd); setMsg("Saved."); load(); } catch (e) { setMsg((e as Error).message); } };
  return <div className="space-y-3">
    {role === "manager" && <div className={card + " space-y-2 text-sm"}><b>Approved visual assets</b><input className="w-full border rounded-xl p-2" value={cols} onChange={e => setCols(e.target.value)} aria-label="Brand colours" placeholder="#4F46E5, #14B8A6" />
      <p>Reference logo (PNG/JPG): {b?.has_logo ? "uploaded" : "none"} <input type="file" accept=".png,.jpg,.jpeg" onChange={e => setLogo(e.target.files?.[0])} /></p><button className={btn} onClick={save}>Save assets</button> {msg}</div>}
    <div className={card + " space-y-2"}><input type="file" accept=".png,.jpg,.jpeg,.webp" onChange={e => setFile(e.target.files?.[0])} aria-label="Image to audit" />
      {file && <img src={URL.createObjectURL(file)} alt={alt || "Uploaded image preview"} className="max-h-64 rounded-xl border" />}
      <input className="w-full border rounded-xl p-2 text-sm" aria-label="Alt text for this image" placeholder="Alt text for this image" value={alt} onChange={e => setAlt(e.target.value)} />
      <TierPick v={tier} on={setTier} /><p className="text-xs text-slate-700">Images are sent to the AI exactly as uploaded and cannot have personal data removed. Mark an image Restricted to keep it off AI.</p>
      <button className={btn} disabled={!file || busy} onClick={audit}>{busy ? "Auditing…" : "Run audit"}</button>{err && <p className="text-red-600 text-sm" role="alert">{err}</p>}</div>
    {r && <div className={card + " text-sm space-y-2"}><p>Brand colour match: about {Math.round(r.colour_match * 100)}% of sampled pixels (approximate). Reference colours: {r.brand_colours.join(", ")}</p>
      <p>Logo: {r.logo.checked ? `best match score ${r.logo.score}, ${r.logo.found ? "likely present" : "not detected"}. ` : ""}{r.logo.note}</p>
      {r.ai_used ? <div className="border rounded-xl p-3 space-y-1"><b>Text read from the image (AI vision)</b><p className="whitespace-pre-wrap">{r.extracted_text || "No text found."}</p>{r.text_findings.map((x: any, i: number) => <p key={i}><b>{x.title}</b> <span className={`text-xs px-2 rounded ${sev[x.severity]}`}>{x.severity}</span>{x.verification === "UNVERIFIED" && <b className="text-xs text-red-700"> UNVERIFIED</b>} “{x.original}” · {x.evidence}{x.citation && <span className="text-xs text-slate-700"> · cites {x.citation.label}</span>}</p>)}{!r.text_findings.length && r.extracted_text && <p>No rule matches in the image text.</p>}{r.observations.map((o: string, i: number) => <p key={i} className="text-xs">AI observation (unverified): {o}</p>)}</div> : <p className="text-xs">{r.ai_blocked || "Reading text inside images needs an AI key on the backend (not set), so only the basic checks ran."}</p>}
      {!r.findings.length && <p>No issues found by these checks.</p>}{r.findings.map((f: any, i: number) => <div key={i} className="border rounded-xl p-3"><b>{f.title}</b> <span className={`text-xs px-2 rounded ${sev[f.severity]}`}>{f.severity}</span> <i className="text-xs">{f.category}</i><p>{f.detail}</p></div>)}
      <p className="text-xs text-slate-700">{r.limits}</p></div>}</div>;
}
