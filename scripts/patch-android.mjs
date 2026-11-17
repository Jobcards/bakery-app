// Run after `npx cap add android`: camera permission and a version number that goes up every build,
// so a new APK installs over the old one and keeps the job cards on the phone.
import { readFileSync, writeFileSync, cpSync } from "node:fs";
// Icon and splash screen: Macadams for the Macadams version, the clipboard for the general Job Cards version
const FLAVOR = process.env.FLAVOR === "general" ? "general" : "macadams";
cpSync(FLAVOR === "general" ? "resources/android-general" : "resources/android", "android/app/src/main/res", { recursive: true });
const man = "android/app/src/main/AndroidManifest.xml";
let m = readFileSync(man, "utf8");
if (!m.includes("android.permission.CAMERA")) {
  m = m.replace("</manifest>", '    <uses-permission android:name="android.permission.CAMERA" />\n</manifest>');
  writeFileSync(man, m);
}
const gradle = "android/app/build.gradle";
let g = readFileSync(gradle, "utf8");
const code = parseInt(process.env.BUILD_NUMBER || "1", 10);
g = g.replace(/versionCode \d+/, `versionCode ${code}`).replace(/versionName "[^"]*"/, `versionName "1.0.${code}"`);
writeFileSync(gradle, g);
console.log(`Android patched (${FLAVOR}): versionCode ${code}`);
