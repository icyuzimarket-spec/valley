from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={"width": 1600, "height": 900})
    page.goto("http://127.0.0.1:8000/accounts/login/", wait_until="networkidle")

    css_href = page.eval_on_selector('link[href*="theme.css"]', "el => el.href")
    print("theme.css href:", css_href)

    resp = page.request.get(css_href)
    body_text = resp.text()
    print("contains new flex rule:", "flex: 1 1 auto" in body_text)
    print("cache-control header:", resp.headers.get("cache-control"))

    for sel in ["body", "main", ".auth-page"]:
        info = page.eval_on_selector(
            sel,
            "el => ({display: getComputedStyle(el).display, flex: getComputedStyle(el).flex, height: el.getBoundingClientRect().height, minHeight: getComputedStyle(el).minHeight})",
        )
        print(sel, info)

    print("viewport height:", page.viewport_size)
    print("document scrollHeight:", page.evaluate("document.documentElement.scrollHeight"))
    browser.close()
