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

@st.cache_resource
def install_playwright():
    subprocess.run(
        [sys.executable, "-m", "playwright", "install", "chromium"],
        check=True
    )

install_playwright()

# --- CONFIGURATION ---
api_key = st.secrets["api_key"]
sender_email = "anandhakrishnancareer@gmail.com"
sender_password = st.secrets["sender_password"]

GEMINI_MODEL_NAME = "gemini-2.5-flash"
API_URL_TEMPLATE = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL_NAME}:generateContent?key="
MAX_RETRIES = 5

st.set_page_config(
    page_title="AI Job Mail Assistant",
    layout="wide",
    page_icon="📨",
    initial_sidebar_state="collapsed"
)

# --- STYLES ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Sora:wght@300;400;600;700&family=JetBrains+Mono:wght@400;500&display=swap');

    html, body, [class*="css"] {
        font-family: 'Sora', sans-serif;
    }

    /* Background */
    .stApp {
        background: linear-gradient(135deg, #0f0c29, #302b63, #24243e);
        min-height: 100vh;
    }

    /* Hero header */
    .hero-header {
        text-align: center;
        padding: 2.5rem 1rem 1.5rem 1rem;
    }
    .hero-header h1 {
        font-size: 2.6rem;
        font-weight: 700;
        color: #ffffff;
        letter-spacing: -0.5px;
        margin-bottom: 0.3rem;
    }
    .hero-header p {
        font-size: 1rem;
        color: #a9b4d6;
        font-weight: 300;
    }

    /* Step cards */
    .step-card {
        background: rgba(255,255,255,0.06);
        border: 1px solid rgba(255,255,255,0.12);
        border-radius: 16px;
        padding: 1.5rem 1.5rem 1rem 1.5rem;
        backdrop-filter: blur(12px);
        margin-bottom: 1.2rem;
    }
    .step-label {
        display: inline-block;
        background: linear-gradient(90deg, #7b6fff, #a78bfa);
        color: white;
        font-size: 0.7rem;
        font-weight: 600;
        letter-spacing: 1.5px;
        text-transform: uppercase;
        border-radius: 20px;
        padding: 3px 12px;
        margin-bottom: 0.6rem;
    }
    .step-title {
        font-size: 1.1rem;
        font-weight: 600;
        color: #e8e8ff;
        margin-bottom: 0.8rem;
    }

    /* Result card */
    .result-card {
        background: rgba(255,255,255,0.05);
        border: 1px solid rgba(167,139,250,0.25);
        border-radius: 16px;
        padding: 1.5rem;
        margin-top: 1.5rem;
    }
    .result-card h3 {
        color: #c4b5fd;
        font-size: 1rem;
        font-weight: 600;
        margin-bottom: 1rem;
        letter-spacing: 0.5px;
    }
    .meta-row {
        display: flex;
        align-items: center;
        gap: 0.6rem;
        background: rgba(255,255,255,0.05);
        border-radius: 10px;
        padding: 0.6rem 1rem;
        margin-bottom: 0.6rem;
        color: #d1d5f0;
        font-size: 0.9rem;
        font-family: 'JetBrains Mono', monospace;
    }
    .meta-label {
        color: #a78bfa;
        font-weight: 600;
        min-width: 70px;
    }

    /* Divider */
    .styled-divider {
        border: none;
        height: 1px;
        background: linear-gradient(90deg, transparent, rgba(167,139,250,0.4), transparent);
        margin: 1.8rem 0;
    }

    /* Buttons */
    .stButton > button {
        font-family: 'Sora', sans-serif !important;
        font-weight: 600 !important;
        border-radius: 10px !important;
        border: none !important;
        padding: 0.55rem 1.4rem !important;
        transition: all 0.2s ease !important;
        letter-spacing: 0.3px !important;
    }
    .stButton > button[kind="primary"],
    .stButton > button:first-child {
        background: linear-gradient(135deg, #7b6fff, #a78bfa) !important;
        color: white !important;
    }
    .stButton > button:hover {
        opacity: 0.88 !important;
        transform: translateY(-1px) !important;
        box-shadow: 0 6px 20px rgba(123,111,255,0.35) !important;
    }

    /* Inputs */
    .stTextArea textarea,
    .stTextInput input {
        font-family: 'JetBrains Mono', monospace !important;
        font-size: 0.82rem !important;
        background: rgba(255,255,255,0.05) !important;
        border: 1px solid rgba(255,255,255,0.15) !important;
        border-radius: 10px !important;
        color: #e2e8f0 !important;
    }
    .stTextArea textarea:focus,
    .stTextInput input:focus {
        border-color: #7b6fff !important;
        box-shadow: 0 0 0 2px rgba(123,111,255,0.2) !important;
    }

    /* File uploader */
    .stFileUploader {
        background: rgba(255,255,255,0.04) !important;
        border: 2px dashed rgba(167,139,250,0.4) !important;
        border-radius: 12px !important;
        padding: 1rem !important;
    }

    /* Info / warning banners */
    .stInfo, .stWarning, .stSuccess, .stError {
        border-radius: 10px !important;
        font-family: 'Sora', sans-serif !important;
    }

    /* JSON viewer */
    .stJson {
        background: rgba(0,0,0,0.3) !important;
        border-radius: 10px !important;
        border: 1px solid rgba(255,255,255,0.08) !important;
    }

    /* Labels */
    label, .stLabel {
        color: #c4b5fd !important;
        font-size: 0.85rem !important;
        font-weight: 500 !important;
    }

    /* Scrollbar */
    ::-webkit-scrollbar { width: 6px; }
    ::-webkit-scrollbar-track { background: transparent; }
    ::-webkit-scrollbar-thumb { background: rgba(167,139,250,0.4); border-radius: 3px; }
</style>
""", unsafe_allow_html=True)


# --- Helper Functions ---
def file_to_base64(uploaded_file):
    """Convert uploaded file to base64 string."""
    if uploaded_file is None:
        return None
    bytes_data = uploaded_file.getvalue()
    return base64.b64encode(bytes_data).decode("utf-8")


def call_gemini_api(api_key, prompt, image_data_base64=None):
    """Call Gemini API with exponential backoff and expect structured JSON."""
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
                    except json.JSONDecodeError:
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


import smtplib
from email.message import EmailMessage

def send_email(sender_email, sender_password, to_email, subject, body):
    """Send UTF-8 email with CV attachment safely."""
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
                st.info(f"📎 Attached CV: {os.path.basename(cv_path)}")
        except Exception as e:
            st.warning(f"⚠️ Failed to attach CV: {e}")
    else:
        st.warning("⚠️ CV file not found in repo path.")

    try:
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(sender_email, sender_password)
            server.send_message(msg)
            return "✅ Email with CV sent successfully!"
    except Exception as e:
        return f"❌ Failed to send email: {str(e)}"


# --- Streamlit App ---
def app():

    # Hero Header
    st.markdown("""
    <div class="hero-header">
        <h1>📨 AI Job Mail Assistant</h1>
        <p>Upload a job posting → AI crafts your application → Send it in one click</p>
    </div>
    """, unsafe_allow_html=True)

    # CV Refresh bar (top utility row)
    with st.container():
        col_cv, col_spacer = st.columns([1, 4])
        with col_cv:
            if st.button("🔄 Refresh CV"):
                with st.spinner("Generating latest CV..."):
                    file_path = download_cv()
                    upload_to_github(file_path, file_path)
                st.success("CV updated!")

    st.markdown('<hr class="styled-divider">', unsafe_allow_html=True)

    # Main two-column layout
    col1, col2 = st.columns([1, 1.4], gap="large")

    with col1:
        st.markdown("""
        <div class="step-card">
            <div class="step-label">Step 01</div>
            <div class="step-title">Upload Job Posting</div>
        </div>
        """, unsafe_allow_html=True)
        uploaded_file = st.file_uploader(
            "Drop your job image here (JPG / PNG)",
            type=["jpg", "jpeg", "png"],
            label_visibility="visible"
        )
        if uploaded_file:
            st.image(uploaded_file, caption="📋 Job Posting Preview", use_container_width=True)
            image_b64 = file_to_base64(uploaded_file)
        else:
            image_b64 = None
            st.info("No image uploaded yet. Please upload a job vacancy screenshot or flyer.")

    with col2:
        st.markdown("""
        <div class="step-card">
            <div class="step-label">Step 02</div>
            <div class="step-title">Configure AI Prompt</div>
        </div>
        """, unsafe_allow_html=True)

        default_prompt = """Analyze the uploaded image containing job vacancy details.

Extract and generate the following as a valid JSON response:
{
  "MAIL_ID": "<official email ID found in the image or inferred>",
  "SUBJECT_LINE": "<short professional subject line for applying>",
  "EMAIL_CONTENT": "<well-written job application email>"
}

About the applicant:
- Name: Anandha Krishnan S
- Education: Master's in Computer Science, University of Kerala
- Skills: Python, Machine Learning, Data Analytics, SQL, Power BI, TensorFlow, PyTorch
- Experience: AI/ML projects — credit card transaction analysis, currency valuation prediction (LSTM), gesture recognition volume control, diabetic retinopathy detection (CNN), fake news prediction (SVM), employee attrition prediction.
- Interests: AI/ML, Data Science, Full-stack development
- Tone: Friendly, professional, concise (120–150 words), first-person"""

        user_prompt = st.text_area(
            "Prompt (customize if needed)",
            value=default_prompt,
            height=370,
            label_visibility="visible"
        )

    st.markdown('<hr class="styled-divider">', unsafe_allow_html=True)

    # Step 3 — Analyze button (centered)
    st.markdown("""
    <div class="step-card" style="text-align:center; padding: 1rem 1.5rem;">
        <div class="step-label">Step 03</div>
        <div class="step-title">Analyze with Gemini AI</div>
    </div>
    """, unsafe_allow_html=True)

    _, btn_col, _ = st.columns([2, 1, 2])
    with btn_col:
        analyze_clicked = st.button("🚀 Extract & Analyze", use_container_width=True)

    if analyze_clicked:
        if not uploaded_file:
            st.error("⚠️ Please upload a job posting image first.")
        elif not api_key:
            st.error("⚠️ Gemini API key not found in secrets.")
        else:
            with st.spinner("Analyzing image with Gemini AI..."):
                result_json = call_gemini_api(api_key, user_prompt, image_b64)
            st.session_state["analysis_result"] = result_json

    # Step 4 — Results & Send
    if "analysis_result" in st.session_state:
        parsed = st.session_state["analysis_result"]

        st.markdown('<hr class="styled-divider">', unsafe_allow_html=True)
        st.markdown("""
        <div class="step-card">
            <div class="step-label">Step 04</div>
            <div class="step-title">Review & Send</div>
        </div>
        """, unsafe_allow_html=True)

        res_col1, res_col2 = st.columns([1, 1], gap="large")

        with res_col1:
            st.markdown('<div class="result-card"><h3>📋 Extracted Details (JSON)</h3>', unsafe_allow_html=True)
            st.json(parsed)
            st.markdown('</div>', unsafe_allow_html=True)

        with res_col2:
            mail_id = parsed.get('MAIL_ID', 'Not found')
            subject = parsed.get('SUBJECT_LINE', 'Not found')
            body = parsed.get('EMAIL_CONTENT', '')

            st.markdown(f"""
            <div class="result-card">
                <h3>✉️ Email Preview</h3>
                <div class="meta-row"><span class="meta-label">To:</span> {mail_id}</div>
                <div class="meta-row"><span class="meta-label">Subject:</span> {subject}</div>
            </div>
            """, unsafe_allow_html=True)

            st.text_area("Email Body", value=body, height=220, label_visibility="visible")

            st.markdown("<br>", unsafe_allow_html=True)
            _, send_col, _ = st.columns([1, 2, 1])
            with send_col:
                if st.button("📤 Send Email Now", use_container_width=True):
                    if not sender_email or not sender_password:
                        st.error("Sender credentials missing from secrets.")
                    elif not parsed.get("MAIL_ID"):
                        st.error("No recipient email found in AI output.")
                    else:
                        with st.spinner("Sending your application..."):
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
