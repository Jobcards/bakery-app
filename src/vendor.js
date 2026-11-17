// Bundled into www/vendor.js: the Android bridges (share sheet, back button).
import { SimplePool } from "nostr-tools/pool";
import { finalizeEvent, verifyEvent, generateSecretKey, getPublicKey } from "nostr-tools/pure";
import * as nip44 from "nostr-tools/nip44";
import { bytesToHex, hexToBytes } from "@noble/hashes/utils.js";
import { sha256 } from "@noble/hashes/sha2.js";
import { Capacitor } from "@capacitor/core";

// Phone-to-phone sync: encrypted records through Nostr relays (same library the Proformance app uses).
window.NT = { SimplePool, finalizeEvent, verifyEvent, generateSecretKey, getPublicKey, nip44, bytesToHex, hexToBytes, sha256 };
import { Filesystem, Directory } from "@capacitor/filesystem";
import { Share } from "@capacitor/share";
import { App } from "@capacitor/app";

const toBase64 = (blob) => new Promise((res, rej) => {
  const r = new FileReader();
  r.onload = () => res(String(r.result).split(",")[1]);
  r.onerror = () => rej(r.error);
  r.readAsDataURL(blob);
});

window.Native = {
  isNative: () => Capacitor.isNativePlatform(),
  async sharePdf(name, blob) {
    const file = await Filesystem.writeFile({ path: name, data: await toBase64(blob), directory: Directory.Cache });
    await Share.share({ title: name, files: [file.uri], dialogTitle: "Send report" });
  },
  async shareText(text) {
    await Share.share({ text, dialogTitle: "Send job card" });
  },
};

if (Capacitor.isNativePlatform()) {
  App.addListener("backButton", () => {
    if (!(window.onBack && window.onBack())) App.exitApp();
  });
}

/* ---------- automatic updates ----------
   When the app opens it checks the public update channel. New screens and features (the web part of the app)
   download in the background and switch over by themselves. A version that needs a new APK shows a prompt,
   because Android always asks the person to tap Install.
   Safety: a downloaded version only becomes the start-up version after it has opened properly once.
   If it doesn't, the app goes back to the last good version. Installing an APK always resets to the APK's own version. */
import { WebView } from "@capacitor/core";
// The app lives under the "jobcards" GitHub organisation; the old address is kept as a fallback during the move.
const UPDATE_URLS = ["https://raw.githubusercontent.com/jobcards/bakery-app/updates/", "https://raw.githubusercontent.com/freddieschallies/bakery-app/updates/"];
let UPDATE_URL = UPDATE_URLS[0];
const lsGet = (k) => { try { return localStorage.getItem(k); } catch (_) { return null; } };
const lsSet = (k, v) => { try { if (v == null || v === "") localStorage.removeItem(k); else localStorage.setItem(k, v); } catch (_) {} };
const bufToB64 = (buf) => { const b = new Uint8Array(buf); let s = ""; for (let i = 0; i < b.length; i += 0x8000) s += String.fromCharCode.apply(null, b.subarray(i, i + 0x8000)); return btoa(s); };
const thisBuild = () => String(window.APP_BUILD || 0);
let busy = false;

async function fetchWithTimeout(url, ms) {
  const c = new AbortController(); const t = setTimeout(() => c.abort(), ms);
  try { return await fetch(url, { cache: "no-store", signal: c.signal }); } finally { clearTimeout(t); }
}

// Which version of the app this is: the Macadams one (com.bakerytech.jobcards) or the general Job Cards one (…general).
// The web files are the same for both; only the installed APK differs. In a browser it counts as the general one.
window.APP_FLAVOR = "general";
if (Capacitor.isNativePlatform()) App.getInfo().then((i) => {
  window.APP_FLAVOR = /\.general$/.test(i.id) ? "general" : "macadams";
  window.onFlavor && window.onFlavor(window.APP_FLAVOR);
}).catch(() => {});

