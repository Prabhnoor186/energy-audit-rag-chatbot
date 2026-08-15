import streamlit as st
import requests
 
API_ENDPOINT = "https://rons8aus36.execute-api.eu-north-1.amazonaws.com/ask"
 
st.set_page_config(page_title="Energy Audit Chatbot", layout="centered")
st.title("Energy Audit RAG Chatbot")
st.caption("Ask questions about the compressor and boiler energy audit reports.")
 
if "messages" not in st.session_state:
    st.session_state.messages = []
 
if "pending_question" not in st.session_state:
    st.session_state.pending_question = None
 
 
def clean_preview(text: str, max_chars: int = 260) -> str:
    """Trim to a whole sentence/word boundary instead of cutting mid-word."""
    text = " ".join(text.split())  # collapse extra whitespace/newlines/bullets
    if len(text) <= max_chars:
        return text
    trimmed = text[:max_chars]
    last_space = trimmed.rfind(" ")
    if last_space > 0:
        trimmed = trimmed[:last_space]
    return trimmed.rstrip(",.;:") + "..."
 
 
def score_label(score: float) -> str:
    if score >= 0.75:
        return "Strong match"
    elif score >= 0.5:
        return "Moderate match"
    return "Weak match"
 
 
def render_message(msg):
    with st.chat_message(msg["role"]):
        st.write(msg["content"])
        sources = msg.get("sources")
        if sources:
            with st.expander(f"View retrieved context ({len(sources)} sources)"):
                for s in sources:
                    with st.container(border=True):
                        col1, col2 = st.columns([3, 1])
                        col1.markdown(f"**{s['source'].replace('_', ' ').title()}**  \n{s['section']}")
                        col2.markdown(f"<div style='text-align:right; color:#9ca3af; font-size:0.85em;'>{score_label(s['score'])}</div>", unsafe_allow_html=True)
                        st.caption(clean_preview(s["chunk_text"]))
 
 
def ask_and_store(question: str):
    st.session_state.messages.append({"role": "user", "content": question})
    try:
        response = requests.post(API_ENDPOINT, json={"question": question}, timeout=30)
        data = response.json()
        answer = data.get("answer", "Something went wrong - no answer returned.")
        sources = data.get("sources", [])
        st.session_state.messages.append({"role": "assistant", "content": answer, "sources": sources})
    except Exception as e:
        error_msg = f"Error contacting the chatbot API: {e}"
        st.session_state.messages.append({"role": "assistant", "content": error_msg})
 
 
if not st.session_state.messages:
    st.write("**Try asking:**")
    sample_questions = [
        "What is the rated power of the compressor?",
        "What methodology was used for the audits?",
        "What fuel does the boiler use?",
        "What is the price of a new industrial boiler?",
    ]
    cols = st.columns(2)
    for i, q in enumerate(sample_questions):
        if cols[i % 2].button(q, use_container_width=True):
            st.session_state.pending_question = q
 
if st.session_state.pending_question:
    q = st.session_state.pending_question
    st.session_state.pending_question = None
    with st.spinner("Thinking..."):
        ask_and_store(q)
 
typed_question = st.chat_input("Ask a question about the audit reports...")
if typed_question:
    with st.spinner("Thinking..."):
        ask_and_store(typed_question)
 
for msg in st.session_state.messages:
    render_message(msg)
 