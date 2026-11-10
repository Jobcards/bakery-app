# Bakery Tech Job Cards

Phone web app for Macadams International's bakery service technicians.

- Job cards with site, customer, equipment, fault, work done, parts and photos
- One-tap PDF reports (WhatsApp / email) and daily/weekly summaries by technician
- Per-technician van stock that deducts when parts are used on a job card
- Macadams logo plus brand logos on reports (uploaded in Settings)

## Files

- `index.html` — the whole app (HTML, CSS and JavaScript in one file)

## Note on hosting

The app currently runs as a Claude artifact and uses its built-in services for the
shared database (`db`), photo/logo uploads (`assets`), user names (`user`) and
PDF saving (`downloads`). Opened outside Claude, those parts won't work until they
are swapped for a standalone backend (e.g. Firebase or Supabase).
