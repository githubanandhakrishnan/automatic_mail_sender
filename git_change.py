import requests
import base64
import streamlit as st

def upload_to_github(file_path, repo_path):
    token = st.secrets["GITHUB_TOKEN"]
    repo = st.secrets["GITHUB_REPO"]
    branch = st.secrets["GITHUB_BRANCH"]

    # Read file
    with open(file_path, "rb") as f:
        content = base64.b64encode(f.read()).decode("utf-8")

    # Check if file already exists to get SHA
    url = f"https://api.github.com/repos/{repo}/contents/{repo_path}"
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json"
    }

    response = requests.get(url, headers=headers)

    sha = None
    if response.status_code == 200:
        sha = response.json()["sha"]

    data = {
        "message": "Auto update CV from Streamlit Cloud",
        "content": content,
        "branch": branch
    }

    if sha:
        data["sha"] = sha  # Required to update existing file

    upload = requests.put(url, headers=headers, json=data)

    if upload.status_code in [200, 201]:
        print("Uploaded to GitHub successfully!")
    else:
        print("Failed:", upload.json())
