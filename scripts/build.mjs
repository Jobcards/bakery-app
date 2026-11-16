// Builds the app into www/ (what goes inside the APK). Run: npm run build
import { build } from "esbuild";
import { cpSync, mkdirSync, rmSync, writeFileSync } from "node:fs";

rmSync("www", { recursive: true, force: true });
mkdirSync("www/lib", { recursive: true });
cpSync("src/index.html", "www/index.html");
// the build number lets the app tell whether a downloaded update is newer than what it is running
writeFileSync("www/build.js", `window.APP_BUILD=${parseInt(process.env.BUILD_NUMBER || "0", 10) || 0};\n`);
cpSync("src/macadams-logo.png", "www/macadams-logo.png");
cpSync("node_modules/jspdf/dist/jspdf.umd.min.js", "www/lib/jspdf.umd.min.js");
cpSync("node_modules/jspdf-autotable/dist/jspdf.plugin.autotable.min.js", "www/lib/jspdf.plugin.autotable.min.js");
await build({ entryPoints: ["src/vendor.js"], bundle: true, minify: true, format: "iife", target: "es2020", outfile: "www/vendor.js", logLevel: "warning" });
await build({ entryPoints: ["src/fonts.css"], bundle: true, minify: true, outfile: "www/fonts.css", loader: { ".woff2": "file", ".woff": "file" }, assetNames: "fonts/[name]", logLevel: "warning" });
// the server serves the same app as the admin website
rmSync("server/public", { recursive: true, force: true });
cpSync("www", "server/public", { recursive: true });
console.log("Built www/ and server/public/");
