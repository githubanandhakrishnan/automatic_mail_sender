import streamlit as st
import requests
import base64
import json
import os
import time
import smtplib
import subprocess
import sys
from email.message import EmailMessage
from git_change import upload_to_github
from automaticcv_download import download_cv

# =========================================================
# PAGE CONFIG
# =========================================================
st.set_page_config(
    page_title="AI Job Mail Assistant",
    page_icon="📨",
    layout="centered"
)

# =========================================================
# INSTALL PLAYWRIGHT (Cached)
# =========================================================
@st.cache_resource
def install_playwright():
    subprocess.run(
        [sys.executable, "-m", "playwright", "install", "chromium"],
        check=True
    )

install_playwright()

# =========================================================
# CONFIGURATION
# =========================================================
api_key = st.secrets.get("api_key")
sender_email = "anandhakrishnancareer@gmail.com"
sender_password = st.secrets.get("sender_password")

GEMINI_MODEL_NAME = "gemini-2.5-flash"
API_URL_TEMPLATE = (
    f"https://generativelanguage.googleapis.com/v1beta/models/"
    f"{GEMINI_MODEL_NAME}:generateContent?key="
)
MAX_RETRIES = 5

# =========================================================
# CLEAN UI STYLING
# =========================================================
st.markdown("""
<style>
.block-container {
    padding-top: 2rem;
    padding-bottom: 2rem;
}

.stButton>button {
    background-color: #2563eb;
    color: white;
    border-radius: 8px;
    padding: 0.6rem 1.2rem;
    font-weight: 600;
}

.stButton>button:hover {
    background-color: #1e40af;
}

.stTextInput>div>div>input, textarea {
    border-radius: 8px;
}

</style>
""", unsafe_allow_html=True)

# =========================================================
# HELPER FUNCTIONS
# =========================================================
def file_to_base64(uploaded_file):
    if uploaded_file is None:
        return None
    return base64.b64encode(uploaded_file.getvalue()).decode("utf-8")


def call_gemini_api(api_key, prompt, image_data_base64=None):
    if not api_key:
        return {
            "MAIL_ID": "",
            "SUBJECT_LINE": "",
            "EMAIL_CONTENT": "API key missing."
        }

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
            response = requests.post(
                api_url,
                headers=headers,
                data=json.dumps(payload)
            )
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
                return {
                    "MAIL_ID": "",
                    "SUBJECT_LINE": "",
                    "EMAIL_CONTENT": text_output
                }

        except requests.exceptions.RequestException:
            if attempt < MAX_RETRIES - 1:
                time.sleep(2 ** attempt)
            else:
                return {
                    "MAIL_ID": "",
                    "SUBJECT_LINE": "",
                    "EMAIL_CONTENT": "API request failed."
                }


def send_email(sender_email, sender_password, to_email, subject, body):
    msg = EmailMessage()
    msg["From"] = sender_email
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.set_content(body, subtype="plain", charset="utf-8")

    # Attach CV
    cv_path = os.path.join(os.getcwd(), "cv.pdf")
    if os.path.exists(cv_path):
        with open(cv_path, "rb") as f:
            msg.add_attachment(
                f.read(),
                maintype="application",
                subtype="pdf",
                filename="cv.pdf"
            )

    try:
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(sender_email, sender_password)
            server.send_message(msg)
        return "✅ Email sent successfully!"
    except Exception as e:
        return f"❌ Email failed: {str(e)}"

# =========================================================
# MAIN APP
# =========================================================
def app():
    st.title("📨 AI-Powered Job Application Mail Sender")
    st.markdown(
        "Generate and send professional job application emails "
        "automatically using AI."
    )

    st.divider()

    # STEP 1 - Update CV
    st.subheader("🔄 Step 1: Update Resume (Optional)")
    if st.button("Generate Latest CV"):
        with st.spinner("Generating CV..."):
            file_path = download_cv()
            upload_to_github(file_path, file_path)
        st.success("✅ CV Updated Successfully!")

    st.divider()

    # STEP 2 - Upload Image
    st.subheader("🖼️ Step 2: Upload Job Posting Image")
    uploaded_file = st.file_uploader(
        "Upload JPG or PNG",
        type=["jpg", "jpeg", "png"]
    )

    image_b64 = None
    if uploaded_file:
        st.image(
            uploaded_file,
            caption="Uploaded Job Posting",
            use_container_width=True
        )
        image_b64 = file_to_base64(uploaded_file)
        st.success("Image uploaded successfully!")

    st.divider()

    # STEP 3 - Generate Email
    st.subheader("🧠 Step 3: Generate Email")

    default_prompt = """
Analyze the uploaded job vacancy image.

Return valid JSON:
{
  "MAIL_ID": "",
  "SUBJECT_LINE": "",
  "EMAIL_CONTENT": ""
}

Tone: Friendly, respectful, professional.
Length: 120-150 words.
"""

    user_prompt = st.text_area(
        "Modify instructions if needed:",
        value=default_prompt,
        height=200
    )

    if st.button("🚀 Generate Email"):
        if not uploaded_file:
            st.error("Please upload a job image first.")
        elif not api_key:
            st.error("Gemini API key missing.")
        else:
            with st.spinner("Analyzing with AI..."):
                result_json = call_gemini_api(
                    api_key,
                    user_prompt,
                    image_b64
                )
                result_json = result_json.replace("```json", "").replace("```", "").replace("json", "").strip()
                

            
            st.session_state["analysis_result"] = result_json
            st.success("Email generated successfully!")

    st.divider()

    # STEP 4 - Review & Send
    if "analysis_result" in st.session_state:
        parsed = st.session_state["analysis_result"]

        st.subheader("📋 Step 4: Review & Send")

        to_email = st.text_input(
            "Recipient Email",
            value=parsed.get("MAIL_ID", "")
        )

        subject = st.text_input(
            "Subject",
            value=parsed.get("SUBJECT_LINE", "")
        )

        body = st.text_area(
            "Email Body",
            value=parsed.get("EMAIL_CONTENT", ""),
            height=250
        )

        if st.button("📤 Send Email"):
            if not sender_password:
                st.error("Sender password missing in secrets.")
            elif not to_email:
                st.error("Recipient email missing.")
            else:
                with st.spinner("Sending email..."):
                    status = send_email(
                        sender_email,
                        sender_password,
                        to_email,
                        subject,
                        body
                    )

                if "✅" in status:
                    st.success(status)
                else:
                    st.error(status)


if __name__ == "__main__":
    app()


