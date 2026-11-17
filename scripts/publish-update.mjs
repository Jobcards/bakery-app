// Publishes the built app (www/) to the public "updates" branch, where phones check for updates.
// update.json says which web build is newest and the lowest APK build it runs on (minNative).
// minNative only moves when something inside the APK itself changed (plugins, Android settings, icons, signing).
import { createHash } from "node:crypto";
import { execSync } from "node:child_process";
import { readFileSync, readdirSync, statSync, cpSync, mkdirSync, rmSync, writeFileSync, existsSync } from "node:fs";
import { join, relative } from "node:path";

const BUILD = parseInt(process.env.BUILD_NUMBER, 10);
const REPO = process.env.GITHUB_REPOSITORY;
const TOKEN = process.env.GITHUB_TOKEN;
if (!BUILD || !REPO || !TOKEN) throw new Error("BUILD_NUMBER, GITHUB_REPOSITORY and GITHUB_TOKEN are needed");

const walk = (d) => readdirSync(d).flatMap((f) => { const p = join(d, f); return statSync(p).isDirectory() ? walk(p) : [p]; });

// what goes into the APK itself
const pkg = JSON.parse(readFileSync("package.json", "utf8"));
const caps = Object.entries({ ...pkg.dependencies, ...pkg.devDependencies }).filter(([k]) => k.startsWith("@capacitor/")).sort();
const h = createHash("sha256");
h.update(JSON.stringify(caps));
for (const f of ["capacitor.config.json", "scripts/patch-android.mjs", ".github/workflows/android.yml", ...walk("resources").sort()])
  if (existsSync(f)) { h.update(f); h.update(readFileSync(f)); }
const nativeHash = h.digest("hex").slice(0, 16);

const remote = process.env.UPDATE_REMOTE || `https://x-access-token:${TOKEN}@github.com/${REPO}.git`; // UPDATE_REMOTE: for testing
let prev = null;
try { prev = JSON.parse(execSync(`git fetch -q --depth 1 ${remote} updates && git show FETCH_HEAD:update.json`, { encoding: "utf8", stdio: ["ignore", "pipe", "ignore"] })); } catch (_) {}
const minNative = prev && prev.nativeHash === nativeHash ? prev.minNative : BUILD;

const out = "/tmp/update-channel";
rmSync(out, { recursive: true, force: true }); mkdirSync(out);
cpSync("www", join(out, "web"), { recursive: true });
const files = walk(join(out, "web")).map((f) => relative(join(out, "web"), f).split("\\").join("/")).sort();
writeFileSync(join(out, "update.json"), JSON.stringify({
  web: BUILD, version: `1.0.${BUILD}`, minNative, nativeHash,
  apk: `https://github.com/${REPO}/releases/download/build-${BUILD}/BakeryJobCards.apk`, // Macadams version (name kept so older phones still find it)
  apkGeneral: `https://github.com/${REPO}/releases/download/build-${BUILD}/JobCards.apk`, // general Job Cards version
  files, published: new Date().toISOString(),
}, null, 2));
writeFileSync(join(out, "README.md"), "Update channel for the Bakery Job Cards app. Written by the Build APK workflow; don't edit by hand.\n");

const sh = (c) => execSync(c, { cwd: out, stdio: "inherit" });
sh("git init -q -b updates");
sh('git -c user.name="update-bot" -c user.email="update-bot@users.noreply.github.com" add -A');
sh(`git -c user.name="update-bot" -c user.email="update-bot@users.noreply.github.com" commit -q -m "Update ${BUILD}"`);
sh(`git push -q --force ${remote} updates`);
console.log(`Published web build ${BUILD} (APK needed from build ${minNative}${minNative === BUILD ? ", new APK" : ""})`);
