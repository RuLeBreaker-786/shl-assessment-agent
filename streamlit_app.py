import json
import os
from datetime import datetime
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
st.session_state.setdefault("last_uploaded_file", "")
st.session_state.setdefault("user_input", "")
st.session_state.setdefault("show_file_uploader", False)
st.session_state.setdefault("saved_conversations", [])


if "messages" not in st.session_state:
    st.session_state.messages = []

if "recommendations" not in st.session_state:
    st.session_state.recommendations = []


def archive_current_conversation():
    if st.session_state.messages:
        session_name = f"Session {len(st.session_state.saved_conversations) + 1}"
        st.session_state.saved_conversations.append(
            {
                "name": session_name,
                "created_at": datetime.utcnow().isoformat() + "Z",
                "messages": [m.copy() for m in st.session_state.messages],
            }
        )


def reset_conversation():
    st.session_state.messages = []
    st.session_state.recommendations = []
    st.session_state.last_uploaded_file = ""
    st.session_state.user_input = ""
    st.session_state.show_file_uploader = False


def restore_conversation(index: int):
    session = st.session_state.saved_conversations[index]
    st.session_state.messages = [m.copy() for m in session["messages"]]
    st.session_state.recommendations = []
    st.session_state.user_input = ""
    st.session_state.last_uploaded_file = ""
    st.session_state.show_file_uploader = False


def new_conversation():
    if st.session_state.messages:
        archive_current_conversation()
    reset_conversation()


def safe_rerun():
    """Attempt to rerun the Streamlit script; silently no-op if not available."""
    try:
        # older/newer streamlit variations — guard against absence
        if hasattr(st, "experimental_rerun"):
            st.experimental_rerun()
        elif hasattr(st, "rerun"):
            st.rerun()
    except Exception:
        # If rerun isn't supported in the running environment (e.g. Render runtime), ignore
        pass
def chat_history_json() -> str:
    return json.dumps({"messages": st.session_state.messages}, indent=2)

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

def render_chat_messages(messages):
    for msg in messages:
        format_chat_message(msg.get("role", "user"), msg.get("content", ""))


def conversation_json_payload(messages):
    return json.dumps({"messages": messages}, indent=2)


def call_backend_chat(messages, backend_url):
    url = urljoin(backend_url.rstrip("/"), "/chat")
    payload = {"messages": messages}
    response = requests.post(url, json=payload, timeout=20)
    response.raise_for_status()
    return response.json()


def call_backend_ingest(uploaded_file, backend_url):
    url = urljoin(backend_url.rstrip("/"), "/ingest")
    content_type = uploaded_file.type or "application/octet-stream"
    files = {"file": (uploaded_file.name, uploaded_file.getvalue(), content_type)}
    response = requests.post(url, files=files, timeout=30)
    response.raise_for_status()
    return response.json()


