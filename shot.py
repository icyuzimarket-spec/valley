import sys
from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:8000"
OUT = sys.argv[1] if len(sys.argv) > 1 else "shots"

pages = [
    ("home", "/"),
    ("login", "/accounts/login/"),
    ("signup", "/accounts/signup/"),
]

viewports = {
    "mobile": {"width": 390, "height": 844},
    "desktop": {"width": 1600, "height": 900},
}

with sync_playwright() as p:
    browser = p.chromium.launch()
    for vp_name, vp in viewports.items():
        page = browser.new_page(viewport=vp)
        for name, path in pages:
            page.goto(BASE + path, wait_until="networkidle")
            page.screenshot(path=f"{OUT}/{name}_{vp_name}.png", full_page=True)
            print(f"captured {name}_{vp_name}.png")
        page.close()
    browser.close()
