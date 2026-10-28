import { useEffect, useState } from "react";
import { LayoutDashboard, BookOpen, ScanSearch, CheckCircle2, LogOut, Menu, GitCompare, Lightbulb, Users, Image as ImageIcon, ShieldCheck, Network, Settings as Cog } from "lucide-react";
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
      <select className="w-full border rounded-xl p-2" value={email} onChange={e => setEmail(e.target.value)}>
        {["creator", "manager", "approver"].map(r => <option key={r}>{r}@demo.com</option>)}</select>
      <input className="w-full border rounded-xl p-2" type="password" value={pw} onChange={e => setPw(e.target.value)} aria-label="Password" />
      {err && <p className="text-red-600 text-sm" role="alert">{err}</p>}
      <button className={btn + " w-full"} onClick={login}>Sign in</button>
      <p className="text-xs text-slate-700">Demo accounts, password demo1234.</p></div></div>);
  const nav = [["Overview", LayoutDashboard], ["Brand Guidelines", BookOpen], ["Content Scanner", ScanSearch], ["Cross-Channel Check", GitCompare], ["Visual Brand Audit", ImageIcon], ["Review & Approvals", CheckCircle2], ["Brand Intelligence", Lightbulb], ["Knowledge Graph", Network], ["Team Management", Users], ["Settings", Cog]] as const;
  const hidden: Record<string, string[]> = { creator: ["Brand Intelligence", "Team Management"], manager: [], approver: ["Content Scanner", "Team Management"] };
  const items = nav.filter(([n]) => !(hidden[role] ?? []).includes(n));
  return (<div className="min-h-screen md:flex md:p-4 md:gap-4">
    <aside className={`${open ? "block" : "hidden"} md:flex md:flex-col w-full md:w-64 shrink-0 bg-white/90 md:rounded-3xl shadow-xl shadow-indigo-500/10 p-4 space-y-1 md:sticky md:top-4 md:h-[calc(100vh-2rem)] overflow-auto`}>
      <div className="flex items-center gap-3 mb-4"><div className="w-10 h-10 rounded-xl bg-gradient-to-br from-indigo-600 to-cyan-400 grid place-items-center text-white"><ShieldCheck size={20} /></div><b className="text-lg">BrandGuard <span className="text-[10px] bg-indigo-100 text-indigo-700 rounded px-1.5">AI</span></b></div>
      {items.map(([n, I]) => <button key={n} onClick={() => { setPage(n); setOpen(false); }} className={`flex gap-3 items-center w-full text-left px-3 py-2.5 rounded-xl text-sm font-medium transition ${page === n ? "bg-gradient-to-r from-indigo-600 to-cyan-500 text-white shadow-md shadow-indigo-500/30" : "text-slate-800 hover:bg-indigo-50 hover:translate-x-0.5"}`}><I size={18} />{n}</button>)}
      <div className="md:mt-auto pt-4"><button onClick={() => { sessionStorage.clear(); token = ""; setRole(""); setPage("Overview"); }} className="flex gap-2 items-center px-3 py-2 text-sm text-slate-700 hover:text-slate-800"><LogOut size={16} />Sign out ({role})</button></div>
    </aside>
    <main className="fade flex-1 min-w-0 p-4 md:p-6 space-y-4"><div className="flex items-center gap-3"><button className="md:hidden" onClick={() => setOpen(!open)} aria-label="Menu"><Menu /></button><div><p className="text-xs text-slate-700">Governance › {page}</p><h2 className="text-2xl font-bold">{page}</h2></div></div>
      {page === "Overview" && <Overview go={p => setPage((hidden[role] ?? []).includes(p) ? "Review & Approvals" : p)} />}{page === "Brand Guidelines" && <Guidelines role={role} />}
      {page === "Content Scanner" && <Scanner role={role} />}{page === "Review & Approvals" && <Review role={role} />}{page === "Cross-Channel Check" && <Cross />}{page === "Visual Brand Audit" && <Visual role={role} />}{page === "Brand Intelligence" && <Intel role={role} />}{page === "Team Management" && <Team role={role} />}{page === "Knowledge Graph" && <Graph />}{page === "Settings" && <SettingsPage role={role} />}</main></div>);
}
const col: Record<string, string> = { Approved: "#10B981", "Pending Review": "#6366F1", "Changes Required": "#F59E0B", Rejected: "#94A3B8", Draft: "#22D3EE" };
const chipCls: Record<string, string> = { Approved: "bg-emerald-100 text-emerald-700", "Pending Review": "bg-indigo-100 text-indigo-700", "Changes Required": "bg-amber-100 text-amber-700", Rejected: "bg-slate-200 text-slate-800", Draft: "bg-cyan-100 text-cyan-700" };
const Chip = ({ s }: { s: string }) => <span className={`text-xs font-medium px-2.5 py-0.5 rounded-full ${chipCls[s] || ""}`}>{s}</span>;
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
function Graph() {
  const [g, setG] = useState<any[]>([]); const [subs, setSubs] = useState<any[]>([]);
  useEffect(() => { api("/guidelines").then(setG); api("/submissions").then(setSubs); }, []);
  return <div className="space-y-3"><div className={card}><b>Brand → Guidelines → Content</b><p className="text-sm text-slate-700">If a rule changes, these submissions may be affected.</p></div>
    {g.map(x => { const a = subs.filter(s => s.findings.some((f: any) => f.guideline === x.id)); return <div key={x.id} className={card}><b>{x.category}</b> <span className="text-xs px-2 rounded bg-indigo-100 text-indigo-700">{x.id}</span><p className="text-sm">{x.pattern} {x.fix && `→ ${x.fix}`}</p><p className="text-xs text-slate-700">Linked content: {a.length ? a.map(s => s.title).join(", ") : "none yet"}</p></div>; })}</div>;
}
function SettingsPage({ role }: { role: string }) {
  const [s, setS] = useState<any>(); useEffect(() => { api("/ai-status").then(setS).catch(() => {}); }, []);
  return <div className="space-y-3"><div className={card}><b>Profile</b><p className="text-sm">Role: {role}</p></div><div className={card}><b>AI provider</b><p className="text-sm">{s?.llm_configured ? "AI model connected (key held on the backend)." : "No API key set: scans use the labelled demo rules."}</p></div><div className={card}><b>Storage</b><p className="text-sm">{s?.mongo ? "MongoDB connected." : "In-memory only; data resets on restart."}</p></div></div>;
}
function Guidelines({ role }: { role: string }) {
  const [g, setG] = useState<any[]>([]); const [f, setF] = useState({ category: "Terminology", priority: "medium", kind: "term", pattern: "", fix: "", source: "" });
  const [err, setErr] = useState(""); const load = () => api("/guidelines").then(setG); useEffect(() => { load(); }, []);
  const can = role !== "creator";
  return <div className="space-y-3">{can ? <div className={card + " grid gap-2 md:grid-cols-3"}>
    {(["pattern", "fix", "source"] as const).map(k => <input key={k} className="border rounded-xl p-2 text-sm" placeholder={k} value={f[k]} onChange={e => setF({ ...f, [k]: e.target.value })} />)}
    <button className={btn} onClick={async () => { try { await api("/guidelines", "POST", f); setF({ ...f, pattern: "", fix: "", source: "" }); load(); } catch (e) { setErr((e as Error).message); } }}>Add rule</button>
    {err && <p className="text-red-600 text-sm">{err}</p>}</div> : <p className="text-sm text-slate-700">Creators can view guidelines; managers edit them.</p>}
    {g.map(x => <div key={x.id} className={card + " flex justify-between gap-3"}><div><b>{x.category}</b> <span className={`text-xs px-2 rounded ${sev[x.priority] || ""}`}>{x.priority}</span>
      <p className="text-sm">{x.pattern} {x.fix && `→ ${x.fix}`}</p><p className="text-xs text-slate-700">{x.source || "No source document"}</p></div>
      {can && <button className="text-sm text-red-600" onClick={async () => { await api("/guidelines/" + x.id, "DELETE"); load(); }}>Delete</button>}</div>)}</div>;
}
function Findings({ s, onFix }: { s: any; onFix: (t: string) => void }) {
  const [text, setText] = useState(s.text); useEffect(() => setText(s.text), [s.text]);
  return <div className="space-y-2"><p className="text-sm">Status: <Chip s={s.status} /> · Risk: {s.risk} · Engine: {s.mode === "llm" ? "AI model (validated against your guidelines)" : "demo rules (not real AI)"}{s.needs_human && " · human approval required"}</p>
    {s.findings.map((x: any, i: number) => <div key={i} className="border rounded-xl p-3 text-sm space-y-1"><b>{x.title}</b> <span className={`text-xs px-2 rounded ${sev[x.severity]}`}>{x.severity}</span> <i className="text-xs">{x.status}</i>
      <p>Original: “{x.original}”</p><p className="text-slate-800">Evidence: {x.evidence}</p>{x.confidence && <p className="text-xs">Confidence: {x.confidence}</p>}{x.explanation && <p className="text-xs">{x.explanation}</p>}
      {x.suggestion && <button className="text-indigo-600" onClick={() => onFix(s.text.replace(new RegExp(x.original.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"), "gi"), x.suggestion))}>Accept suggestion</button>}</div>)}
    <textarea className="w-full border rounded-xl p-2 text-sm" rows={4} value={text} onChange={e => setText(e.target.value)} aria-label="Edit content" />
    <button className={btn} onClick={() => onFix(text)}>Rescan edited text</button></div>;
}
function Scanner({ role }: { role: string }) {
  const [t, setT] = useState(""); const [text, setText] = useState(""); const [s, setS] = useState<any>(); const [err, setErr] = useState(""); const [busy, setBusy] = useState(false);
  const run = async (fn: () => Promise<any>) => { setBusy(true); setErr(""); try { setS(await fn()); } catch (e) { setErr((e as Error).message); } setBusy(false); };
  const up = async (f?: File) => { if (!f) return; const fd = new FormData(); fd.append("file", f); try { setErr(""); setText((await upl("/upload-text", fd)).text); } catch (e) { setErr((e as Error).message); } };
  if (role === "approver") return <p className="text-sm">Approvers review submissions under Review & Approvals.</p>;
  return <div className={card + " space-y-3"}><input className="w-full border rounded-xl p-2" placeholder="Content title" value={t} onChange={e => setT(e.target.value)} />
    <div onDragOver={e => e.preventDefault()} onDrop={e => { e.preventDefault(); up(e.dataTransfer.files[0]); }} className="border-2 border-dashed rounded-xl p-4 text-sm text-slate-700">Drop a .txt, .md, .docx or .pdf (max 5 MB), or <input type="file" accept=".txt,.md,.docx,.pdf" onChange={e => up(e.target.files?.[0])} /></div>
    <textarea className="w-full border rounded-xl p-2" rows={5} placeholder="Paste content, e.g. Brand Guard is the #1 cheap tool." value={text} onChange={e => setText(e.target.value)} />
    <button className={btn} disabled={busy || !text || !t} onClick={() => run(() => api("/scan", "POST", { title: t, text }))}>{busy ? "Scanning…" : "Scan content"}</button>
    {err && <p className="text-red-600 text-sm" role="alert">{err}</p>}
    {s && <Findings s={s} onFix={txt => run(() => api(`/submissions/${s.id}/revise`, "POST", { text: txt }))} />}
    {s && !s.findings.length && <button className={btn} onClick={() => run(() => api(`/submissions/${s.id}/submit`, "POST"))}>Submit for review</button>}</div>;
}
function Review({ role }: { role: string }) {
  const [l, setL] = useState<any[]>([]); const [err, setErr] = useState(""); const load = () => api("/submissions").then(setL); useEffect(() => { load(); }, []);
  const d = async (id: string, decision: string) => { try { await api(`/submissions/${id}/decide`, "POST", { decision }); load(); } catch (e) { setErr((e as Error).message); } };
  return <div className="space-y-3">{err && <p className="text-red-600 text-sm">{err}</p>}{!l.length && <p className="text-sm text-slate-700">No submissions yet. Scan some content first.</p>}
    {l.map(s => <div key={s.id} className={card + " flex justify-between items-center"}><div><b>{s.title}</b><p className="text-xs"><Chip s={s.status} /> {s.risk}</p></div>
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
  return <div className="space-y-3"><div className={card + " flex flex-wrap gap-2"}><input className="border rounded-xl p-2 text-sm" placeholder="email" value={em} onChange={e => setEm(e.target.value)} />
    <select className="border rounded-xl p-2 text-sm" value={ro} onChange={e => setRo(e.target.value)}>{["creator", "manager", "approver"].map(r => <option key={r}>{r}</option>)}</select>
    <button className={btn} onClick={async () => { try { const r = await api("/team/invite", "POST", { email: em, role: ro }); setMsg(`Created. Temporary password: ${r.temp_password}`); setEm(""); load(); } catch (e) { setMsg((e as Error).message); } }}>Invite</button>{msg && <p className="text-sm w-full">{msg}</p>}</div>
    <div className={card + " text-sm"}>{d?.users.map((u: any) => <p key={u.email}>{u.email} — {u.role}</p>)}<p className="font-medium mt-3">Activity</p>{d?.activity.map((a: any, i: number) => <p key={i} className="text-xs">{a.join(" · ")}</p>)}</div></div>;
}

function Visual({ role }: { role: string }) {
  const [file, setFile] = useState<File>(); const [alt, setAlt] = useState(""); const [r, setR] = useState<any>(); const [err, setErr] = useState(""); const [busy, setBusy] = useState(false);
  const [b, setB] = useState<any>(); const [cols, setCols] = useState(""); const [logo, setLogo] = useState<File>(); const [msg, setMsg] = useState("");
  const load = () => api("/brand-assets").then(x => { setB(x); setCols(x.colors.join(", ")); }); useEffect(() => { load(); }, []);
  const audit = async () => { if (!file) return; setBusy(true); setErr(""); const fd = new FormData(); fd.append("file", file); fd.append("alt", alt); try { setR(await upl("/visual-audit", fd)); } catch (e) { setErr((e as Error).message); } setBusy(false); };
  const save = async () => { const fd = new FormData(); fd.append("colors", cols); if (logo) fd.append("logo", logo); try { await upl("/brand-assets", fd); setMsg("Saved."); load(); } catch (e) { setMsg((e as Error).message); } };
  return <div className="space-y-3">
    {role === "manager" && <div className={card + " space-y-2 text-sm"}><b>Approved visual assets</b><input className="w-full border rounded-xl p-2" value={cols} onChange={e => setCols(e.target.value)} aria-label="Brand colours" placeholder="#4F46E5, #14B8A6" />
      <p>Reference logo (PNG/JPG): {b?.has_logo ? "uploaded" : "none"} <input type="file" accept=".png,.jpg,.jpeg" onChange={e => setLogo(e.target.files?.[0])} /></p><button className={btn} onClick={save}>Save assets</button> {msg}</div>}
    <div className={card + " space-y-2"}><input type="file" accept=".png,.jpg,.jpeg,.webp" onChange={e => setFile(e.target.files?.[0])} aria-label="Image to audit" />
      {file && <img src={URL.createObjectURL(file)} alt={alt || "Uploaded image preview"} className="max-h-64 rounded-xl border" />}
      <input className="w-full border rounded-xl p-2 text-sm" placeholder="Alt text for this image" value={alt} onChange={e => setAlt(e.target.value)} />
      <button className={btn} disabled={!file || busy} onClick={audit}>{busy ? "Auditing…" : "Run audit"}</button>{err && <p className="text-red-600 text-sm" role="alert">{err}</p>}</div>
    {r && <div className={card + " text-sm space-y-2"}><p>Brand colour match: about {Math.round(r.colour_match * 100)}% of sampled pixels (approximate). Reference colours: {r.brand_colours.join(", ")}</p>
      <p>Logo: {r.logo.checked ? `best match score ${r.logo.score}, ${r.logo.found ? "likely present" : "not detected"}. ` : ""}{r.logo.note}</p>
      {r.ai_used ? <div className="border rounded-xl p-3 space-y-1"><b>Text read from the image (AI vision)</b><p className="whitespace-pre-wrap">{r.extracted_text || "No text found."}</p>{r.text_findings.map((x: any, i: number) => <p key={i}><b>{x.title}</b> <span className={`text-xs px-2 rounded ${sev[x.severity]}`}>{x.severity}</span> “{x.original}” · {x.evidence}</p>)}{!r.text_findings.length && r.extracted_text && <p>No rule matches in the image text.</p>}{r.observations.map((o: string, i: number) => <p key={i} className="text-xs">AI observation (unverified): {o}</p>)}</div> : <p className="text-xs">Reading text inside images needs an AI key on the backend (not set), so only the basic checks ran.</p>}
      {!r.findings.length && <p>No issues found by these checks.</p>}{r.findings.map((f: any, i: number) => <div key={i} className="border rounded-xl p-3"><b>{f.title}</b> <span className={`text-xs px-2 rounded ${sev[f.severity]}`}>{f.severity}</span> <i className="text-xs">{f.category}</i><p>{f.detail}</p></div>)}
      <p className="text-xs text-slate-700">{r.limits}</p></div>}</div>;
}