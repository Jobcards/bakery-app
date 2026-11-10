# End-to-end test: starts the real server, then drives an admin browser and two technician "phones".
# Run from the repo root after `npm run build`:  python3 tests/test_server.py
import asyncio, subprocess, sys, time, os, shutil, tempfile, urllib.request
from playwright.async_api import async_playwright
HERE=os.path.dirname(os.path.abspath(__file__)); ROOT=os.path.dirname(HERE); PORT="8791"; URL=f"http://localhost:{PORT}/"
DATA=tempfile.mkdtemp(); SHOTS=os.environ.get("SHOTS","")
def start():
    p=subprocess.Popen(["node",os.path.join(ROOT,"server","server.js")],env={**os.environ,"PORT":PORT,"DATA_DIR":DATA},stdout=subprocess.DEVNULL)
    for _ in range(50):
        try: urllib.request.urlopen(URL+"api/status"); return p
        except Exception: time.sleep(0.1)
    raise SystemExit("server did not start")
errors=[]; results=[]
def ok(n,cond,extra=""):
    results.append(bool(cond)); print(("PASS" if cond else "FAIL"),n,extra)
async def shot(pg,name):
    if SHOTS: await pg.screenshot(path=os.path.join(SHOTS,name))
async def login(pg,u,p):
    await pg.wait_for_selector("#l_user"); await pg.fill("#l_user",u); await pg.fill("#l_pass",p); await pg.click("#loginBtn")
async def sign(pg):
    cv=pg.locator("#signPad"); await cv.scroll_into_view_if_needed(); bx=await cv.bounding_box()
    await pg.mouse.move(bx["x"]+30,bx["y"]+90); await pg.mouse.down()
    for i in range(1,40): await pg.mouse.move(bx["x"]+30+i*7,bx["y"]+90+(30 if i%2 else -30)*(1-i/60))
    await pg.mouse.up()
async def newcard(pg,cust,photo=True,full=False):
    await pg.click("#tabList"); await pg.click("#fab"); await pg.fill("#f_customer",cust); await pg.fill("#f_equipment","Rack oven"); await pg.fill("#f_work","Serviced")
    if full:
        await pg.fill("#f_site","Empangeni"); await pg.fill("#f_contact","Zanele 082 555 0101"); await pg.fill("#f_model","Rotomax 68"); await pg.fill("#f_serial","RM-4471"); await pg.fill("#f_timeIn","08:00"); await pg.fill("#f_timeOut","10:30")
        await pg.fill("#f_fault","Oven not reaching temperature.\nBurner cutting out after 10 minutes."); await pg.fill("#f_work","Cleaned flame sensor and replaced the door seal.\nTested for 45 minutes at 220 C, holding temperature."); await pg.fill("#f_notes","Recommend replacing the steam solenoid at next service.")
        await pg.click("[data-status=follow]")
        await pg.select_option("#usedPick",index=1); await pg.fill("#usedQty","1"); await pg.click("#addUsed")
        await pg.fill("#f_signName","Zanele Mthembu"); await sign(pg); await shot(pg,"6_form_sign.png")
    if photo:
        await pg.set_input_files("#galIn",os.path.join(HERE,"photo.jpg")); await pg.wait_for_function("!document.querySelector('.ph .up')",timeout=15000)
    await pg.click("#saveBottom"); await pg.wait_for_selector("#pdfOne"); await pg.click("[data-go=list]")
async def synced(pg): await pg.wait_for_function("document.querySelector('#syncState').textContent==='Synced'",timeout=15000)
async def cards(pg,n): await pg.wait_for_function(f"document.querySelectorAll('.card').length==={n}",timeout=40000)
async def page(b):
    ctx=await b.new_context(viewport={"width":400,"height":860},accept_downloads=True); pg=await ctx.new_page()
    pg.on("pageerror",lambda e:errors.append(str(e))); await pg.goto(URL); return ctx,pg
