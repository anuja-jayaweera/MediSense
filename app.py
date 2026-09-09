import json
import re

import streamlit as st
import streamlit.components.v1 as components
import google.generativeai as genai
from PIL import Image
import PyPDF2

from pathlib import Path

st.set_page_config(page_title="MediSense", page_icon="💙", layout="wide")


# ---------------- Custom styling (external CSS) ----------------
def load_css(path: str):
    css_path = Path(__file__).parent / path
    with open(css_path) as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)


# ---------------- Custom interactivity (external JS) ----------------
def load_js(path: str):
    js_path = Path(__file__).parent / path
    with open(js_path) as f:
        code = f.read()
    # Rendered inside a same-origin iframe; the script reaches into
    # window.parent.document to enhance the real Streamlit DOM. A
    # MutationObserver re-applies itself after every Streamlit rerun,
    # so this only needs to be injected once per page load.
    components.html(f"<script>{code}</script>", height=0, width=0)


load_css("css/style.css")
load_js("js/interactions.js")

STATUS_COLORS = {
    "Normal": "#22c55e",
    "Borderline": "#eab308",
    "Attention": "#ef4444",
}

# ---------------- Sidebar ----------------
st.sidebar.title("💙 MediSense")
st.sidebar.caption("Understand Your Medical Reports. In Simple Language.")

uploaded_file = st.sidebar.file_uploader(
    "Upload Medical Report (PDF or Image)", type=["pdf", "png", "jpg", "jpeg"]
)

if uploaded_file:
    st.sidebar.caption(f"📄 {uploaded_file.name} · {uploaded_file.size / 1024:.1f} KB")

analyze_btn = st.sidebar.button("Analyze Report", use_container_width=True, type="primary")

if st.session_state.get("summary_text"):
    if st.sidebar.button("🗑️ Clear & Start Over", use_container_width=True):
        for key in ["summary_text", "dashboard_items", "chat_history", "raw_response"]:
            st.session_state.pop(key, None)
        st.rerun()

# ---------------- Main UI ----------------
st.title("MediSense")
st.caption("Understand Your Medical Reports. In Simple Language.")

# ---------------- Session state ----------------
if "summary_text" not in st.session_state:
    st.session_state.summary_text = None
if "dashboard_items" not in st.session_state:
    st.session_state.dashboard_items = []
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

# ---------------- Helpers ----------------
def extract_text_from_pdf(file):
    reader = PyPDF2.PdfReader(file)
    text = ""
    for page in reader.pages:
        text += page.extract_text() or ""
    return text


def parse_ai_response(raw_text):
    """Split the model's response into the markdown summary and the
    structured dashboard JSON. Falls back gracefully if either part
    is missing or malformed."""
    summary_match = re.search(r"<<<SUMMARY>>>(.*?)<<<END_SUMMARY>>>", raw_text, re.DOTALL)
    dashboard_match = re.search(r"<<<DASHBOARD>>>(.*?)<<<END_DASHBOARD>>>", raw_text, re.DOTALL)

    summary_text = summary_match.group(1).strip() if summary_match else raw_text.strip()

    dashboard_items = []
    if dashboard_match:
        json_chunk = dashboard_match.group(1).strip()
        json_chunk = re.sub(r"^```(json)?|```$", "", json_chunk, flags=re.MULTILINE).strip()
        try:
            parsed = json.loads(json_chunk)
            if isinstance(parsed, list):
                dashboard_items = parsed
        except json.JSONDecodeError:
            dashboard_items = []

    return summary_text, dashboard_items


STATUS_BG = {
    "Normal": "rgba(34, 197, 94, 0.10)",
    "Borderline": "rgba(234, 179, 8, 0.10)",
    "Attention": "rgba(239, 68, 68, 0.10)",
}

STATUS_EMOJI = {"Normal": "🟢", "Borderline": "🟡", "Attention": "🔴"}


def render_dashboard(items):
    if not items:
        st.info("No structured lab values were detected in this report, but you can still read the full summary in the next tab.")
        return

    counts = {"Normal": 0, "Borderline": 0, "Attention": 0}
    for item in items:
        counts[item.get("status", "Normal")] = counts.get(item.get("status", "Normal"), 0) + 1

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total tests", len(items))
    c2.metric("🟢 Normal", counts.get("Normal", 0))
    c3.metric("🟡 Borderline", counts.get("Borderline", 0))
    c4.metric("🔴 Needs attention", counts.get("Attention", 0))

    st.divider()

    # ---- Interactive controls: search + status filter ----
    search_col, filter_col = st.columns([2, 3])
    with search_col:
        query = st.text_input(
            "🔍 Search a test", placeholder="🔍 Search test name — e.g. Hemoglobin, Glucose..", label_visibility="collapsed"
        )
    with filter_col:
        status_filter = st.segmented_control(
            "Filter by status",
            options=["All", "Normal", "Borderline", "Attention"],
            default="All",
            label_visibility="collapsed",
        )

    st.caption("💡 Click any value below to copy it · press **/** to jump to search")

    filtered = items
    if query:
        filtered = [i for i in filtered if query.lower() in i.get("parameter", "").lower()]
    if status_filter and status_filter != "All":
        filtered = [i for i in filtered if i.get("status", "Normal") == status_filter]

    if not filtered:
        st.warning("No tests match your search/filter.")
        return

    cols = st.columns(3)
    for idx, item in enumerate(filtered):
        status = item.get("status", "Normal")
        color = STATUS_COLORS.get(status, "#94a3b8")
        bg = STATUS_BG.get(status, "rgba(148,163,184,0.12)")
        note = item.get("note", "")
        with cols[idx % 3]:
            st.markdown(f"""
            <div class="ms-card" style="--ms-status-color:{color}; --ms-status-bg:{bg}; animation-delay:{idx * 0.03}s;">
                <div class="ms-card-header">
                    <span class="ms-dot"></span>
                    <span class="ms-card-title">{item.get('parameter', 'Unknown')}</span>
                </div>
                <div class="ms-card-value">{item.get('value', '—')}
                    <span class="ms-card-unit">{item.get('unit', '')}</span>
                </div>
                <div class="ms-card-range">Reference: {item.get('reference_range', 'N/A')}</div>
                <div class="ms-card-status">{STATUS_EMOJI.get(status, '⚪')} {status.upper()}</div>
                <details class="ms-card-note">
                    <summary></summary>
                    {note}
                </details>
            </div>
            """, unsafe_allow_html=True)

