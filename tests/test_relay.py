# End-to-end test of phone-to-phone sync (no server): a local test relay, an admin phone and two technician phones.
# Run from the repo root after `npm run build`:  python3 tests/test_relay.py
import asyncio, subprocess, sys, time, os
from playwright.async_api import async_playwright
HERE=os.path.dirname(os.path.abspath(__file__)); ROOT=os.path.dirname(HERE); SHOTS=os.environ.get("SHOTS","")
URL="http://localhost:8793/index.html?relay=ws://localhost:7447"
errors=[]; results=[]
def ok(n,cond,extra=""):
    results.append(bool(cond)); print(("PASS" if cond else "FAIL"),n,extra)
async def shot(pg,name):
    if SHOTS: await pg.screenshot(path=os.path.join(SHOTS,name))
async def login(pg,u,p):
    await pg.wait_for_selector("#l_user"); await pg.fill("#l_user",u); await pg.fill("#l_pass",p); await pg.click("#loginBtn")
async def newcard(pg,cust,photo=True):
    await pg.click("#tabList"); await pg.click("#fab"); await pg.fill("#f_customer",cust); await pg.fill("#f_site","Empangeni"); await pg.fill("#f_equipment","Rack oven"); await pg.fill("#f_serial","RM-4471"); await pg.fill("#f_work","Serviced")
    if photo:
        await pg.set_input_files("#galIn",os.path.join(HERE,"photo.jpg")); await pg.wait_for_function("!document.querySelector('.ph .up')",timeout=15000)
    await pg.click("#saveBottom"); await pg.wait_for_selector("#pdfOne"); await pg.click("[data-go=list]")
async def synced(pg): await pg.wait_for_function("document.querySelector('#syncState').textContent==='Synced'",timeout=30000)
async def cards(pg,n): await pg.wait_for_function(f"document.querySelectorAll('.card').length==={n}",timeout=40000)
async def page(b):
    ctx=await b.new_context(viewport={"width":400,"height":860},accept_downloads=True); pg=await ctx.new_page()
    pg.on("pageerror",lambda e:errors.append(str(e))); await pg.goto(URL); return ctx,pg
