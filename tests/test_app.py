import asyncio, subprocess, sys, time, os
from playwright.async_api import async_playwright
WWW=sys.argv[1]
srv=subprocess.Popen([sys.executable,"-m","http.server","8765","-d",WWW],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL); time.sleep(1)
errors=[]
async def main():
  async with async_playwright() as p:
    b=await p.chromium.launch(executable_path="/usr/bin/google-chrome",args=["--no-sandbox"])
    ctx=await b.new_context(viewport={"width":400,"height":860},accept_downloads=True)
    pg=await ctx.new_page()
    pg.on("pageerror",lambda e:errors.append(str(e)))
    pg.on("console",lambda m:errors.append("console:"+m.text) if m.type=="error" else None)
    await pg.goto("http://localhost:8765/index.html")
    await pg.wait_for_selector("#w_name"); print("1 who screen shown")
    await pg.fill("#w_name","Fred Schallies"); await pg.click("text=Start")
    await pg.wait_for_selector("text=No job cards yet"); await pg.wait_for_timeout(300); await pg.screenshot(path="home.png"); print("2 list empty; sync:",await pg.inner_text("#syncState"))
    # van stock
    await pg.click("#tabVan"); await pg.click("#addPart")
    await pg.fill("#p_partNo","DS-100"); await pg.fill("#p_desc","Oven door seal"); await pg.fill("#p_qty","5"); await pg.fill("#p_min","2")
    await pg.click("#partForm button[type=submit]"); await pg.wait_for_selector("text=Oven door seal"); print("3 part added:",await pg.inner_text(".qty output"))
    # job card
    await pg.click("#tabList"); await pg.click("#fab")
    await pg.fill("#f_serviceCo","ZSP"); await pg.fill("#f_customer","Test Bakery"); await pg.fill("#f_site","Branch 1"); await pg.fill("#f_equipment","Deck oven")
    await pg.fill("#f_fault","Door not sealing"); await pg.fill("#f_work","Replaced seal"); await pg.fill("#f_timeIn","08:00"); await pg.fill("#f_timeOut","09:30")
    await pg.set_input_files("#galIn","photo.jpg")
    await pg.wait_for_function("!document.querySelector('.ph .up')",timeout=15000); print("4 photo saved")
    await pg.fill("#cap_0","before"); await pg.screenshot(path="s_form.png",full_page=True)
    await pg.select_option("#usedPick",label="DS-100 · Oven door seal (5 on van)"); await pg.fill("#usedQty","2"); await pg.click("#addUsed")
    await pg.click("#saveBottom"); await pg.wait_for_selector("#pdfOne"); print("5 card saved; detail img src set:",await pg.eval_on_selector(".gallery img","e=>!!e.getAttribute('src')"))
    await pg.click("#tabVan"); await pg.wait_for_timeout(2900); await pg.screenshot(path="s_van.png"); print("6 stock after use (expect 3):",await pg.inner_text(".qty output"))
    # PDF
    await pg.click("#tabList"); await pg.click(".card")
    async with pg.expect_download() as dl:
      await pg.click("#pdfOne")
    d=await dl.value; path=await d.path(); await d.save_as("job.pdf"); await pg.wait_for_timeout(2800); await pg.screenshot(path="s_detail.png"); await pg.click("[data-go=list]"); await pg.wait_for_timeout(300); await pg.screenshot(path="s_list.png"); await pg.click(".card"); print("7 PDF:",d.suggested_filename,os.path.getsize(path),"bytes")
    # settings + logo
    await pg.click("#settingsBtn"); await pg.set_input_files("#logoIn","logo.png"); await pg.wait_for_selector("text=Logo ready")
    await pg.set_input_files("#brandIn","logo.png"); await pg.wait_for_selector(".brands img[src]")
    await pg.fill("#s_name","Macadams International"); await pg.fill("#s_footer","Durban branch"); await pg.click("#setForm button[type=submit]")
    await pg.wait_for_selector("#coLogo:not([hidden])"); print("8 settings saved; header:",await pg.inner_text("#coName"))
    # reload: persisted on the phone?
    await pg.reload(); await pg.wait_for_selector(".card"); await pg.wait_for_timeout(500)
    print("9 after reload: cards",await pg.locator(".card").count(),"| thumbs loaded",await pg.eval_on_selector(".thumbs-mini img","e=>!!e.getAttribute('src')"),"| logo",await pg.eval_on_selector("#coLogo","e=>!e.hidden"))
    # edit card: reduce parts to 1 -> stock 4
    await pg.click(".card"); await pg.click("#editOne"); await pg.click("[data-unused='0']")
    await pg.select_option("#usedPick",index=1); await pg.fill("#usedQty","1"); await pg.click("#addUsed"); await pg.click("#saveTop"); await pg.wait_for_selector("#pdfOne")
    await pg.click("#tabVan"); await pg.wait_for_timeout(300); print("10 stock after edit (expect 4):",await pg.inner_text(".qty output"))
    # summary pdf
    await pg.click("#tabReports"); await pg.wait_for_timeout(2900); await pg.screenshot(path="s_reports.png")
    async with pg.expect_download() as dl:
      await pg.click("#pdfSum")
    d=await dl.value; print("11 summary PDF:",d.suggested_filename,os.path.getsize(await d.path()))
    # delete -> stock back to 5
    await pg.click("#tabList"); await pg.click(".card"); await pg.click("#delAsk"); await pg.click("#delYes"); await pg.wait_for_selector("text=No job cards yet")
    await pg.click("#tabVan"); await pg.wait_for_timeout(300); print("12 stock after delete (expect 5):",await pg.inner_text(".qty output"))
    await pg.click("#tabList"); await pg.screenshot(path="shot.png")
    await b.close()
asyncio.run(main()); srv.terminate()
print("ERRORS:",errors or "none")
