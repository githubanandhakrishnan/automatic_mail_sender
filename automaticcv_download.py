from playwright.sync_api import sync_playwright
import time

CV_PATH = "cv.pdf"

def download_cv():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)  # ✅ headless mode enabled
        context = browser.new_context(accept_downloads=False)
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

        # Download handling
        with page.expect_download() as download_info:
            page.click("text=Download")

        download = download_info.value
        download.save_as("cv.pdf")

        browser.close()

        print("CV downloaded successfully!")

        browser.close()


download_cv()