st.markdown(
    """
    <style>
    .main-container {padding: 0 40px 40px 40px;}
    .page-title {font-size: clamp(42px, 4vw, 56px); font-weight: 800; margin-bottom: 0.2rem;}
    .subtitle {color: #adb5bd; margin-top: 0; margin-bottom: 1.4rem; max-width: 760px;}
    .page-title {font-size: 32px; font-weight: 800; margin-bottom: 0.4rem;}
    .subtitle {color: #4b5563; margin-top: 0; margin-bottom: 1rem; max-width: 680px;}
    .search-panel {background: rgba(255,255,255,.96); border-radius: 28px; padding: 24px; box-shadow: 0 22px 44px rgba(15,23,42,0.08);}
    .search-row {display: flex; gap: 14px; align-items: flex-start;}
    .search-plus-button {width: 54px; height: 54px; border-radius: 50%; background: #0f62fe; color: white; font-size: 26px; font-weight: 700; border: none; display: flex; align-items: center; justify-content: center; cursor: pointer;}
    .search-note {color: #6b7280; margin-top: 12px;}
    .search-textarea textarea {border-radius: 32px !important; padding: 22px 24px !important; min-height: 160px !important; border: 1px solid #d1d5db !important; box-shadow: none !important;}
    .search-button button {background: #0f62fe !important; color: white !important; border-radius: 999px !important; padding: 16px 28px !important; font-weight: 700 !important;}
    .chat-history-panel {margin-top: 24px;}
    .chat-card {display: flex; margin-bottom: 16px;}
    .chat-card .bubble {padding: 18px 20px; border-radius: 22px; max-width: 100%; line-height: 1.6;}
    .user-card {justify-content: flex-end;}
    .user-card .bubble {background: linear-gradient(135deg, #dbeafe, #e0f2fe); border-radius: 22px 22px 8px 22px;}
    .agent-card .bubble {background: #f8fafc; border-radius: 22px 22px 22px 8px; border: 1px solid #e2e8f0;}
    .recommendation-card {background:#ffffff; padding:18px; border-radius:18px; border:1px solid #e3e8ff; margin-bottom:16px; box-shadow: 0 10px 30px rgba(15,98,254,0.08);}    
    .recommendation-card a {color:#0f62fe; text-decoration:none;}
    .recommendation-tag {display:inline-block; background:#0f62fe; color:white; padding:5px 12px; border-radius:999px; font-size:12px; margin-bottom:12px;}
    .sidebar-section {margin-bottom: 24px;}
    .sidebar-title {font-size:18px; font-weight:700; margin-bottom:12px;}
    .sidebar-panel {background: #ffffff; border:1px solid #e5e7eb; border-radius: 18px; padding: 18px;}
    .sidebar-link {color:#0f62fe; text-decoration:none;}
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown(
        """
        <div class='main-container'>
            <h1 class='page-title'>SHL Assessment Navigator</h1>
            <p class='subtitle'>Use AI-guided recommendations to find the best SHL personality and leadership assessment for your hiring or development need.</p>
        </div>
        """,
        unsafe_allow_html=True,
)

with st.sidebar:
    st.markdown("<div class='sidebar-section'><div class='sidebar-title'>Interface Settings</div></div>", unsafe_allow_html=True)
    st.text_input("Backend URL", key="backend_url")
    backend_health = "Unknown"
    try:
        health_resp = requests.get(urljoin(st.session_state.backend_url.rstrip("/"), "/health"), timeout=2)
        backend_health = "Online" if health_resp.status_code == 200 else f"Error {health_resp.status_code}"
    except Exception:
        backend_health = "Unavailable"
    st.markdown(
        f"**Active backend:** <a class='sidebar-link' href='{st.session_state.backend_url}' target='_blank'>{st.session_state.backend_url}</a><br>"
        f"**Status:** {backend_health}",
        unsafe_allow_html=True,
    )

    st.markdown("<div class='sidebar-section'><div class='sidebar-title'>Conversation sessions</div><div class='sidebar-panel'>", unsafe_allow_html=True)
    if st.button("Start new conversation", key="new_conversation"):
        new_conversation()
        safe_rerun()

    if st.session_state.messages:
        st.download_button(
            label="Download current conversation",
            data=chat_history_json(),
            file_name="shl_conversation_current.json",
            mime="application/json",
        )

    if st.session_state.saved_conversations:
        st.markdown("### Saved sessions")
        for index, session in enumerate(st.session_state.saved_conversations, 1):
            st.markdown(f"**{session['name']}**")
            st.write(f"Created: {session['created_at']}")
            restore_key = f"restore_saved_{index}"
            if st.button(f"Restore {session['name']}", key=restore_key):
                restore_conversation(index - 1)
                safe_rerun()
            st.download_button(
                label=f"Download {session['name']}",
                data=json.dumps(session, indent=2),
                file_name=f"{session['name'].replace(' ', '_').lower()}.json",
                mime="application/json",
                key=f"download_saved_{index}",
            )
    else:
        st.write("No saved sessions yet. Start a conversation and click New Conversation to archive it.")

    if st.button("Clear conversation", key="clear_history"):
        reset_conversation()
        safe_rerun()
    st.markdown("</div></div>", unsafe_allow_html=True)

    st.markdown("<div class='sidebar-section'><div class='sidebar-title'>Quick prompts</div><div class='sidebar-panel'>", unsafe_allow_html=True)
    if st.button("Senior leadership assessment", key="prompt_1"):
        st.session_state.user_input = "I need a senior leadership assessment for a finance director."
        safe_rerun()
    if st.button("Personality test for customer success", key="prompt_2"):
        st.session_state.user_input = "Recommend a personality test for a customer success manager."
        safe_rerun()
    if st.button("Talent development tools", key="prompt_3"):
        st.session_state.user_input = "What SHL tools help with talent development in operations?"
        safe_rerun()
    st.markdown("</div></div>", unsafe_allow_html=True)

    st.markdown("<div class='sidebar-section'><div class='sidebar-title'>Help</div><div class='sidebar-panel'>", unsafe_allow_html=True)
    st.write(
        "This app connects to your backend `/chat` endpoint and recommends SHL assessments based on your brief. "
        "Use the sidebar for settings, conversation tools, and prompts."
    )
    if st.button("Reset conversation", key="reset_sidebar"):
        reset_conversation()
        safe_rerun()
    st.markdown("</div></div>", unsafe_allow_html=True)

    st.write("\n")

    st.markdown("<div class='sidebar-section'><div class='sidebar-title'>How this works</div><div class='sidebar-panel'>", unsafe_allow_html=True)
    st.write(
        "This Streamlit UI sends your request to the SHL assessment backend at `/chat`. "
        "The backend returns a conversational reply and a shortlist of SHL recommendation links. "
        "If your app is deployed separately from the backend, set the Backend URL accordingly."
    )
    st.markdown("</div></div>", unsafe_allow_html=True)

main_col, recommend_col = st.columns([3, 1])

with main_col:
    st.markdown("<div class='search-panel'>", unsafe_allow_html=True)
    st.markdown("<h2>Ask the SHL Agent</h2>", unsafe_allow_html=True)
    row_cols = st.columns([0.08, 0.92])
    with row_cols[0]:
        if st.button("+", key="search_plus", help="Open upload controls in the search panel"):
            st.session_state.show_file_uploader = not st.session_state.show_file_uploader
            safe_rerun()
    with row_cols[1]:
        user_input = st.text_area(
            "Describe your hiring or assessment need",
            height=180,
            placeholder="Example: I need an SHL assessment for a mid-level HR business partner role.",
            key="user_input",
            label_visibility="collapsed",
        )
    submit = st.button("Ask SHL Agent", type="primary")
    if st.session_state.show_file_uploader:
        st.markdown("<div class='search-note'>Upload any file directly here. The app accepts text, markdown, JSON, PDF, DOCX, and other text-based files.</div>", unsafe_allow_html=True)
        with st.container():
            uploaded_file = st.file_uploader(
                "Upload file for SHL assessment context",
                type=None,
                accept_multiple_files=False,
                key="floating_upload",
            )
            if uploaded_file is not None:
                if uploaded_file.type == "application/pdf":
                    st.warning("PDF upload is accepted, but only text-based parsing is supported.")
                elif not uploaded_file.type:
                    st.info("Uploaded file type is unknown. The backend will attempt text extraction if possible.")
                try:
                    with st.spinner("Uploading file and extracting content..."):
                        ingest_response = call_backend_ingest(uploaded_file, st.session_state.backend_url)
                    if ingest_response.get("error"):
                        st.error(ingest_response.get("error"))
                    else:
                        messages = ingest_response.get("messages", [])
                        if messages:
                            st.session_state.messages.extend(messages)
                            st.session_state.last_uploaded_file = uploaded_file.name
                            st.success(f"Uploaded {uploaded_file.name} and added {len(messages)} messages to the chat history.")
                        else:
                            st.error("The uploaded file did not contain recognized chat traces or messages.")
                except requests.HTTPError as http_err:
                    st.error(f"Upload failed: {http_err}")
                except Exception as exc:
                    st.error(f"Unable to upload file to backend at {st.session_state.backend_url}. {exc}")
    if st.session_state.last_uploaded_file:
        st.caption(f"Last upload: {st.session_state.last_uploaded_file}")
    st.markdown("</div>", unsafe_allow_html=True)

    if submit and user_input.strip():
        st.session_state.messages.append({"role": "user", "content": user_input.strip()})
        assistant_placeholder = st.empty()
        assistant_placeholder.info("SHL Agent is thinking...")
        try:
            result = call_backend_chat(st.session_state.messages, st.session_state.backend_url)
            assistant_placeholder.empty()

            st.session_state.messages.append({"role": "assistant", "content": result.get("reply", "")})
            st.session_state.recommendations = result.get("recommendations", [])
            if result.get("end_of_conversation"):
                st.success("This looks like a completed recommendation cycle.")
        except requests.HTTPError as http_err:
            assistant_placeholder.empty()
            st.error(f"Backend error: {http_err}")
        except Exception as exc:
            assistant_placeholder.empty()
            st.error(f"Unable to reach backend at {st.session_state.backend_url}. {exc}")

    if st.session_state.messages:
        st.markdown("<div class='chat-history-panel'>", unsafe_allow_html=True)
        render_chat_messages(st.session_state.messages)
        st.markdown("</div>", unsafe_allow_html=True)

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
