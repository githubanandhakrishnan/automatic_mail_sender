import streamlit as st
from playwright.sync_api import sync_playwright
import os

CV_PATH = "cv.pdf"

def download_cv():
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=False,
            args=["--no-sandbox", "--disable-dev-shm-usage"]
        )
        context = browser.new_context(accept_downloads=True)
        page = context.new_page()

        # Open FlowCV login
        page.goto("https://flowcv.com/login")
        page.locator("button:has-text('Login with email')").click()

        # Login
        page.fill('input[name="email"]', st.secrets["flowcv_email"])
        page.fill('input[name="password"]', st.secrets["flowcv_password"])
        page.click('button[type="submit"]')

        page.wait_for_load_state("networkidle")

        # Navigate to resume page
        page.goto("https://app.flowcv.com/resume/content")

        # Delete old CV if exists
        if os.path.exists(CV_PATH):
            os.remove(CV_PATH)

        # Download handling
        with page.expect_download() as download_info:
            page.click("text=Download")

        download = download_info.value
        download.save_as(CV_PATH)

        browser.close()


    return CV_PATH