async def main():
  global srv
  async with async_playwright() as p:
    b=await p.chromium.launch(executable_path=os.environ.get("CHROME","/usr/bin/google-chrome"),args=["--no-sandbox"])
    actx,admin=await page(b)
    await admin.wait_for_selector("#goSetup"); await shot(admin,"1_signin.png")
    await admin.click("#goSetup"); await admin.fill("#a_name","Fred Schallies"); await admin.fill("#a_user","admin"); await admin.fill("#a_pass","secret1"); await admin.click("#setupBtn")
    await admin.wait_for_selector("#tabTeam:not([hidden])"); ok("admin account set up on first open",True)
    await admin.click("#tabTeam")
    for n,u,pw in [("Sipho Dlamini","sipho","oven123"),("Thabo Nkosi","thabo","mixer456")]:
        await admin.click("#addTech"); await admin.fill("#t_name",n); await admin.fill("#t_user",u); await admin.fill("#t_pass",pw); await admin.click("#teamSave"); await admin.wait_for_selector(f".member:has-text('{n}')")
    ok("admin created two technician logins",await admin.locator(".member").count()==2)
    await admin.click("#addTech"); await admin.fill("#t_name","Dup"); await admin.fill("#t_user","sipho"); await admin.fill("#t_pass","abcdef"); await admin.click("#teamSave"); await admin.wait_for_selector("text=That username is taken"); await admin.click("#cancelTeam"); ok("duplicate username refused",True)

    sctx,sipho=await page(b)
    ok("setup no longer offered once an admin exists",await sipho.locator("#goSetup").count()==0)
    await login(sipho,"sipho","nope"); await sipho.wait_for_selector("text=Wrong username or password"); ok("wrong password refused",True)
    await login(sipho,"sipho","oven123"); await sipho.wait_for_selector("text=No job cards yet"); ok("technician has no Technicians tab",await sipho.eval_on_selector("#tabTeam","e=>e.hidden"))
    await sipho.click("#tabVan"); await sipho.click("#addPart"); await sipho.fill("#p_partNo","EL-1"); await sipho.fill("#p_desc","Element"); await sipho.fill("#p_qty","4"); await sipho.click("#partForm button[type=submit]"); await sipho.wait_for_selector("text=Element")
    await newcard(sipho,"Bakery A",full=True); await newcard(sipho,"Bakery B"); await synced(sipho)
    await sipho.click(".card:has-text('Bakery A')"); await sipho.wait_for_selector(".signbox img[src]"); ok("signature shows on the saved job card",True)
    ok("status chosen with the chips was saved",await sipho.locator(".jobhead .pill:has-text('Follow-up needed')").count()==1)
    async with sipho.expect_download() as dl: await sipho.click("#pdfOne")
    d=await dl.value
    if SHOTS: await d.save_as(os.path.join(SHOTS,"job.pdf"))
    await sipho.click("[data-go=list]")
    await sipho.click("#tabCust"); await sipho.wait_for_selector(".card.cust:has-text('Bakery A')"); await shot(sipho,"7_customers.png"); await sipho.click(".card.cust:has-text('Bakery A')")
    await sipho.wait_for_selector(".mach:has-text('RM-4471')"); await shot(sipho,"8_customer.png"); ok("machine went into the customer's profile",True)
    ok("customer profile shows the job history",await sipho.locator(".hist").count()==1)
    await sipho.click("[data-machjob='0']"); await sipho.wait_for_selector("#f_serial"); ok("new job from a saved machine is pre-filled",await sipho.input_value("#f_serial")=="RM-4471" and await sipho.input_value("#f_customer")=="Bakery A" and await sipho.input_value("#f_site")=="Empangeni")
    await sipho.click("#cancelForm"); await sipho.click("#tabList")
    await admin.click("#tabList"); await admin.click("#settingsBtn"); await admin.click("#syncBtn"); await admin.click("[data-go=list]"); await cards(admin,2)
    ok("Sipho's job cards reached the admin",True)
    await admin.wait_for_selector(".thumbs-mini img[src]"); ok("photos load on the admin side",True)

    tctx,thabo=await page(b); await login(thabo,"thabo","mixer456"); await thabo.wait_for_selector("text=No job cards yet"); await synced(thabo)
    ok("Thabo doesn't see Sipho's job cards",await thabo.locator(".card").count()==0)
    await thabo.click("#fab"); await thabo.fill("#f_customer","Bakery A"); await thabo.press("#f_customer","Tab"); await thabo.wait_for_selector("[data-mach='0']")
    ok("another tech gets the customer's site and contact filled in",await thabo.input_value("#f_site")=="Empangeni" and "Zanele" in await thabo.input_value("#f_contact"))
    await thabo.click("[data-mach='0']"); ok("another tech can pick the saved machine",await thabo.input_value("#f_serial")=="RM-4471"); await thabo.click("#cancelForm")
    await thabo.click("#tabVan"); await thabo.wait_for_timeout(300); ok("Thabo doesn't see Sipho's van stock",await thabo.locator("text=Element").count()==0)
    # offline: card is saved on the phone, then goes up when the connection is back
    await tctx.set_offline(True); await newcard(thabo,"Bakery C (no signal)",photo=False)
    await thabo.wait_for_function("document.querySelector('#syncState').textContent.startsWith('Offline')",timeout=15000); await shot(thabo,"5_offline.png")
    ok("offline: card saved on the phone and marked as waiting",await thabo.locator(".card").count()==1, await thabo.inner_text("#syncState"))
    await thabo.click("#settingsBtn"); await thabo.click("#signOut"); await thabo.wait_for_selector("text=haven't synced yet"); ok("sign-out blocked while a card is waiting to sync",True); await thabo.click("[data-go=list]")
    await tctx.set_offline(False); await synced(thabo)
    await admin.click("#settingsBtn"); await admin.click("#syncBtn"); await admin.click("[data-go=list]"); await cards(admin,3); await admin.wait_for_timeout(2700); await shot(admin,"2_admin_list.png")
    ok("after reconnecting, the offline card reached the admin",True)
    # a technician asking the server directly gets only their own records
    r=await thabo.evaluate("fetch('/api/sync',{method:'POST',headers:{'Content-Type':'application/json',Authorization:'Bearer '+localStorage.token},body:JSON.stringify({since:0,changes:[]})}).then(r=>r.json()).then(j=>j.changes.filter(c=>c.path.startsWith('jobcards/')).map(c=>c.data.customer))")
    ok("server gives Thabo only his own job cards",r==["Bakery C (no signal)"],str(r))
    r=await thabo.evaluate("fetch('/api/users',{headers:{Authorization:'Bearer '+localStorage.token}}).then(r=>r.status)"); ok("server refuses the logins list to a technician",r==403,str(r))
    sid=await sipho.evaluate("JSON.parse(localStorage.profile).id")
    r=await thabo.evaluate("(sid)=>fetch('/api/sync',{method:'POST',headers:{'Content-Type':'application/json',Authorization:'Bearer '+localStorage.token},body:JSON.stringify({since:0,changes:[{path:'jobcards/forged1',data:{techId:sid,customer:'Forged'},ts:Date.now()}]})}).then(r=>r.json()).then(()=>1)",sid)
    await admin.click("#settingsBtn"); await admin.click("#syncBtn"); await admin.click("[data-go=list]"); await admin.wait_for_timeout(800)
    ok("server refuses a card written in another technician's name",await admin.locator(".card:has-text('Forged')").count()==0)
    # admin screens
    await admin.click("#tabVan"); await admin.wait_for_selector("#vanTechSel"); opts=await admin.eval_on_selector_all("#vanTechSel option","o=>o.map(x=>x.textContent)"); ok("admin can open each technician's van",len(opts)==3,str(opts))
    await admin.select_option("#vanTechSel",label="Sipho Dlamini"); await admin.wait_for_selector("text=Element"); ok("admin sees Sipho's van stock",True)
    await admin.click("#tabList"); await admin.click(".card:has-text('Bakery A')"); await shot(admin,"3_admin_card.png")
    async with admin.expect_download() as dl: await admin.click("#pdfOne")
    d=await dl.value
    if SHOTS: await d.save_as(os.path.join(SHOTS,"job_admin.pdf"))
    ok("admin can make the PDF report of a technician's card",os.path.getsize(await d.path())>20000,d.suggested_filename)
    await admin.click("[data-go=list]"); await admin.click("#tabReports"); await admin.wait_for_selector("#pdfSum")
    async with admin.expect_download() as dl: await admin.click("#pdfSum")
    d=await dl.value
    if SHOTS: await d.save_as(os.path.join(SHOTS,"summary.pdf"))
    await admin.click("#tabTeam"); await admin.wait_for_selector(".member"); await admin.wait_for_timeout(2700); await shot(admin,"4_technicians.png")
    # new password: old one stops, the phone is asked to sign in again, and its job cards are kept
    await admin.click(".member:has-text('Sipho') [data-resetpw]"); await admin.fill("#t_pass","newpass9"); await admin.click("#teamSave"); await admin.wait_for_selector("text=New password set")
    await sipho.click("#settingsBtn"); await sipho.click("#syncBtn"); await sipho.wait_for_selector("#l_user"); ok("after a new password, the phone asks Sipho to sign in again",True)
    await login(sipho,"sipho","oven123"); await sipho.wait_for_selector("text=Wrong username or password"); ok("old password refused",True)
    await login(sipho,"sipho","newpass9"); await cards(sipho,2); ok("new password works and Sipho's cards are still on his phone",True)
    # switch off
    await admin.click(".member:has-text('Thabo') [data-toggle]"); await admin.wait_for_selector(".member.off")
    await thabo.click("#settingsBtn"); await thabo.click("#syncBtn"); await thabo.wait_for_selector("#l_user"); await login(thabo,"thabo","mixer456"); await thabo.wait_for_selector("text=switched off"); ok("switched-off login is signed out and can't get back in",True)
    # server restart: nothing lost, phones stay signed in
    srv.terminate(); srv.wait(); srv=start()
    await sipho.reload(); await cards(sipho,2); await newcard(sipho,"Bakery D"); await synced(sipho)
    await admin.reload(); await cards(admin,4); ok("after a server restart: data kept, everyone still signed in, new cards still arrive",True)
    await b.close()
srv=start()
try: asyncio.run(main())
finally: srv.terminate(); shutil.rmtree(DATA,ignore_errors=True)
print("PAGE ERRORS:",errors or "none"); print(f"{sum(results)}/{len(results)} passed"); sys.exit(0 if all(results) and not errors else 1)