# ---------------- Configuration ----------------
GEMINI_API_KEY = st.secrets.get("GEMINI_API_KEY", "")

SUMMARY_PROMPT = """
You are MediSense, an AI assistant that explains medical reports to patients who have
NO medical background at all.

Read the medical report content given below (it could be a blood test, urine test,
or scan report) and explain it as if talking to a friend who knows nothing about medicine.

Your response MUST contain exactly two parts, in this exact order, with nothing before,
between, or after them besides the markers themselves.

PART 1 — wrap this between the markers <<<SUMMARY>>> and <<<END_SUMMARY>>>:
Markdown content with these sections, in this order:

## Summary
A short 3-5 sentence plain-language summary of what the report shows overall, and what
it means for the patient's body right now.

## Jargon Buster
List any medical/technical terms that appeared in the report and explain each in one
simple sentence.

## Questions For Your Doctor
Give 3 short, specific questions the patient could ask their doctor based on this report.

## Disclaimer
Remind the patient this is general education, not medical advice, and that they should
consult their doctor for diagnosis or treatment decisions.

Keep the tone warm and reassuring. Avoid technical terms unless you immediately explain
them. Do NOT include a "Key Results" section here — that data goes in Part 2 instead.

PART 2 — wrap this between the markers <<<DASHBOARD>>> and <<<END_DASHBOARD>>>:
A single JSON array and nothing else (no prose, no code fences). One object per test
value found in the report, in this exact shape:
{"parameter": "string", "value": "string", "unit": "string", "reference_range": "string",
"status": "Normal" | "Borderline" | "Attention", "note": "one simple sentence on what this
value means for the patient's body"}
"""


def get_model(api_key):
    genai.configure(api_key=api_key)
    return genai.GenerativeModel("gemini-3.6-flash")


def analyze_report(api_key, content_parts):
    model = get_model(api_key)
    response = model.generate_content([SUMMARY_PROMPT] + content_parts)
    return response.text


def ask_chatbot(api_key, summary, question):
    model = get_model(api_key)
    chat_prompt = f"""
You are MediSense, a friendly AI health assistant. You already gave the patient this
report summary:

{summary}

The patient (who has no medical background) now asks a follow-up question. Answer in
simple, clear, reassuring language. Suggest practical next steps if relevant, but do NOT
give a diagnosis or prescribe medication. Remind them to consult a doctor for anything
that needs medical judgement.

Patient's question: {question}
"""
    response = model.generate_content(chat_prompt)
    return response.text

# ---------------- Analyze flow ----------------
if analyze_btn:
    if not uploaded_file:
        st.error("Please upload a report first.")
    else:
        with st.status("Analyzing your report...", expanded=True) as status:
            try:
                status.write("📖 Reading file...")
                if uploaded_file.type == "application/pdf":
                    text = extract_text_from_pdf(uploaded_file)
                    content_parts = [text]
                else:
                    image = Image.open(uploaded_file)
                    content_parts = [image]

                status.write("🧠 Asking Gemini to interpret the results...")
                raw_response = analyze_report(GEMINI_API_KEY, content_parts)

                status.write("🚦 Building your health dashboard...")
                summary_text, dashboard_items = parse_ai_response(raw_response)

                st.session_state.summary_text = summary_text
                st.session_state.dashboard_items = dashboard_items
                st.session_state.chat_history = []  # reset chat for a new report

                status.update(label="✅ Analysis complete!", state="complete", expanded=False)
            except Exception as e:
                status.update(label="Something went wrong", state="error")
                st.error(f"Something went wrong: {e}")

# ---------------- Results ----------------
if st.session_state.summary_text:
    tab_dashboard, tab_report, tab_chat = st.tabs(["🚦 Dashboard", "📋 Full Report", "💬 Chat"])

    with tab_dashboard:
        render_dashboard(st.session_state.dashboard_items)

    with tab_report:
        st.markdown(st.session_state.summary_text)

    with tab_chat:
        st.subheader("💬 Ask MediSense a question")

        for role, msg in st.session_state.chat_history:
            with st.chat_message(role):
                st.write(msg)

        user_question = st.chat_input("Ask about your report or next steps...")

        if user_question:
            st.session_state.chat_history.append(("user", user_question))
            with st.chat_message("user"):
                st.write(user_question)

            with st.chat_message("assistant"):
                with st.spinner("Thinking..."):
                    try:
                        answer = ask_chatbot(GEMINI_API_KEY, st.session_state.summary_text, user_question)
                    except Exception as e:
                        answer = f"Sorry, something went wrong: {e}"
                    st.write(answer)
                    st.session_state.chat_history.append(("assistant", answer))
else:
    st.info("👈 Upload a medical report and click 'Analyze Report' to get started.")