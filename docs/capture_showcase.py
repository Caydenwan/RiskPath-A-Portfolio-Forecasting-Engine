"""Capture actual browser-rendered public/synthetic product screens. No private data."""
import asyncio
from pathlib import Path
from playwright.async_api import async_playwright, expect

OUT=Path("docs/screenshots")
URL="https://riskpath-workbench.vercel.app/"
async def ready(page):
    await expect(page.locator("#status")).to_contain_text("Calculation complete",timeout=180000)
    await page.evaluate("document.fonts.ready")
async def shot(page, locator, name):
    await expect(locator).to_be_visible(timeout=15000)
    await locator.screenshot(path=str(OUT/name),animations="disabled",scale="css",timeout=30000)
    print("Captured",name,flush=True)
async def main():
    OUT.mkdir(parents=True,exist_ok=True)
    async with async_playwright() as p:
        browser=await p.chromium.launch(headless=True,args=["--no-sandbox"])
        # New isolated context: no remembered API or cloud credentials.
        context=await browser.new_context(viewport={"width":1440,"height":1000},device_scale_factor=1,locale="en-US")
        page=await context.new_page()
        page.on("pageerror",lambda e: print("Browser error:",str(e),flush=True))
        await page.goto(URL+"?view=portfolio",wait_until="domcontentloaded",timeout=60000)
        await ready(page)
        await expect(page.locator("#source")).to_have_value("public")
        await expect(page.locator("#portfolioNav")).to_have_attribute("aria-current","page")
        await page.screenshot(path=str(OUT/"portfolio.png"),animations="disabled",scale="css")
        print("Captured portfolio.png",flush=True)
        await shot(page,page.locator(".panel").filter(has=page.get_by_role("heading",name="Your paths to success",exact=True)),"goal-paths.png")
        await shot(page,page.locator(".panel").filter(has=page.get_by_role("heading",name="Find your path",exact=True)),"feasibility-map.png")
        await page.goto(URL+"?view=research",wait_until="domcontentloaded",timeout=60000)
        await ready(page)
        await expect(page.locator("#researchNav")).to_have_attribute("aria-current","page")
        await expect(page.locator("#source")).to_have_value("public")
        await page.locator("#validateModel").check()
        await page.locator("#compareScenarios").check()
        await page.locator("#run").click()
        await ready(page)
        await page.evaluate("window.scrollTo(0,0)")
        await page.screenshot(path=str(OUT/"research.png"),animations="disabled",scale="css")
        print("Captured research.png",flush=True)
        for title,name in [("Efficient frontier","efficient-frontier.png"),("Model validation","validation.png"),("Scenario comparison","scenarios.png")]:
            await shot(page,page.locator(".panel").filter(has=page.get_by_role("heading",name=title,exact=True)),name)
        # The institutional mode needs 28 assets. Use the explicitly labeled synthetic fixture.
        await page.locator("#institutionalBtn").click()
        await page.locator("#source").select_option("synthetic")
        await page.locator("#mode").select_option("backtest")
        await page.locator("#method").select_option("risk_budget")
        await page.locator("#run").click()
        await ready(page)
        await expect(page.locator("#insight")).to_contain_text("Synthetic experiment")
        await page.evaluate("window.scrollTo(0,0)")
        await page.screenshot(path=str(OUT/"institutional-synthetic.png"),animations="disabled",scale="css")
        print("Captured institutional-synthetic.png",flush=True)
        await browser.close()
asyncio.run(main())
