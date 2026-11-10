// Macadams Job Cards server.
// One program: keeps the job cards, the logins and the photos, and serves the admin website.
// No other software or outside service is needed. Run:  node server.js
// Data is kept in the "data" folder next to this file. Back that folder up.
"use strict";
const http = require("http"), fs = require("fs"), path = require("path"), crypto = require("crypto"), os = require("os");

const PORT = +process.env.PORT || 8080;
const DATA = process.env.DATA_DIR || path.join(__dirname, "data");
const PUB = process.env.PUBLIC_DIR || path.join(__dirname, "public");
const DB_FILE = path.join(DATA, "db.json"), BLOBS = path.join(DATA, "photos");
fs.mkdirSync(BLOBS, { recursive: true });

// ---------- store ----------
let st = { seq: 0, users: [], sessions: {}, docs: {} };
if (fs.existsSync(DB_FILE)) st = { ...st, ...JSON.parse(fs.readFileSync(DB_FILE, "utf8")) };
let saveTimer = null;
function saveNow() { clearTimeout(saveTimer); saveTimer = null; const tmp = DB_FILE + ".tmp"; fs.writeFileSync(tmp, JSON.stringify(st)); fs.renameSync(tmp, DB_FILE); }
function save() { if (!saveTimer) saveTimer = setTimeout(saveNow, 250); }
for (const sig of ["SIGINT", "SIGTERM"]) process.on(sig, () => { if (saveTimer) saveNow(); process.exit(0); });

// ---------- logins ----------
const normUser = v => String(v || "").trim().toLowerCase().replace(/[^a-z0-9._-]/g, "");
const hashPw = (pw, salt) => crypto.scryptSync(String(pw), salt, 32).toString("hex");
const pub = u => ({ id: u.id, name: u.name, username: u.username, role: u.role, active: u.active !== false });
const hasAdmin = () => st.users.some(u => u.role === "admin");
function addUser(name, username, password, role) {
  const salt = crypto.randomBytes(16).toString("hex");
  const u = { id: "u" + crypto.randomBytes(8).toString("hex"), name, username, role, active: true, salt, hash: hashPw(password, salt), createdAt: Date.now() };
  st.users.push(u); save(); return u;
}
function newSession(u) { const token = crypto.randomBytes(32).toString("hex"); st.sessions[token] = { uid: u.id, at: Date.now() }; save(); return token; }
function dropSessions(uid) { for (const [t, s] of Object.entries(st.sessions)) if (s.uid === uid) delete st.sessions[t]; }
const fails = new Map(); // username -> {n, until}
function whoIs(req) {
  const m = /^Bearer (.+)$/.exec(req.headers.authorization || ""); if (!m) return { code: 401 };
  const s = st.sessions[m[1]]; if (!s) return { code: 401 };
  const u = st.users.find(x => x.id === s.uid); if (!u) return { code: 401 };
  if (u.active === false) return { code: 403 };
  return { user: u, token: m[1] };
}

// ---------- who may see and change what ----------
const SAFE_ID = /^[A-Za-z0-9_-]{1,80}$/;
function owner(p, data, old) { // the technician a record belongs to
  const a = p.split("/");
  if (a[0] === "jobcards") return (data && data.techId) || (old && old.owner) || "";
  if (a[0] === "vanstock") return a[1];
  return "";
}
function validPath(p) {
  const a = String(p).split("/");
  if (!a.every(x => SAFE_ID.test(x))) return false;
  return (a[0] === "jobcards" && a.length === 2) || (a[0] === "vanstock" && a.length === 4 && a[2] === "parts") || (a[0] === "settings" && a.length === 2) || (a[0] === "customers" && a.length === 2) || (a[0] === "blobs" && a.length === 2);
}
function mayWrite(u, p, data, old) {
  const admin = u.role === "admin", top = p.split("/")[0];
  if (admin) return true;
  if (top === "settings") return false;
  if (top === "customers") return !!data; // every technician adds to the shared customer list; only the admin removes one
  if (top === "jobcards") return (!old || old.owner === u.id) && (!data || data.techId === u.id);
  if (top === "vanstock") return p.split("/")[1] === u.id;
  return false;
}
function maySee(u, p, d) {
  if (u.role === "admin") return true;
  const top = p.split("/")[0];
  if (top === "settings" || top === "customers") return true;
  return d.owner === u.id;
}