async def main():
  async with async_playwright() as p:
    b=await p.chromium.launch(executable_path=os.environ.get("CHROME","/usr/bin/google-chrome"),args=["--no-sandbox"])
    actx,admin=await page(b)
    await admin.wait_for_selector("#goSetup"); await shot(admin,"r1_signin.png"); ok("sign-in screen needs no server address",await admin.locator("#l_server").count()==0)
    await admin.click("#goSetup"); await admin.fill("#a_name","Fred Schallies"); await admin.fill("#a_user","fredadmin"); await admin.fill("#a_pass","short"); await admin.click("#setupBtn"); await admin.wait_for_selector("text=8 or more"); ok("short password refused (8 or more without a server)",True)
    await admin.fill("#a_pass","secret-admin1"); await admin.click("#setupBtn")
    await admin.wait_for_selector("#tabTeam:not([hidden])",timeout=20000); ok("admin started a new company",True)
    await admin.click("#tabTeam")
    for n,u,pw in [("Sipho Dlamini","sipho","oven-1234"),("Thabo Nkosi","thabo","mixer-4567")]:
        await admin.click("#addTech"); await admin.fill("#t_name",n); await admin.fill("#t_user",u); await admin.fill("#t_pass",pw); await admin.click("#teamSave"); await admin.wait_for_selector(f".member:has-text('{n}')",timeout=20000)
    ok("admin created two technician logins",await admin.locator(".member").count()==2); await synced(admin)

    sctx,sipho=await page(b)
    await login(sipho,"sipho","wrong-pass"); await sipho.wait_for_selector("text=Wrong username or password",timeout=20000); ok("wrong password refused",True)
    await login(sipho,"sipho","oven-1234"); await sipho.wait_for_selector("text=No job cards yet",timeout=30000); ok("Sipho signed in on his own phone with just username and password",await sipho.eval_on_selector("#tabTeam","e=>e.hidden"))
    await newcard(sipho,"Bakery A"); await newcard(sipho,"Bakery B",photo=False); await synced(sipho)
    await admin.click("#tabList"); await cards(admin,2); ok("Sipho's job cards reached the admin's phone",True)
    await admin.wait_for_selector(".thumbs-mini img[src]",timeout=30000); ok("the photo came across too",True); await shot(admin,"r2_admin.png")
    await admin.click("#tabCust"); await admin.wait_for_selector(".card.cust:has-text('Bakery A')"); ok("customer and machine profile reached the admin",True)

    tctx,thabo=await page(b); await login(thabo,"thabo","mixer-4567"); await thabo.wait_for_selector("#fab",timeout=30000); await synced(thabo); await thabo.wait_for_timeout(1500)
    ok("Thabo's phone doesn't show Sipho's job cards",await thabo.locator(".card").count()==0)
    await thabo.click("#tabCust"); await thabo.wait_for_selector(".card.cust:has-text('Bakery A')",timeout=20000); ok("Thabo does get the shared customer list",True)
    await tctx.set_offline(True); await newcard(thabo,"Bakery C (no signal)",photo=False)
    await thabo.wait_for_function("document.querySelector('#syncState').textContent.startsWith('Offline')",timeout=40000); ok("offline: saved on the phone and waiting",True,await thabo.inner_text("#syncState"))
    await tctx.set_offline(False); await thabo.click("#settingsBtn"); await thabo.click("#syncBtn"); await synced(thabo); await thabo.click("[data-go=list]")
    await admin.click("#tabList"); await cards(admin,3); ok("back online: the card reached the admin",True)
    # admin edits a technician's card; the technician's phone gets the change
    await admin.click(".card:has-text('Bakery B')"); await admin.click("#editOne"); await admin.fill("#f_notes","Checked by admin"); await admin.click("#saveTop"); await admin.wait_for_selector("#pdfOne"); await synced(admin)
    await sipho.click(".card:has-text('Bakery B')"); await sipho.wait_for_selector("text=Checked by admin",timeout=30000); ok("admin's edit reached the technician's phone",True); await sipho.click("[data-go=list]")
    await admin.click("[data-go=list]"); await admin.click("#tabVan"); await admin.wait_for_selector("#vanTechSel"); ok("admin can open each technician's van",len(await admin.eval_on_selector_all("#vanTechSel option","o=>o.map(x=>x.textContent)"))==3)
    # new password and switch off
    await admin.click("#tabTeam"); await admin.click(".member:has-text('Sipho') [data-resetpw]"); await admin.fill("#t_pass","brand-new-99"); await admin.click("#teamSave"); await admin.wait_for_selector("text=New password set",timeout=20000)
    await sipho.wait_for_selector("#l_user",timeout=30000); ok("new password: Sipho's phone asks him to sign in again",True)
    await login(sipho,"sipho","oven-1234"); await sipho.wait_for_selector("text=Wrong username or password",timeout=20000); ok("old password refused",True)
    await login(sipho,"sipho","brand-new-99"); await cards(sipho,2); ok("new password works and his cards are still there",True)
    await admin.click(".member:has-text('Thabo') [data-toggle]"); await admin.wait_for_selector(".member.off",timeout=20000)
    await thabo.wait_for_selector("#l_user",timeout=30000); await login(thabo,"thabo","mixer-4567"); await thabo.wait_for_selector("text=switched off",timeout=20000); ok("switched-off login is signed out and can't get back in",True)
    # the admin signs in on a second phone and gets everything
    a2ctx,admin2=await page(b); await login(admin2,"fredadmin","secret-admin1"); await cards(admin2,3); ok("admin signing in on another phone gets all the job cards",True)
    await b.close()
relay=subprocess.Popen(["node",os.path.join(HERE,"relay.js"),"7447"],stdout=subprocess.DEVNULL)
web=subprocess.Popen([sys.executable,"-m","http.server","8793","-d",os.path.join(ROOT,"www")],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL); time.sleep(1.2)
try: asyncio.run(main())
finally: relay.terminate(); web.terminate()
print("PAGE ERRORS:",errors or "none"); print(f"{sum(results)}/{len(results)} passed"); sys.exit(0 if all(results) and not errors else 1)
