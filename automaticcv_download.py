from playwright.sync_api import sync_playwright
import os
import subprocess

CV_PATH = "cv.pdf"

def run_git_command(command):
    result = subprocess.run(command, capture_output=True, text=True, shell=True)
    print(f"$ {command}")
    print(result.stdout)
    if result.returncode != 0:
        print(f"Git error: {result.stderr}")
    return result

def download_cv():
    # Delete old CV before downloading new one
    if os.path.exists(CV_PATH):
        os.remove(CV_PATH)
        print("Old CV deleted.")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(accept_downloads=True)
        page = context.new_page()

        page.goto("https://flowcv.com/login")
        page.locator("text=Login with email").click()

        page.fill('input[name="email"]', "anandhakrishnancareer@gmail.com")
        page.fill('input[name="password"]', "Anandhu@123")
        page.click('button[type="submit"]')
        page.wait_for_timeout(5000)

        page.goto("https://app.flowcv.com/resume/content")

        with page.expect_download() as download_info:
            page.click("text=Download")

        download = download_info.value
        download.save_as(CV_PATH)
        browser.close()

    print("CV downloaded successfully!")

    # ✅ Commit and push updated CV to Git repo
    run_git_command("git config user.email 'github-actions@github.com'")
    run_git_command("git config user.name 'GitHub Actions'")
    run_git_command(f"git add {CV_PATH}")
    run_git_command('git commit -m "chore: update cv.pdf [skip ci]"')
    run_git_command("git push")

    print("CV pushed to repo successfully!")
    return CV_PATH