function sync(u, body) {
  const since = +body.since || 0, sent = new Set(), extra = [];
  for (const c of Array.isArray(body.changes) ? body.changes : []) {
    const p = String(c.path || ""); if (!validPath(p)) continue; sent.add(p);
    const data = c.data && typeof c.data === "object" ? c.data : null, ts = +c.ts || Date.now();
    if (p.startsWith("blobs/")) { // photos and logos: one file each, written once
      const f = path.join(BLOBS, p.slice(6) + ".json");
      if (data && typeof data.data === "string" && data.data.length < 1500000 && (!fs.existsSync(f) || u.role === "admin")) fs.writeFileSync(f, JSON.stringify({ data: data.data, techId: u.id, createdAt: Date.now() }));
      continue;
    }
    const old = st.docs[p];
    if (!mayWrite(u, p, data, old) || (old && old.ts > ts)) { // not allowed, or the server has a newer version: send the server's copy back
      if (old && maySee(u, p, old)) extra.push({ path: p, data: old.data, ts: old.ts });
      else if (!old) extra.push({ path: p, data: null, ts });
      continue;
    }
    st.docs[p] = { data, ts, seq: ++st.seq, owner: owner(p, data, old), by: u.id };
  }
  if (sent.size) save();
  const out = [];
  for (const [p, d] of Object.entries(st.docs)) {
    if (d.seq <= since || sent.has(p) || !maySee(u, p, d)) continue;
    if (d.data === null && since === 0) continue; // a fresh phone doesn't need to hear about deleted cards
    out.push({ path: p, data: d.data, ts: d.ts, seq: d.seq });
  }
  out.sort((a, b) => a.seq - b.seq);
  const more = out.length > 500, page = more ? out.slice(0, 500) : out;
  return { changes: [...extra, ...page.map(({ seq, ...c }) => c)], cursor: more ? page[page.length - 1].seq : st.seq, more };
}

