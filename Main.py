import streamlit as st
import requests
import base64
import json
import os
import time
import smtplib
from email.mime.application import MIMEApplication
from git_change import upload_to_github
from io import BytesIO
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email import policy
from automaticcv_download import download_cv
import subprocess
import sys

# =========================
# PAGE CONFIG
# =========================
st.set_page_config(
    page_title="AI Job Mail Assistant",
    page_icon="📨",
    layout="wide"
)

# =========================
# CUSTOM UI STYLING
# =========================
st.markdown("""
<style>
.main {
    background-color: #f8fafc;
}
.block-container {
    padding-top: 2rem;
    padding-bottom: 2rem;
}
.section-card {
    background: white;
    padding: 25px;
    border-radius: 15px;
    box-shadow: 0 4px 12px rgba(0,0,0,0.05);
    margin-bottom: 25px;
}
.stButton>button {
    background-color: #2563eb;
    color: white;
    border-radius: 8px;
    padding: 0.6rem 1.2rem;
    font-weight: 600;
    border: none;
}
.stButton>button:hover {
    background-color: #1d4ed8;
}
.stTextInput>div>div>input,
textarea {
    border-radius: 8px !important;
}
h1, h2, h3 {
    color: #1e293b;
}
.small-text {
    font-size: 14px;
    color: #64748b;
}
</style>
""", unsafe_allow_html=True)

# =========================
# PLAYWRIGHT INSTALL
# =========================
@st.cache_resource
def install_playwright():
    subprocess.run(
        [sys.executable, "-m", "playwright", "install", "chromium"],
        check=True
    )

install_playwright()

# =========================
# CONFIG
# =========================
api_key = st.secrets["api_key"]
sender_email = "anandhakrishnancareer@gmail.com"
sender_password = st.secrets["sender_password"]

GEMINI_MODEL_NAME = "gemini-2.5-flash"
API_URL_TEMPLATE = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL_NAME}:generateContent?key="
MAX_RETRIES = 5

# =========================
# HELPER FUNCTIONS
# =========================
def file_to_base64(uploaded_file):
    if uploaded_file is None:
        return None
    bytes_data = uploaded_file.getvalue()
    return base64.b64encode(bytes_data).decode("utf-8")


def call_gemini_api(api_key, prompt, image_data_base64=None):
    if not api_key:
        st.error("Please enter your Gemini API Key.")
        return {"MAIL_ID": "", "SUBJECT_LINE": "", "EMAIL_CONTENT": "API key missing."}

    headers = {"Content-Type": "application/json"}
    api_url = API_URL_TEMPLATE + api_key
    parts = [{"text": prompt}]

    if image_data_base64:
        parts.append({
            "inlineData": {
                "mimeType": "image/jpeg",
                "data": image_data_base64
            }
        })

    payload = {"contents": [{"parts": parts}]}

    for attempt in range(MAX_RETRIES):
        try:
            response = requests.post(api_url, headers=headers, data=json.dumps(payload))
            response.raise_for_status()
            result = response.json()
            text_output = (
                result.get("candidates", [{}])[0]
                .get("content", {})
                .get("parts", [{}])[0]
                .get("text", "")
            )

            try:
                return json.loads(text_output)
            except json.JSONDecodeError:
                import re
                match = re.search(r"\{.*\}", text_output, re.DOTALL)
                if match:
                    try:
                        return json.loads(match.group(0))
                    except:
                        return {"MAIL_ID": "", "SUBJECT_LINE": "", "EMAIL_CONTENT": text_output}
                else:
                    return {"MAIL_ID": "", "SUBJECT_LINE": "", "EMAIL_CONTENT": text_output}

        except requests.exceptions.RequestException as e:
            if hasattr(response, "status_code") and response.status_code == 429 and attempt < MAX_RETRIES - 1:
                wait_time = 2 ** attempt
                st.warning(f"Rate limit hit. Retrying in {wait_time}s...")
                time.sleep(wait_time)
            else:
                st.error(f"API Request Failed: {e}")
                return {"MAIL_ID": "", "SUBJECT_LINE": "", "EMAIL_CONTENT": "Error processing request."}

    return {"MAIL_ID": "", "SUBJECT_LINE": "", "EMAIL_CONTENT": "Failed after multiple retries."}


