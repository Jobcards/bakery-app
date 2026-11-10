// Builds the app into www/ (what goes inside the APK). Run: npm run build
import { build } from "esbuild";
import { cpSync, mkdirSync, rmSync } from "node:fs";

rmSync("www", { recursive: true, force: true });
mkdirSync("www/lib", { recursive: true });
cpSync("src/index.html", "www/index.html");
cpSync("src/firebase-config.js", "www/firebase-config.js");
cpSync("src/macadams-logo.png", "www/macadams-logo.png");
cpSync("node_modules/jspdf/dist/jspdf.umd.min.js", "www/lib/jspdf.umd.min.js");
cpSync("node_modules/jspdf-autotable/dist/jspdf.plugin.autotable.min.js", "www/lib/jspdf.plugin.autotable.min.js");
await build({ entryPoints: ["src/vendor.js"], bundle: true, minify: true, format: "iife", target: "es2020", outfile: "www/vendor.js", logLevel: "warning" });
await build({ entryPoints: ["src/fonts.css"], bundle: true, minify: true, outfile: "www/fonts.css", loader: { ".woff2": "file", ".woff": "file" }, assetNames: "fonts/[name]", logLevel: "warning" });
console.log("Built www/");
