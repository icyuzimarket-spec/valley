from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={"width": 390, "height": 844})
    page.goto("http://127.0.0.1:8000/", wait_until="networkidle")

    info = page.eval_on_selector(
        ".table-responsive",
        "el => ({overflowX: getComputedStyle(el).overflowX, scrollWidth: el.scrollWidth, clientWidth: el.clientWidth})",
    )
    print("before scroll:", info)

    page.eval_on_selector(".table-responsive", "el => el.scrollTo({left: 9999})")
    page.wait_for_timeout(200)
    scroll_left = page.eval_on_selector(".table-responsive", "el => el.scrollLeft")
    print("scrollLeft after scrollTo:", scroll_left)

    page.screenshot(path="shots/home_mobile_scrolled.png", full_page=True)
    browser.close()
