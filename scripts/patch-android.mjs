// Run after `npx cap add android`: camera permission and a version number that goes up every build,
// so a new APK installs over the old one and keeps the job cards on the phone.
import { readFileSync, writeFileSync } from "node:fs";
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
console.log(`Android patched: versionCode ${code}`);