// ---------- http ----------
const TYPES = { ".html": "text/html; charset=utf-8", ".js": "text/javascript; charset=utf-8", ".css": "text/css; charset=utf-8", ".png": "image/png", ".jpg": "image/jpeg", ".svg": "image/svg+xml", ".woff2": "font/woff2", ".woff": "font/woff", ".json": "application/json", ".ico": "image/x-icon" };
const CORS = { "Access-Control-Allow-Origin": "*", "Access-Control-Allow-Headers": "Content-Type, Authorization", "Access-Control-Allow-Methods": "GET, POST, OPTIONS", "Access-Control-Max-Age": "86400" };
function send(res, code, obj) { const b = JSON.stringify(obj); res.writeHead(code, { "Content-Type": "application/json", "Cache-Control": "no-store", ...CORS }); res.end(b); }
function readBody(req) {
  return new Promise((resolve, reject) => {
    const chunks = []; let n = 0;
    req.on("data", c => { n += c.length; if (n > 12e6) { reject(Object.assign(new Error("too big"), { code: 413 })); req.destroy(); } else chunks.push(c); });
    req.on("end", () => { try { resolve(chunks.length ? JSON.parse(Buffer.concat(chunks).toString("utf8")) : {}); } catch (e) { reject(Object.assign(new Error("bad json"), { code: 400 })); } });
    req.on("error", reject);
  });
}
async function apiRoute(req, res, url) {
  const p = url.pathname, m = req.method;
  if (m === "OPTIONS") { res.writeHead(204, CORS); return res.end(); }
  if (p === "/api/status") return send(res, 200, { app: "macadams-jobcards", needSetup: !hasAdmin() });

  if (p === "/api/setup" && m === "POST") {
    const b = await readBody(req);
    if (hasAdmin()) return send(res, 409, { error: "An admin already exists. Sign in instead" });
    const name = String(b.name || "").trim(), un = normUser(b.username), pw = String(b.password || "");
    if (!name || !un || pw.length < 6) return send(res, 400, { error: "Type a name, a username and a password of 6 or more characters" });
    const u = addUser(name, un, pw, "admin"); console.log(`Admin account created: ${un}`);
    return send(res, 200, { token: newSession(u), user: pub(u) });
  }
  if (p === "/api/login" && m === "POST") {
    const b = await readBody(req), un = normUser(b.username), f = fails.get(un);
    if (f && f.until > Date.now()) return send(res, 429, { error: "Too many tries. Wait a few minutes and try again" });
    const u = st.users.find(x => x.username === un);
    if (!u || !crypto.timingSafeEqual(Buffer.from(hashPw(b.password || "", u.salt)), Buffer.from(u.hash))) {
      const n = ((f && f.n) || 0) + 1; fails.set(un, { n, until: n >= 8 ? Date.now() + 5 * 60000 : 0 });
      return send(res, 401, { error: "Wrong username or password" });
    }
    fails.delete(un);
    if (u.active === false) return send(res, 403, { error: "This login is switched off. Speak to the admin" });
    return send(res, 200, { token: newSession(u), user: pub(u) });
  }

  const who = whoIs(req);
  if (!who.user) return send(res, who.code, { error: who.code === 403 ? "This login is switched off" : "Sign in again" });
  const u = who.user;
  if (p === "/api/logout" && m === "POST") { delete st.sessions[who.token]; save(); return send(res, 200, {}); }
  if (p === "/api/me") return send(res, 200, { user: pub(u) });
  if (p === "/api/sync" && m === "POST") return send(res, 200, sync(u, await readBody(req)));
  if (p.startsWith("/api/blob/") && m === "GET") {
    const id = decodeURIComponent(p.slice(10)); if (!SAFE_ID.test(id)) return send(res, 400, { error: "Bad id" });
    const f = path.join(BLOBS, id + ".json"); if (!fs.existsSync(f)) return send(res, 404, { error: "Not found" });
    return send(res, 200, { data: JSON.parse(fs.readFileSync(f, "utf8")).data });
  }
  if (p === "/api/users" || p.startsWith("/api/users/")) {
    if (u.role !== "admin") return send(res, 403, { error: "Only the admin can manage logins" });
    if (p === "/api/users" && m === "GET") return send(res, 200, { users: st.users.map(pub) });
    const b = await readBody(req);
    if (p === "/api/users" && m === "POST") {
      const name = String(b.name || "").trim(), un = normUser(b.username), pw = String(b.password || "");
      if (!name || !un || pw.length < 6) return send(res, 400, { error: "Type a name, a username and a password of 6 or more characters" });
      if (st.users.some(x => x.username === un)) return send(res, 409, { error: "That username is taken. Choose another" });
      return send(res, 200, { user: pub(addUser(name, un, pw, "tech")) });
    }
    const t = st.users.find(x => x.id === decodeURIComponent(p.slice(11)));
    if (!t || m !== "POST") return send(res, 404, { error: "No such login" });
    if (typeof b.name === "string" && b.name.trim()) t.name = b.name.trim();
    if (typeof b.password === "string") { if (b.password.length < 6) return send(res, 400, { error: "Use a password of 6 or more characters" }); t.salt = crypto.randomBytes(16).toString("hex"); t.hash = hashPw(b.password, t.salt); dropSessions(t.id); }
    if (typeof b.active === "boolean" && t.role !== "admin") { t.active = b.active; if (!b.active) dropSessions(t.id); }
    save(); return send(res, 200, { user: pub(t) });
  }
  send(res, 404, { error: "Not found" });
}
function serveFile(res, url) {
  let rel = decodeURIComponent(url.pathname); if (rel.endsWith("/")) rel += "index.html";
  const f = path.normalize(path.join(PUB, rel));
  if (!f.startsWith(PUB) || !fs.existsSync(f) || fs.statSync(f).isDirectory()) { res.writeHead(404, { "Content-Type": "text/plain" }); return res.end("Not found"); }
  res.writeHead(200, { "Content-Type": TYPES[path.extname(f).toLowerCase()] || "application/octet-stream", "Cache-Control": "no-cache" });
  fs.createReadStream(f).pipe(res);
}
const server = http.createServer((req, res) => {
  const url = new URL(req.url, "http://x");
  if (url.pathname.startsWith("/api/")) apiRoute(req, res, url).catch(e => { if (!res.headersSent) send(res, e.code || 500, { error: e.code === 413 ? "Too much data in one go" : "Server error" }); if (!e.code) console.error(e); });
  else serveFile(res, url);
});
server.listen(PORT, "0.0.0.0", () => {
  const ips = Object.values(os.networkInterfaces()).flat().filter(i => i && i.family === "IPv4" && !i.internal).map(i => i.address);
  console.log("\nMacadams Job Cards server is running.\n");
  console.log(`  On this PC:        http://localhost:${PORT}`);
  for (const ip of ips) console.log(`  Phones on Wi-Fi:   http://${ip}:${PORT}`);
  console.log(`\n  Job cards so far: ${Object.keys(st.docs).filter(p => p.startsWith("jobcards/") && st.docs[p].data).length}   Logins: ${st.users.length}`);
  console.log(hasAdmin() ? "\nLeave this window open. Close it to stop the server.\n" : "\nNo admin yet: open the address above in a browser and choose \"Set up the admin account\".\nLeave this window open. Close it to stop the server.\n");
});
