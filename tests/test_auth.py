import asyncio, subprocess, sys, time, json
from playwright.async_api import async_playwright
WWW=sys.argv[1]
srv=subprocess.Popen([sys.executable,"-m","http.server","8766","-d",WWW],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL); time.sleep(1)
errors=[]; MOCK=open(__import__("os").path.join(__import__("os").path.dirname(__file__),"mock_vendor.js")).read()
async def login(pg,u,p):
    await pg.wait_for_selector("#l_user"); await pg.fill("#l_user",u); await pg.fill("#l_pass",p); await pg.click("#loginBtn")
async def signout(pg):
    await pg.click("#settingsBtn"); await pg.click("#signOut"); await pg.wait_for_selector("#l_user")
async def newcard(pg,cust):
    await pg.click("#tabList"); await pg.click("#fab"); await pg.fill("#f_customer",cust); await pg.fill("#f_equipment","Rack oven")
    await pg.set_input_files("#galIn","photo.jpg"); await pg.wait_for_function("!document.querySelector('.ph .up')",timeout=15000)
    await pg.click("#saveBottom"); await pg.wait_for_selector("#pdfOne"); await pg.click("[data-go=list]")
async def main():
  async with async_playwright() as p:
    b=await p.chromium.launch(executable_path="/usr/bin/google-chrome",args=["--no-sandbox"])
    ctx=await b.new_context(viewport={"width":400,"height":860})
    await ctx.route("**/vendor.js",lambda r:r.fulfill(body=MOCK,content_type="application/javascript"))
    await ctx.route("**/firebase-config.js",lambda r:r.fulfill(body='window.FIREBASE_CONFIG={apiKey:"test"};',content_type="application/javascript"))
    pg=await ctx.new_page()
    pg.on("pageerror",lambda e:errors.append(str(e)))
    await pg.goto("http://localhost:8766/index.html")
    await pg.wait_for_selector("#goSetup"); await pg.screenshot(path="a_login.png"); print("1 sign-in screen, setup offered; tab bar hidden:",await pg.eval_on_selector(".tabbar","e=>e.hidden"))
    await pg.click("#goSetup"); await pg.fill("#a_name","Fred Schallies"); await pg.fill("#a_user","Admin"); await pg.fill("#a_pass","secret1"); await pg.click("#setupBtn")
    await pg.wait_for_selector("#tabTeam:not([hidden])"); print("2 admin created and signed in; Technicians tab shown")
    await pg.click("#tabTeam"); await pg.click("#addTech"); await pg.fill("#t_name","Sipho Dlamini"); await pg.fill("#t_user","sipho"); await pg.fill("#t_pass","oven123"); await pg.screenshot(path="a_addtech.png"); await pg.click("#teamSave")
    await pg.wait_for_selector(".member"); 
    await pg.click("#addTech"); await pg.fill("#t_name","Thabo Nkosi"); await pg.fill("#t_user","thabo"); await pg.fill("#t_pass","mixer456"); await pg.click("#teamSave")
    await pg.wait_for_function("document.querySelectorAll('.member').length===2"); print("3 two tech logins created; admin still signed in:",await pg.eval_on_selector("#tabTeam","e=>!e.hidden"))
    await pg.click("#addTech"); await pg.fill("#t_name","Dup"); await pg.fill("#t_user","sipho"); await pg.fill("#t_pass","abcdef"); await pg.click("#teamSave"); await pg.wait_for_selector("text=That username is taken"); await pg.click("#cancelTeam"); print("4 duplicate username refused")
    await signout(pg); print("5 admin signed out; setup no longer offered:",await pg.locator("#goSetup").count()==0)
    await login(pg,"sipho","wrong!"); await pg.wait_for_selector("text=Wrong username or password"); print("6 wrong password refused")
    await login(pg,"sipho","oven123"); await pg.wait_for_selector("text=No job cards yet"); print("7 Sipho signed in; Technicians tab hidden:",await pg.eval_on_selector("#tabTeam","e=>e.hidden"))
    await newcard(pg,"Bakery A"); await newcard(pg,"Bakery B"); print("8 Sipho cards:",await pg.locator(".card").count())
    await pg.click("#tabVan"); await pg.click("#addPart"); await pg.fill("#p_partNo","EL-1"); await pg.fill("#p_desc","Element"); await pg.fill("#p_qty","4"); await pg.click("#partForm button[type=submit]"); await pg.wait_for_selector("text=Element")
    await pg.click("#settingsBtn"); await pg.wait_for_selector("#signOut"); await pg.screenshot(path="a_techsettings.png"); print("9 tech settings has company section:",await pg.locator("#s_name").count()>0); await pg.click("[data-go=list]")
    await signout(pg)
    await login(pg,"thabo","mixer456"); await pg.wait_for_selector("text=No job cards yet"); print("10 Thabo sees Sipho's cards:",await pg.locator(".card").count())
    await newcard(pg,"Bakery C"); print("11 Thabo cards:",await pg.locator(".card").count())
    await pg.click("#tabVan"); await pg.wait_for_timeout(300); print("12 Thabo sees Sipho's van part:",await pg.locator("text=Element").count()>0, "| van picker:",await pg.locator("#vanTechSel").count())
    # tech tries to read everything directly: must be refused
    r=await pg.evaluate("window.firebase.firestore().collection('jobcards').get().then(()=> 'ALLOWED').catch(e=>e.code)"); print("13 tech reading all job cards directly:",r)
    r=await pg.evaluate("window.firebase.firestore().collection('users').get().then(()=> 'ALLOWED').catch(e=>e.code)"); print("14 tech reading logins list directly:",r)
    await signout(pg)
    await login(pg,"admin","secret1"); await pg.wait_for_function("document.querySelectorAll('.card').length===3"); await pg.wait_for_timeout(400)
    await pg.screenshot(path="a_adminlist.png"); print("15 admin sees all cards:",await pg.locator(".card").count(),"| names:",await pg.eval_on_selector_all(".card .m","els=>[...new Set(els.map(e=>e.innerText.split('\\n').find(x=>/Sipho|Thabo/.test(x))||e.innerText))]"))
    print("16 photos load for admin:",await pg.eval_on_selector(".thumbs-mini img","e=>!!e.getAttribute('src')"))
    await pg.click("#tabVan"); await pg.wait_for_selector("#vanTechSel"); print("17 admin van picker options:",await pg.eval_on_selector_all("#vanTechSel option","o=>o.map(x=>x.textContent)"))
    await pg.click("#tabTeam"); await pg.wait_for_selector(".member"); await pg.wait_for_timeout(300); await pg.screenshot(path="a_team.png")
    # reset Sipho's password
    await pg.click(".member:has-text('Sipho') [data-resetpw]"); await pg.fill("#t_pass","newpass9"); await pg.click("#teamSave"); await pg.wait_for_selector("text=New password set"); 
    # switch Thabo off
    await pg.click(".member:has-text('Thabo') [data-toggle]"); await pg.wait_for_selector(".member.off"); print("18 password reset + Thabo switched off")
    await signout(pg)
    await login(pg,"sipho","oven123"); await pg.wait_for_selector("text=Wrong username or password"); print("19 Sipho's old password refused")
    await login(pg,"sipho","newpass9"); await pg.wait_for_function("document.querySelectorAll('.card').length===2"); print("20 Sipho's new password works, still has his cards:",await pg.locator(".card").count())
    await pg.click("#tabVan"); await pg.wait_for_selector("text=Element"); print("21 Sipho still has his van stock")
    await signout(pg)
    await login(pg,"thabo","mixer456"); await pg.wait_for_selector("text=switched off"); await pg.wait_for_selector("#l_user"); print("22 switched-off login can't get in")
    await pg.reload(); await login(pg,"admin","secret1"); await pg.wait_for_function("document.querySelectorAll('.card').length===3"); await pg.reload(); await pg.wait_for_function("document.querySelectorAll('.card').length===3"); print("23 admin stays signed in after reopening the app")
    await b.close()
asyncio.run(main()); srv.terminate()
print("ERRORS:",errors or "none")
