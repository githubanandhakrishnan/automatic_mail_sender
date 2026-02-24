from playwright.sync_api import sync_playwright
import os

CV_PATH = "cv.pdf"

def download_cv():
    # Delete old CV before downloading new one
    if os.path.exists(CV_PATH):
        os.remove(CV_PATH)
        print("Old CV deleted.")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(accept_downloads=True)
        page = context.new_page()

        # Open FlowCV login
        page.goto("https://flowcv.com/login")
        page.locator("text=Login with email").click()

        # Login
        page.fill('input[name="email"]', "anandhakrishnancareer@gmail.com")
        page.fill('input[name="password"]', "Anandhu@123")
        page.click('button[type="submit"]')
        page.wait_for_timeout(5000)

        # Navigate to resume page
        page.goto("https://app.flowcv.com/resume/content")

        # Download CV
        with page.expect_download() as download_info:
            page.click("text=Download")

        download = download_info.value
        download.save_as(CV_PATH)  # saves directly to cv.pdf

        browser.close()  # ✅ only called once

    print("CV downloaded and updated successfully!")
    return CV_PATH
