import json
import os
from urllib.parse import urljoin

import requests
import streamlit as st

BACKEND_URL_DEFAULT = "http://localhost:8000"

st.set_page_config(
    page_title="SHL Assessment Agent",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.session_state.setdefault("backend_url", os.environ.get("BACKEND_URL", BACKEND_URL_DEFAULT))
st.session_state.setdefault("show_upload_panel", False)
st.session_state.setdefault("last_uploaded_file", "")

if "messages" not in st.session_state:
    st.session_state.messages = []

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

if "recommendations" not in st.session_state:
    st.session_state.recommendations = []


def reset_conversation():
    st.session_state.messages = []
    st.session_state.chat_history = []
    st.session_state.recommendations = []
    st.session_state.show_upload_panel = False
    st.session_state.last_uploaded_file = ""
    st.session_state.user_input = ""


def toggle_upload_panel():
    st.session_state.show_upload_panel = not st.session_state.show_upload_panel


def chat_history_json() -> str:
    history = [
        {"role": role, "content": content}
        for role, content in st.session_state.chat_history
    ]
    return json.dumps({"history": history}, indent=2)


def format_chat_message(role: str, content: str) -> None:
    if role == "user":
        st.markdown(
            f"<div class='chat-card user-card'><div class='bubble'><strong>You</strong><p>{content}</p></div></div>",
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            f"<div class='chat-card agent-card'><div class='bubble'><strong>SHL Agent</strong><p>{content}</p></div></div>",
            unsafe_allow_html=True,
        )


def call_backend_chat(messages, backend_url):
    url = urljoin(backend_url.rstrip("/"), "/chat")
    payload = {"messages": messages}
    response = requests.post(url, json=payload, timeout=20)
    response.raise_for_status()
    return response.json()


def call_backend_ingest(uploaded_file, backend_url):
    url = urljoin(backend_url.rstrip("/"), "/ingest")
    files = {"file": (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type)}
    response = requests.post(url, files=files, timeout=30)
    response.raise_for_status()
    return response.json()


st.markdown(
    """
    <style>
    .main-container {padding: 0 40px 40px 40px;}
    .page-title {font-size: clamp(42px, 4vw, 56px); font-weight: 800; margin-bottom: 0.2rem;}
    .subtitle {color: #adb5bd; margin-top: 0; margin-bottom: 1.4rem; max-width: 760px;}
    .tool-chip {display:inline-block; background:#eef4ff; color:#0f62fe; padding:10px 16px; border-radius:999px; margin:4px 6px 4px 0; cursor:pointer; font-size:14px;}
    .tool-chip:hover {background:#d9e8ff;}
    .chat-card {margin: 10px 0; display: flex;}
    .bubble {padding: 18px 20px; border-radius: 22px; max-width: 100%; line-height: 1.6;}
    .user-card {justify-content: flex-end;}
    .user-card .bubble {background: linear-gradient(135deg, #dbeafe, #e0f2fe); border-radius: 22px 22px 8px 22px;}
    .agent-card .bubble {background: #f8fafc; border-radius: 22px 22px 22px 8px; border: 1px solid #e2e8f0;}
    .upload-panel {background:#ffffff; border:1px solid #e5e7eb; border-radius:20px; padding:18px; margin-bottom:18px;}
    .upload-button {background:#0f62fe; color:white; padding:12px 18px; border-radius:999px; border:none; font-weight:700; cursor:pointer;}
    .upload-button:hover {background:#0958d9;}
    .recommendation-card {background:#ffffff; padding:18px; border-radius:18px; border:1px solid #e3e8ff; margin-bottom:16px; box-shadow: 0 14px 30px rgba(15,98,254,0.05);}    
    .recommendation-card a {color:#0f62fe; text-decoration:none;}
    .recommendation-tag {display:inline-block; background:#0f62fe; color:white; padding:5px 12px; border-radius:999px; font-size:12px; margin-bottom:12px;}
    .sidebar-title {font-size:18px; font-weight:600; margin-bottom:8px;}
    .page-banner {background: linear-gradient(135deg, rgba(15,98,254,0.13), rgba(15,98,254,0)); border-radius: 24px; padding: 24px 30px; margin-bottom: 20px;}
    .banner-pill {display:inline-flex; align-items:center; gap:8px; background:#e7f0ff; color:#053d9a; padding:8px 14px; border-radius:999px; font-weight:600; margin-bottom:12px;}
    .header-meta {color:#57606a; margin-top:0.5rem;}
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    """
    <div class='main-container'>
      <div class='page-banner'>
        <div class='banner-pill'>🧠 SHL Navigator</div>
        <h1 class='page-title'>SHL Assessment Navigator</h1>
        <p class='subtitle'>Use AI-guided recommendations to find the best SHL personality and leadership assessment for your hiring or development need.</p>
      </div>
    </div>
    """,
    unsafe_allow_html=True,
)

with st.sidebar:
    st.markdown("## Interface Settings")
    st.text_input("Backend URL", key="backend_url")
    st.markdown(f"**Active backend:** {st.session_state.backend_url}")
    st.markdown("---")
    st.markdown("## Conversation tools")
    if st.session_state.chat_history:
        st.download_button(
            label="Download chat history",
            data=chat_history_json(),
            file_name="shl_chat_history.json",
            mime="application/json",
        )
        if st.button("Clear conversation", key="clear_history"):
            reset_conversation()
            st.experimental_rerun()
    else:
        st.info("Start a chat or upload a file to unlock conversation tools.")
    st.markdown("---")
    st.markdown("## Quick prompts")
    st.markdown(
        "- *I need an SHL test for a senior sales leader.*\n"
        "- *Recommend an assessment for a technical manager role.*\n"
        "- *What personality and leadership tools fit this hiring need?*"
    )
    st.markdown("---")
    if st.button("Reset conversation", key="reset_sidebar"):
        reset_conversation()
        st.experimental_rerun()

with st.expander("How this works", expanded=False):
    st.write(
        "This Streamlit UI sends your request to the SHL assessment backend at `/chat`. "
        "The backend returns a conversational reply and a shortlist of SHL recommendation links. "
        "If your app is deployed separately from the backend, set the Backend URL accordingly."
    )

main_col, recommend_col = st.columns([3, 1])

with main_col:
    st.markdown("### Start the conversation")
    bottom_bar = st.columns([0.12, 0.68, 0.2])
    with bottom_bar[0]:
        if st.button("+", key="upload_toggle", help="Upload files or past conversation traces"):
            toggle_upload_panel()
    with bottom_bar[1]:
        user_input = st.text_area(
            "Describe your hiring or assessment need",
            height=180,
            placeholder="Example: I need an SHL assessment for a mid-level HR business partner role.",
            key="user_input",
        )
    with bottom_bar[2]:
        submit = st.button("Ask SHL Agent", type="primary")

    st.markdown("#### Need inspiration?")
    prompt_cols = st.columns(3)
    prompts = [
        "I need a senior leadership assessment for a finance director.",
        "Recommend a personality test for a customer success manager.",
        "What SHL tools help with talent development in operations?",
    ]
    for prompt_text, prompt_col in zip(prompts, prompt_cols):
        if prompt_col.button(prompt_text, key=prompt_text):
            st.session_state.user_input = prompt_text
            st.experimental_rerun()

    if st.session_state.show_upload_panel:
        with st.container():
            st.markdown("<div class='upload-panel'><strong>Upload a resume, job brief, or conversation trace</strong></div>", unsafe_allow_html=True)
            st.markdown("Supported file types: `.txt`, `.md`, `.json`, `.pdf` — plain text is best for job briefs and conversation traces.")
            st.markdown("If your document includes candidate background, role requirements, or assessment needs, upload it here and the agent will use it as context.")
            uploaded_file = st.file_uploader("Choose a file", type=["txt", "md", "json", "pdf"], accept_multiple_files=False)
            if uploaded_file is not None:
                if uploaded_file.type == "application/pdf":
                    st.warning("PDF upload is accepted, but only text-based parsing is supported. Plain-text job briefs and markdown traces work best.")
                try:
                    with st.spinner("Uploading file and extracting content..."):
                        ingest_response = call_backend_ingest(uploaded_file, st.session_state.backend_url)
                    messages = ingest_response.get("messages", [])
                    if messages:
                        st.session_state.messages.extend(messages)
                        st.session_state.chat_history.append(("user", f"Uploaded file: {uploaded_file.name}"))
                        st.session_state.last_uploaded_file = uploaded_file.name
                        st.success(f"Uploaded {uploaded_file.name} and added {len(messages)} messages to the chat history.")
                    else:
                        st.error("The uploaded file did not contain recognized chat traces or messages.")
                except requests.HTTPError as http_err:
                    st.error(f"Upload failed: {http_err}")
                except Exception as exc:
                    st.error(f"Unable to upload file to backend at {st.session_state.backend_url}. {exc}")

    if submit and user_input.strip():
        st.session_state.messages.append({"role": "user", "content": user_input.strip()})
        try:
            with st.spinner("Connecting to backend and generating recommendations..."):
                result = call_backend_chat(st.session_state.messages, st.session_state.backend_url)

            st.session_state.chat_history.append(("user", user_input.strip()))
            st.session_state.chat_history.append(("assistant", result.get("reply", "")))
            st.session_state.recommendations = result.get("recommendations", [])
            if result.get("end_of_conversation"):
                st.success("This looks like a completed recommendation cycle.")
        except requests.HTTPError as http_err:
            st.error(f"Backend error: {http_err}")
        except Exception as exc:
            st.error(f"Unable to reach backend at {st.session_state.backend_url}. {exc}")

    if st.session_state.last_uploaded_file:
        st.info(f"Latest upload: {st.session_state.last_uploaded_file}")

    if st.session_state.chat_history:
        st.markdown("### Conversation")
        for role, content in st.session_state.chat_history:
            format_chat_message(role, content)

with recommend_col:
    st.markdown("### Recommendations")
    if not st.session_state.recommendations:
        st.info("Submit a request to see tailored SHL recommendations here.")
    else:
        for item in st.session_state.recommendations:
            url = item.get("url")
            test_type = item.get("test_type", "-")
            name = item.get("name", "Unnamed assessment")
            score_line = item.get("score") if item.get("score") else None
            st.markdown(
                f"<div class='recommendation-card'>"
                f"<span class='recommendation-tag'>{test_type}</span>"
                f"<strong>{name}</strong><br>"
                f"<a href='{url}' target='_blank'>Open SHL details</a>"
                f"</div>",
                unsafe_allow_html=True,
            )
            if score_line:
                st.write(f"Score indicator: {score_line}")

st.markdown("---")
st.write(
    "Need help deploying? Run the Python backend with `uvicorn main:app --reload` and then start Streamlit by running `streamlit run streamlit_app.py`. "
    "For Render, use separate services or set `BACKEND_URL` to your backend service URL."
)
