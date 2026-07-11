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


def format_chat_message(role: str, content: str) -> None:
    if role == "user":
        st.markdown(f"<div class='user-message'><strong>You:</strong> {content}</div>", unsafe_allow_html=True)
    else:
        st.markdown(f"<div class='agent-message'><strong>Agent:</strong> {content}</div>", unsafe_allow_html=True)


def call_backend_chat(messages, backend_url):
    url = urljoin(backend_url.rstrip("/"), "/chat")
    payload = {"messages": messages}
    response = requests.post(url, json=payload, timeout=20)
    response.raise_for_status()
    return response.json()


st.markdown(
    """
    <style>
    .page-title {font-size: 42px; font-weight: 700; margin-bottom: 0.25rem;}
    .subtitle {color: #6c757d; margin-top: 0; margin-bottom: 1rem;}
    .user-message {background:#eaf4ff; padding:16px; border-radius:14px; margin:10px 0;}
    .agent-message {background:#f8f9fa; padding:16px; border-radius:14px; margin:10px 0;}
    .recommendation-card {background:linear-gradient(180deg, #ffffff 0%, #f2f8ff 100%); padding:18px; border-radius:18px; border:1px solid #e3e8ff; margin-bottom:16px;}
    .recommendation-card a {color:#0f62fe; text-decoration:none;}
    .recommendation-tag {display:inline-block; background:#0f62fe; color:white; padding:4px 10px; border-radius:999px; font-size:12px; margin-right:8px;}
    .sidebar-title {font-size:18px; font-weight:600; margin-bottom:8px;}
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("SHL Assessment Navigator")
st.write("Use AI-guided assessment recommendations for SHL personality and leadership hiring cases.")

with st.sidebar:
    st.markdown("## Interface Settings")
    st.text_input("Backend URL", key="backend_url")
    st.markdown(f"**Active backend:** {st.session_state.backend_url}")
    st.markdown("---")
    st.markdown("## Quick prompts")
    st.markdown(
        "- *I need an SHL test for a senior sales leader.*\n"
        "- *Recommend an assessment for a technical manager role.*\n"
        "- *What personality and leadership tools fit this hiring need?*"
    )
    st.markdown("---")
    if st.button("Reset conversation"):
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
    user_input = st.text_area("Describe your hiring or assessment need", height=180, placeholder="Example: I need an SHL assessment for a mid-level HR business partner role.")
    submit = st.button("Ask SHL Agent")

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
