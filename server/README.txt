MACADAMS JOB CARDS - TEST SERVER
================================

This folder is the whole server: it keeps the job cards, the logins and the
photos, and it is also the admin website. Nothing is sent anywhere else.

FIRST TIME
1. Install Node.js (LTS) from https://nodejs.org  - just click Next through the installer.
2. Double-click "Start Server.bat".
   If Windows Firewall asks, tick "Private networks" and click "Allow access".
3. The black window shows two kinds of address:
      On this PC:       http://localhost:8080
      Phones on Wi-Fi:  http://192.168.x.x:8080   (your numbers will differ)
4. On the PC, open http://localhost:8080 in Chrome or Edge.
   Click "Set up the admin account" and choose your name, username and password.
5. Open the "Technicians" tab and add a technician (name, username, password).

ON THE PHONE (same Wi-Fi as the PC)
6. Open Chrome on the phone and type the "Phones on Wi-Fi" address.
7. Sign in with the technician's username and password.
8. Make a job card. Within a few seconds it shows on the PC under "Job cards".
   (On the PC: Settings > Sync now fetches straight away.)

TRY THIS
- Switch the phone's Wi-Fi off, make a job card, switch Wi-Fi back on.
  The card stays on the phone and goes to the PC when the connection is back.
- In "Technicians", give a tech a new password or switch a login off.

GOOD TO KNOW
- Keep the black window open. Closing it stops the server; phones keep working
  and sync again when it is started.
- All data is in the "data" folder here. Copy that folder to back it up.
  Delete it to start again from nothing.
- The PC's Wi-Fi address can change. If the phone can't connect, check the
  address in the black window again.
- This test version runs on your own network only. Reaching it over mobile
  data needs it on a server with a public address - that is the later step.
