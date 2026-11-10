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
