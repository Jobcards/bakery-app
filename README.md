# Bakery Tech Job Cards

Android app for Macadams International's bakery service technicians.

- Job cards with site, customer, equipment, fault, work done, parts and photos
- PDF reports shared straight to WhatsApp or email, plus daily/weekly summaries
- Per-technician van stock that deducts when parts are used on a job card
- Company logo and brand logos on reports (Settings)
- Works with no signal: everything is saved on the phone and syncs to the company server when it can reach it
- One admin sees all job cards and hands out a login to each technician

## Getting the APK

Every push to `main` builds the APK on GitHub (Actions → **Build APK**).
Download `BakeryJobCards.apk` from the latest **Release** and open it on the phone.
New versions install over the old one and keep the data.

## Phone-to-phone sync (no server)

This is the default, and works the same way as the Proformance app's club sync. All data stays on each phone.
Phones of the same company pass changes to each other over Wi-Fi or mobile data, end-to-end encrypted,
through free public Nostr relays (nos.lol, relay.damus.io, relay.primal.net, offchain.pub). The relays keep
the latest copy of each record so a new phone can catch up, but they cannot read it.

- **Admin:** sign in with the base login, username `Admin`, password `1234`. This is a test setup: the login is built into the app, so anyone with the app and this login can read the data. Replace it before a real rollout.
- **Technicians tab (admin):** add each technician with a username and password (4 or more characters).
- **Technician's phone:** sign in with that username and password. Nothing else to set up.
- A technician's phone keeps only their own job cards and van stock; the admin's phone gets everything. The customer list is shared.
- Every phone of the company holds the same company key, so the technician/admin split is kept by the app, not by encryption. Fine for testing; use the company server for the real rollout.

To use a company server instead, tap **Use a company server instead** on the sign-in screen.

## Server, admin and technician logins

The app syncs straight to the company's own server. No outside service is used.

- `server/server.js` is the whole server: job cards, logins, photos and the admin website. It needs only Node.js (`node server/server.js`, port 8080, data in `server/data/`).
- `npm run build` also copies the app into `server/public/`, so the server serves it as the admin website.
- **First open:** choose **Set up the admin account**. This can only be done once.
- **Technicians tab (admin only):** add each technician with a username and password, set a new password, or switch a login off.
- **Technicians** see only their own job cards and van stock. Everything is saved on the phone first and sent to the server when the phone can reach it.
- **Admin** sees every technician's job cards, van stock and reports.

See `server/README.txt` for the step-by-step test on a Windows PC.

## Project layout

- `src/index.html` - the app (screens, job cards, van stock, PDFs)
- `src/vendor.js` - Android bridges (share sheet, back button)
- `server/` - the server program and its Windows start file
- `scripts/build.mjs` - builds `www/` for the APK (`npm run build`)
- `.github/workflows/android.yml` - builds the APK on GitHub
- `tests/test_relay.py` - end-to-end test of phone-to-phone sync against a local test relay
- `tests/test_server.py` - end-to-end test: real server, an admin browser and two technician phones (needs Playwright and Chrome)
- `ci/debug.keystore` - signing key, kept fixed so updates install over the old app

To try it in a browser: `npm install && npm run build`, then serve the `www` folder.
