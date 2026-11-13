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
async def newcard(pg,cust,photo=True,parts=0,km=""):
    await pg.click("#tabList"); await pg.click("#fab"); await pg.fill("#f_customer",cust); await pg.fill("#f_site","Empangeni"); await pg.fill("#f_equipment","Rack oven"); await pg.fill("#f_serial","RM-4471"); await pg.fill("#f_work","Serviced")
    await pg.fill("#f_timeIn","08:00"); await pg.fill("#f_timeOut","10:30")
    if km: await pg.fill("#f_km",km)
    if parts:
        await pg.click("[data-tog='jobType:breakdown']"); await pg.click("[data-tog='dept:bakery']"); await pg.click("[data-tog='dept:deli']")
        await pg.fill("#f_custRef","PO 55120"); await pg.fill("#f_model","Rotomax 68"); await pg.fill("#f_fault","Oven not reaching temperature, burner cutting out after 10 minutes."); await pg.fill("#f_work","Cleaned flame sensor and replaced the door seal. Tested for 45 minutes at 220 C, holding temperature.")
        await pg.fill("#f_parts","1 Door seal 600mm"); await pg.fill("#f_partsNeeded","1 Steam solenoid valve\n2 Oven light globes")
        await pg.fill("#f_signName","Zanele Mthembu"); cv=pg.locator("#signPad"); await cv.scroll_into_view_if_needed(); bx=await cv.bounding_box()
        await pg.mouse.move(bx["x"]+30,bx["y"]+90); await pg.mouse.down()
        for i in range(1,40): await pg.mouse.move(bx["x"]+30+i*7,bx["y"]+90+(30 if i%2 else -30)*(1-i/60))
        await pg.mouse.up()
    if parts:
        await pg.click("#pickOpen"); await pg.wait_for_selector("#picker .part")
        for _ in range(parts): await pg.click("#picker .part:has-text('Element') button[data-d='1']")
        await shot(pg,"p1_picker.png"); await pg.click("#pickDone")
    if photo:
        await pg.set_input_files("#galIn",os.path.join(HERE,"photo.jpg")); await pg.wait_for_function("!document.querySelector('.ph .up')",timeout=15000)
    await pg.click("#saveBottom"); await pg.wait_for_selector("#pdfOne"); await pg.click("[data-go=list]")
async def addco(pg,name,details,aname,auser,apw,inv):
    await pg.click("#addCo"); await pg.fill("#c_name",name); await pg.fill("#c_details",details); await pg.fill("#c_adminName",aname); await pg.fill("#c_adminUser",auser); await pg.fill("#c_adminPass",apw)
    if inv: await pg.check("#c_inv")
    if inv: await pg.set_input_files("#c_logo",os.path.join(HERE,"logo.png")); await pg.wait_for_selector("#c_logoBox img")
    await shot(pg,"c1_addcompany.png"); await pg.click("#coSave"); await pg.wait_for_selector(f".member:has-text('{name}')",timeout=30000)
async def synced(pg): await pg.wait_for_function("document.querySelector('#syncState').textContent==='Synced'",timeout=30000)
async def cards(pg,n): await pg.wait_for_function(f"document.querySelectorAll('.card').length==={n}",timeout=40000)
async def page(b):
    ctx=await b.new_context(viewport={"width":400,"height":860},accept_downloads=True); pg=await ctx.new_page()
    pg.on("pageerror",lambda e:errors.append(str(e))); await pg.goto(URL); return ctx,pg
