import streamlit as st
import google.generativeai as genai
from PIL import Image
import PyPDF2

st.set_page_config(page_title="MediSense", page_icon="💙", layout="wide")

# ---------------- Sidebar ----------------
st.sidebar.title("💙 MediSense")
st.sidebar.caption("Understand Your Medical Reports. In Simple Language.")

uploaded_file = st.sidebar.file_uploader(
    "Upload Medical Report (PDF or Image)", type=["pdf", "png", "jpg", "jpeg"]
)
analyze_btn = st.sidebar.button("Analyze Report", use_container_width=True)

# ---------------- Main UI ----------------
st.title("MediSense")
st.caption("Understand Your Medical Reports. In Simple Language.")


# ---------------- Session state ----------------
if "summary" not in st.session_state:
    st.session_state.summary = None
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

# ---------------- Helpers ----------------
def extract_text_from_pdf(file):
    reader = PyPDF2.PdfReader(file)
    text = ""
    for page in reader.pages:
        text += page.extract_text() or ""
    return text

# ---------------- Configuration ----------------

GEMINI_API_KEY = st.secrets.get("GEMINI_API_KEY", "")

SUMMARY_PROMPT = """
You are MediSense, an AI assistant that explains medical reports to patients who have
NO medical background at all.

Read the medical report content given below (it could be a blood test, urine test,
or scan report) and explain it as if talking to a friend who knows nothing about medicine.

Your response MUST follow this exact structure using Markdown:

## Summary
A short 3-5 sentence plain-language summary of what the report shows overall, and what
it means for the patient's body right now.

## Key Results
For every important value found in the report, list it as:
- **Test Name**: value — (Normal / Borderline / Attention) — one simple sentence on what
  this means for the body. No jargon.

## Jargon Buster
List any medical/technical terms that appeared in the report and explain each in one
simple sentence.

## Questions For Your Doctor
Give 3 short, specific questions the patient could ask their doctor based on this report.

## Disclaimer
Remind the patient this is general education, not medical advice, and that they should
consult their doctor for diagnosis or treatment decisions.

Keep the tone warm and reassuring. Avoid technical terms unless you immediately explain
them.
"""
def get_model(api_key):
    genai.configure(api_key=api_key)
    return genai.GenerativeModel("gemini-3.6-flash")

def analyze_report(api_key, content_parts):
    model = get_model(api_key)
    response = model.generate_content([SUMMARY_PROMPT] + content_parts)
    return response.text

if analyze_btn:
    if not uploaded_file:
        st.error("Please upload a report first.")
    else:
        with st.spinner("Analyzing your report..."):
            try:
                if uploaded_file.type == "application/pdf":
                    text = extract_text_from_pdf(uploaded_file)
                    content_parts = [text]
                else:
                    image = Image.open(uploaded_file)
                    content_parts = [image]

                st.session_state.summary = analyze_report(GEMINI_API_KEY, content_parts)
                st.session_state.chat_history = []  # reset chat for a new report
            except Exception as e:
                st.error(f"Something went wrong: {e}")

if st.session_state.summary:
    st.markdown(st.session_state.summary)
else:
    st.info("👈 Upload a medical report and click 'Analyze Report' to get started.")