window.Updater = {
  build: () => +thisBuild(),
  async nativeBuild() { try { return +(await App.getInfo()).build || 0; } catch (_) { return 0; } },
  async versionText() {
    const n = await this.nativeBuild(), w = thisBuild();
    return n && String(n) !== w ? `1.0.${w} (app 1.0.${n})` : `1.0.${w}`;
  },
  /* returns "web" | "apk" | "current" | "offline" | "error" | "notnative" */
  async check() {
    if (!Capacitor.isNativePlatform()) return "notnative";
    if (busy) return "busy"; busy = true;
    try {
      let u;
      for (const base of UPDATE_URLS) {
        try { const r = await fetchWithTimeout(base + "update.json?t=" + Date.now(), 15000); if (!r.ok) continue; u = await r.json(); UPDATE_URL = base; break; }
        catch (_) {}
      }
      if (!u) return "offline";
      const native = await this.nativeBuild(), web = +u.web || 0;
      if (native && native < (+u.minNative || 0)) { window.onUpdate && window.onUpdate({ type: "apk", version: u.version, url: window.APP_FLAVOR === "general" ? (u.apkGeneral || u.apk) : u.apk }); return "apk"; }
      if (web <= +thisBuild() || String(web) === lsGet("upd.bad")) return "current";
      const pending = JSON.parse(lsGet("upd.pending") || "null");
      if (pending && pending.build === web) { window.onUpdate && window.onUpdate({ type: "web", build: web }); return "web"; }
      const dir = "www-" + web;
      for (const f of u.files || []) {
        const r = await fetchWithTimeout(UPDATE_URL + "web/" + f + "?b=" + web, 60000);
        if (!r.ok) throw new Error("download failed: " + f);
        await Filesystem.writeFile({ path: dir + "/" + f, data: bufToB64(await r.arrayBuffer()), directory: Directory.Data, recursive: true });
      }
      const { uri } = await Filesystem.getUri({ path: dir, directory: Directory.Data });
      lsSet("upd.pending", JSON.stringify({ build: web, path: decodeURIComponent(uri.replace(/^file:\/\//, "")) }));
      window.onUpdate && window.onUpdate({ type: "web", build: web });
      return "web";
    } catch (e) { console.warn("update", e); return "error"; }
    finally { busy = false; }
  },
  hasPending() { const p = JSON.parse(lsGet("upd.pending") || "null"); return !!(p && p.build > +thisBuild()); },
  /* switches to the downloaded version (the app reloads) */
  async apply() {
    const p = JSON.parse(lsGet("upd.pending") || "null"); if (!p || !(p.build > +thisBuild())) return false;
    lsSet("upd.pending", ""); lsSet("upd.try", String(p.build));
    await WebView.setServerBasePath({ path: p.path });
    return true;
  },
  /* called once the app has opened properly: keep this version for next time and tidy up old downloads */
  async markGood() {
    if (!Capacitor.isNativePlatform()) return;
    if (lsGet("upd.try") === thisBuild()) { await WebView.persistServerBasePath(); lsSet("upd.try", ""); lsSet("upd.good", thisBuild()); }
    try {
      const keep = "www-" + thisBuild(), p = JSON.parse(lsGet("upd.pending") || "null"), keep2 = p ? "www-" + p.build : "";
      const { files } = await Filesystem.readdir({ path: "", directory: Directory.Data });
      for (const f of files) { const n = f.name || f; if (/^www-\d+$/.test(n) && n !== keep && n !== keep2) await Filesystem.rmdir({ path: n, directory: Directory.Data, recursive: true }).catch(() => {}); }
    } catch (_) {}
  },
};

if (Capacitor.isNativePlatform()) {
  // a version that was switched to but never opened properly is skipped from now on
  const tried = lsGet("upd.try");
  if (tried && tried !== thisBuild()) { lsSet("upd.bad", tried); lsSet("upd.try", ""); }
}