async def main():
  async with async_playwright() as p:
    b=await p.chromium.launch(executable_path=os.environ.get("CHROME","/usr/bin/google-chrome"),args=["--no-sandbox"])
    dctx,dev=await page(b)
    await dev.wait_for_selector("#l_user"); ok("sign-in screen has no setup button or server box",await dev.locator("#l_server").count()==0 and await dev.locator("#goSetup").count()==0)
    await login(dev,"Admin","9999"); await dev.wait_for_selector("text=Wrong username or password",timeout=20000); ok("wrong developer password refused",True)
    await login(dev,"Admin","1234"); await dev.wait_for_selector("#addCo",timeout=20000); ok("developer login opens the Companies screen",await dev.eval_on_selector(".tabbar","e=>e.hidden"))
    await addco(dev,"Zululand Service Providers","12 Bullion Boulevard, Alton, Richards Bay 3900\nTel 035 555 0100\nservice@zsp.example\nVAT no. 4123456789","Fred Schallies","zspadmin","zsp-1234",True)
    await addco(dev,"Coastal Bakery Services","5 Harbour Road, Durban 4001\nTel 031 555 0200","Nomsa Zulu","cbsadmin","cbs-1234",False)
    ok("developer added two companies with their own admin logins",await dev.locator(".member").count()==2); await dev.wait_for_timeout(2500); await shot(dev,"c2_companies.png")
    actx,admin=await page(b)
    await login(admin,"zspadmin","zsp-1234"); await admin.wait_for_selector("#tabTeam:not([hidden])",timeout=30000); await admin.wait_for_function("document.querySelector('#coName').textContent==='Zululand Service Providers'",timeout=20000)
    ok("company admin signs in and sees their own company name",True)
    ok("invoicing is on for this company (set by the developer)",await admin.eval_on_selector("#tabInv","e=>!e.hidden"))
    await admin.wait_for_function("!document.querySelector('#coBadge').hidden&&document.querySelector('#coLogo2').getAttribute('src').startsWith('data:')",timeout=30000); ok("the company's own logo shows next to the Macadams one",await admin.eval_on_selector('#coLogo','e=>e.getAttribute("src")')=='macadams-logo.png')
    await admin.click("#tabTeam")
    for n,u,pw in [("Sipho Dlamini","sipho","oven-1234"),("Thabo Nkosi","thabo","mixer-4567")]:
        await admin.click("#addTech"); await admin.fill("#t_name",n); await admin.fill("#t_user",u); await admin.fill("#t_pass",pw); await admin.click("#teamSave"); await admin.wait_for_selector(f".member:has-text('{n}')",timeout=20000)
    ok("admin created two technician logins",await admin.locator(".member").count()==2); await synced(admin)

    sctx,sipho=await page(b)
    await login(sipho,"sipho","wrong-pass"); await sipho.wait_for_selector("text=Wrong username or password",timeout=20000); ok("wrong password refused",True)
    await login(sipho,"sipho","oven-1234"); await sipho.wait_for_selector("text=No job cards yet",timeout=30000); ok("Sipho signed in on his own phone with just username and password",await sipho.eval_on_selector("#tabTeam","e=>e.hidden"))
    await sipho.click("#tabVan"); await sipho.click("#addPart"); await sipho.fill("#p_partNo","EL-1"); await sipho.fill("#p_desc","Element"); await sipho.fill("#p_qty","5"); await sipho.fill("#p_price","450"); await sipho.click("#partForm button[type=submit]"); await sipho.wait_for_selector(".part:has-text('Element')")
    await newcard(sipho,"Bakery A",parts=2,km="40"); await newcard(sipho,"Bakery B",photo=False); await synced(sipho)
    await sipho.click(".card:has-text('Bakery A')"); await sipho.wait_for_selector("text=Breakdown"); ok("job type and department show on the job card",await sipho.locator("text=Bakery, Deli").count()==1)
    async with sipho.expect_download() as dl: await sipho.click("#pdfOne")
    d=await dl.value
    if SHOTS: await d.save_as(os.path.join(SHOTS,"job.pdf"))
    await sipho.click("[data-go=list]")
    await sipho.click("#tabVan"); await sipho.wait_for_timeout(300); ok("picked parts came off the van stock (5 - 2 = 3)",await sipho.inner_text(".part:has-text('Element') .qty output")=="3"); await sipho.click("#tabList")
    await sipho.click(".card:has-text('Bakery A')"); await sipho.click("#editOne"); await sipho.click("#pickOpen"); await sipho.click("#picker .part:has-text('Element') button[data-d='-1']"); await sipho.click("#pickDone"); await sipho.click("#saveTop"); await sipho.wait_for_selector("#pdfOne"); await sipho.click("[data-go=list]")
    await sipho.click("#tabVan"); await sipho.wait_for_timeout(300); ok("taking one back off the job card returns it to the van (4)",await sipho.inner_text(".part:has-text('Element') .qty output")=="4"); await sipho.click("#tabList"); await synced(sipho)
    await admin.click("#tabList"); await cards(admin,2); ok("Sipho's job cards reached the admin's phone",True)
    await admin.wait_for_selector(".thumbs-mini img[src]",timeout=30000); ok("the photo came across too",True); await shot(admin,"r2_admin.png")
    await admin.click("#tabCust"); await admin.wait_for_selector(".card.cust:has-text('Bakery A')"); ok("customer and machine profile reached the admin",True)
    # invoicing
    await admin.click("#settingsBtn"); await admin.fill("#v_labourRate","650"); await admin.fill("#v_kmRate","8.5"); await admin.fill("#v_callout","350"); await admin.fill("#v_vatNo","4123456789"); await admin.fill("#v_bank","FNB, Zululand Service Providers\nAccount 62 000 000 000, branch 250655"); await shot(admin,"i0_settings.png"); await admin.click("#setForm button[type=submit]")
    await admin.click("#tabInv"); await admin.wait_for_selector("[data-newinv]"); ok("completed job cards show as ready to invoice",await admin.locator("[data-newinv]").count()==2)
    await admin.click(".mach:has-text('Bakery A') [data-newinv]"); await admin.wait_for_selector("#invLines .line"); await admin.wait_for_timeout(300); await shot(admin,"i1_form.png")
    tot=await admin.inner_text("#invTot .grand b"); ok("invoice drafted from the job card: call-out 350 + 2.5 h x 650 + 40 km x 8.50 + 1 x 450 = 2 765.00, plus 15% VAT = 3 179.75",tot=="R 3 179.75",tot)
    await admin.click("#invSave"); await admin.wait_for_selector("#invPdf"); await shot(admin,"i2_invoice.png"); ok("invoice saved with the first number",await admin.locator("text=INV-0001").count()>0)
    async with admin.expect_download() as dl: await admin.click("#invPdf")
    d=await dl.value
    if SHOTS: await d.save_as(os.path.join(SHOTS,"invoice.pdf"))
    ok("invoice PDF made",os.path.getsize(await d.path())>15000,d.suggested_filename)
    await admin.click("#invPaid"); await admin.wait_for_selector(".jobhead .pill:has-text('Paid')"); ok("invoice marked paid",True)
    await admin.click("[data-go=inv]"); await admin.wait_for_timeout(2700); await shot(admin,"i3_list.png"); ok("the invoiced job card left the ready list",await admin.locator("[data-newinv]").count()==1)
    await sipho.wait_for_timeout(1500); ok("technicians don't get the Invoices tab",await sipho.eval_on_selector("#tabInv","e=>e.hidden"))
    # a second company sees nothing of the first
    cctx,cbs=await page(b); await login(cbs,"cbsadmin","cbs-1234"); await cbs.wait_for_selector("#tabTeam:not([hidden])",timeout=30000); await cbs.wait_for_function("document.querySelector('#coName').textContent==='Coastal Bakery Services'",timeout=20000); await synced(cbs); await cbs.wait_for_timeout(1500)
    ok("the other company's admin sees none of the first company's job cards",await cbs.locator(".card").count()==0)
    await cbs.click("#tabCust"); await cbs.wait_for_timeout(500); ok("nor its customers",await cbs.locator(".card.cust").count()==0)
    ok("invoicing is off for the company that didn't want it",await cbs.eval_on_selector("#tabInv","e=>e.hidden")); await cctx.close()

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
    # developer gives a company admin a new password, and switches the other company off
    await dev.click(".member:has-text('Zululand') [data-editco]"); await dev.fill("#c_adminPass","zsp-9999"); await dev.click("#coSave"); await dev.wait_for_selector("text=Company saved",timeout=30000)
    await admin.wait_for_selector("#l_user",timeout=40000); await login(admin,"zspadmin","zsp-1234"); await admin.wait_for_selector("text=Wrong username or password",timeout=20000)
    await login(admin,"zspadmin","zsp-9999"); await cards(admin,3); ok("developer's new admin password works; the old one doesn't",True)
    # the admin signs in on a second phone and gets everything
    a2ctx,admin2=await page(b); await login(admin2,"zspadmin","zsp-9999"); await cards(admin2,3); ok("admin signing in on another phone gets all the job cards",True)
    await b.close()
relay=subprocess.Popen(["node",os.path.join(HERE,"relay.js"),"7447"],stdout=subprocess.DEVNULL)
web=subprocess.Popen([sys.executable,"-m","http.server","8793","-d",os.path.join(ROOT,"www")],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL); time.sleep(1.2)
try: asyncio.run(main())
finally: relay.terminate(); web.terminate()
print("PAGE ERRORS:",errors or "none"); print(f"{sum(results)}/{len(results)} passed"); sys.exit(0 if all(results) and not errors else 1)