from email.message import EmailMessage

def send_email(sender_email, sender_password, to_email, subject, body):
    msg = EmailMessage()
    msg["From"] = sender_email
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.set_content(body, subtype="plain", charset="utf-8")

    cv_path = os.path.join(os.getcwd(), "cv.pdf")

    if os.path.exists(cv_path):
        try:
            with open(cv_path, "rb") as f:
                msg.add_attachment(
                    f.read(),
                    maintype="application",
                    subtype="pdf",
                    filename=os.path.basename(cv_path)
                )
                st.info(f"📎 CV Attached: {os.path.basename(cv_path)}")
        except Exception as e:
            st.warning(f"Failed to attach CV: {e}")
    else:
        st.warning("CV file not found.")

    try:
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(sender_email, sender_password)
            server.send_message(msg)
            return "✅ Email with CV sent successfully!"
    except Exception as e:
        return f"❌ Failed to send email: {str(e)}"

# =========================
# MAIN APP
# =========================
def app():

    st.title("📨 AI Job Mail Assistant")
    st.markdown("<p class='small-text'>Upload a job image → Extract details → Generate email → Send automatically</p>", unsafe_allow_html=True)

    # ================= CV SECTION =================
    with st.container():
        st.markdown("### 🔄 CV Management")
        col_a, col_b = st.columns([1,3])

        with col_a:
            if st.button("Refresh CV"):
                with st.spinner("Generating latest CV..."):
                    file_path = download_cv()
                    upload_to_github(file_path, file_path)
                st.success("CV Updated Successfully!")

        with col_b:
            st.markdown("<p class='small-text'>Ensure your latest CV is generated before sending applications.</p>", unsafe_allow_html=True)

    st.divider()

    # ================= INPUT SECTION =================
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### 📤 Step 1: Upload Job Image")
        uploaded_file = st.file_uploader("Upload JPG/PNG", type=["jpg", "jpeg", "png"])

        if uploaded_file:
            st.image(uploaded_file, use_container_width=True)
            image_b64 = file_to_base64(uploaded_file)
        else:
            image_b64 = None

    with col2:
        st.markdown("### 🤖 Step 2: AI Instructions")

        default_prompt = """
Analyze the uploaded image containing job vacancy details.

Extract and generate the following as a valid JSON response:
{
  "MAIL_ID": "<official email ID found in the image or inferred>",
  "SUBJECT_LINE": "<short professional subject line for applying>",
  "EMAIL_CONTENT": "<well-written job application email>"
}
"""
        user_prompt = st.text_area("Prompt", value=default_prompt, height=300)

    st.divider()

    # ================= ANALYZE =================
    if st.button("🚀 Extract & Generate Email", use_container_width=True):
        if not uploaded_file:
            st.error("Please upload an image first.")
        else:
            with st.spinner("Analyzing with Gemini AI..."):
                result_json = call_gemini_api(api_key, user_prompt, image_b64)
            st.session_state["analysis_result"] = result_json

    # ================= RESULTS =================
    if "analysis_result" in st.session_state:

        parsed = st.session_state["analysis_result"]

        st.markdown("## 📬 Extracted Email Details")

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("**Recipient Email**")
            st.info(parsed.get("MAIL_ID", "Not found"))

        with col2:
            st.markdown("**Subject Line**")
            st.info(parsed.get("SUBJECT_LINE", "Not found"))

        st.markdown("**Email Body**")
        st.text_area("", parsed.get("EMAIL_CONTENT", ""), height=200)

        st.divider()

        if st.button("📤 Send Email Now", use_container_width=True):
            if not parsed.get("MAIL_ID"):
                st.error("No recipient email found.")
            else:
                with st.spinner("Sending email..."):
                    status = send_email(
                        sender_email,
                        sender_password,
                        parsed["MAIL_ID"],
                        parsed["SUBJECT_LINE"],
                        parsed["EMAIL_CONTENT"]
                    )
                if "✅" in status:
                    st.success(status)
                else:
                    st.error(status)


if __name__ == "__main__":
    app()
