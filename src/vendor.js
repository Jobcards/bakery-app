// Bundled into www/vendor.js: the Android bridges (share sheet, back button).
import { Capacitor } from "@capacitor/core";
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
