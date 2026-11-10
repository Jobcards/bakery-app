# Bakery Tech Job Cards

Android app for Macadams International's bakery service technicians.

- Job cards with site, customer, equipment, fault, work done, parts and photos
- PDF reports shared straight to WhatsApp or email, plus daily/weekly summaries
- Per-technician van stock that deducts when parts are used on a job card
- Company logo and brand logos on reports (Settings)
- Works with no signal: everything is saved on the phone and syncs when online

## Getting the APK

Every push to `main` builds the APK on GitHub (Actions → **Build APK**).
Download `BakeryJobCards.apk` from the latest **Release** and open it on the phone.
New versions install over the old one and keep the data.

## Admin, technician logins and sync (Firebase)

Until this is done, each phone keeps its own job cards and there is no sign-in.

1. Create a free project at https://console.firebase.google.com
2. **Build → Firestore Database → Create database** (production mode, region `africa-south1` if offered)
3. **Firestore → Rules**: paste in `firestore.rules` from this repo and publish
4. **Build → Authentication → Get started → Email/Password → Enable**
5. **Project settings → Your apps → Web (</>)**: register an app and copy the `firebaseConfig`
6. Paste it into `src/firebase-config.js` as `window.FIREBASE_CONFIG = {...}` and push

Then, in the app:

- **First open (admin's phone):** tap **Set up the admin account** and choose a name, username and password. This can only be done once.
- **Technicians tab (admin only):** add each technician with a username and password, give them a new password, or switch a login off.
- **Technicians** sign in once with signal. After that the phone remembers them and works offline. They see only their own job cards and van stock.
- **Admin** sees every technician's job cards, van stock and reports. Cards arrive when the tech's phone has signal.

Job cards already saved on a phone are handed to whoever signs in on it first.
Usernames are stored as made-up addresses ending in `@jobcards.example.com`; no email is ever sent.

## Project layout

- `src/index.html` - the app (screens, job cards, van stock, PDFs)
- `src/vendor.js` - Firebase and Android bridges (share, back button)
- `src/firebase-config.js` - team sync settings
- `scripts/build.mjs` - builds `www/` for the APK (`npm run build`)
- `.github/workflows/android.yml` - builds the APK on GitHub
- `firestore.rules` - who can see what (admin: everything, technician: their own)
- `tests/` - browser tests (`python3 tests/test_app.py www`, `python3 tests/test_auth.py www`), need Playwright and Chrome
- `ci/debug.keystore` - signing key, kept fixed so updates install over the old app

To try it in a browser: `npm install && npm run build`, then serve the `www` folder.
