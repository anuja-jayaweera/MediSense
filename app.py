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
st.info("👈 Upload a medical report and click 'Analyze Report' to get started.")

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