// A minimal Nostr relay for tests only (the real app uses public relays). Run: node tests/relay.js [port]
const { WebSocketServer } = require("ws");
const port = +process.argv[2] || 7447, events = new Map(), subs = new Map();
const key = e => (e.kind >= 30000 && e.kind < 40000) ? `${e.pubkey}:${e.kind}:${(e.tags.find(t => t[0] === "d") || [])[1] || ""}` : e.id;
const match = (f, e) => (!f.ids || f.ids.includes(e.id)) && (!f.kinds || f.kinds.includes(e.kind)) && (!f.authors || f.authors.includes(e.pubkey)) && (!f.since || e.created_at >= f.since) && (!f.until || e.created_at <= f.until) &&
  Object.entries(f).every(([k, v]) => k[0] !== "#" || e.tags.some(t => t[0] === k.slice(1) && v.includes(t[1])));
new WebSocketServer({ port }).on("connection", ws => {
  subs.set(ws, new Map());
  ws.on("close", () => subs.delete(ws));
  ws.on("message", raw => {
    let m; try { m = JSON.parse(raw); } catch (_) { return; }
    if (m[0] === "EVENT") {
      const e = m[1], k = key(e), old = events.get(k);
      if (!old || e.created_at > old.created_at || (e.created_at === old.created_at && e.id < old.id)) {
        events.set(k, e);
        for (const [sock, ss] of subs) for (const [id, fs] of ss) if (fs.some(f => match(f, e))) sock.send(JSON.stringify(["EVENT", id, e]));
      }
      ws.send(JSON.stringify(["OK", e.id, true, ""]));
    } else if (m[0] === "REQ") {
      const fs = m.slice(2); subs.get(ws).set(m[1], fs);
      for (const e of events.values()) if (fs.some(f => match(f, e))) ws.send(JSON.stringify(["EVENT", m[1], e]));
      ws.send(JSON.stringify(["EOSE", m[1]]));
    } else if (m[0] === "CLOSE") subs.get(ws).delete(m[1]);
  });
});
console.log("test relay on", port);
