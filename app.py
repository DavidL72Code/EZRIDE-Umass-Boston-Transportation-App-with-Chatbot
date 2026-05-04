import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import streamlit as st
from dotenv import load_dotenv

load_dotenv()

# ── Page config (must be the very first Streamlit call) ───────────────────────
st.set_page_config(
    page_title="UMass Boston Recycling Assistant",
    page_icon="https://www.umb.edu/favicon.ico",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── UMass Boston CSS theme ────────────────────────────────────────────────────
st.markdown(
    """
<style>
html, body, [data-testid="stAppViewContainer"] { background-color: #f4f6f9; }

/* Header */
.umb-header {
    display: flex; align-items: center; gap: 14px;
    background: linear-gradient(135deg, #003087 0%, #00509e 100%);
    color: #fff; padding: 18px 28px; border-radius: 10px;
    margin-bottom: 18px; box-shadow: 0 4px 12px rgba(0,48,135,.25);
}
.umb-header img { height: 48px; border-radius: 4px; }
.umb-header h1 { margin: 0; font-size: 1.45rem; font-weight: 700; color: #fff; }
.umb-header p  { margin: 3px 0 0; font-size: .82rem; color: #d0e0ff; }

/* Sidebar */
[data-testid="stSidebar"] { background: #002266 !important; }
[data-testid="stSidebar"] * { color: #e8eef8 !important; }
[data-testid="stSidebar"] h2 {
    color: #fff !important; font-size: 1rem;
    border-bottom: 1px solid #1a4080; padding-bottom: 6px; margin-bottom: 12px;
}
[data-testid="stSidebar"] .stButton > button {
    background: #1a4080; color: #fff; border: none;
    border-radius: 6px; width: 100%; font-size: .85rem;
}
[data-testid="stSidebar"] .stButton > button:hover { background: #0057b8; }

/* Chat bubbles */
.chat-user { display: flex; justify-content: flex-end; margin: 8px 0; }
.chat-user .bubble {
    background: #003087; color: #fff; padding: 10px 16px;
    border-radius: 18px 18px 4px 18px; max-width: 72%;
    font-size: .92rem; line-height: 1.5;
    box-shadow: 0 2px 6px rgba(0,48,135,.2);
}
.chat-bot { display: flex; align-items: flex-start; gap: 10px; margin: 8px 0; }
.chat-bot .avatar {
    width: 34px; height: 34px; border-radius: 50%; background: #003087;
    display: flex; align-items: center; justify-content: center;
    font-size: 16px; flex-shrink: 0;
}
.chat-bot .bubble {
    background: #fff; color: #1a1a2e; padding: 10px 16px;
    border-radius: 4px 18px 18px 18px; max-width: 78%;
    font-size: .92rem; line-height: 1.6;
    border: 1px solid #dce6f7; box-shadow: 0 2px 6px rgba(0,0,0,.07);
}

/* Source badges */
.source-section { margin-top: 6px; padding-left: 44px; }
.src-badge {
    display: inline-block; margin: 2px 4px 2px 0;
    padding: 3px 9px; border-radius: 12px;
    font-size: .73rem; font-weight: 600;
    text-decoration: none !important;
}
.badge-materials     { background:#e8f4e8; color:#1a6b1a; border:1px solid #a8d8a8; }
.badge-locations     { background:#e8f0ff; color:#1a3d8a; border:1px solid #a8c0f0; }
.badge-programs      { background:#fff3e0; color:#8a4500; border:1px solid #ffc580; }
.badge-composting    { background:#f3ffe0; color:#3d6600; border:1px solid #b8e870; }
.badge-sustainability{ background:#e0f7f7; color:#006666; border:1px solid #80d8d8; }
.badge-general       { background:#f0f0f0; color:#444;    border:1px solid #ccc;    }

/* Setup notice */
.setup-box {
    background:#fff8e1; border:1px solid #ffcc02; border-radius:8px;
    padding:18px 22px; margin:20px 0;
}
.setup-box h3 { color:#7a4f00; margin-top:0; }

/* Text input */
.stTextInput input, [data-testid="stChatInput"] textarea {
    border: 2px solid #ccd9f0 !important;
    border-radius: 24px !important;
}
[data-testid="stChatInput"] textarea:focus,
.stTextInput input:focus { border-color: #003087 !important; }

/* Footer */
.umb-footer {
    text-align:center; font-size:.75rem; color:#888;
    margin-top:30px; padding-top:12px; border-top:1px solid #dde3ee;
}
</style>
""",
    unsafe_allow_html=True,
)

# ── Constants ─────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).parent
BM25_DIR = BASE_DIR / "index" / "bm25"
FAISS_DIR = BASE_DIR / "index" / "faiss"

CATEGORY_OPTIONS = {
    "All Categories": None,
    "♻️  Materials": "materials",
    "📍  Locations": "locations",
    "📋  Programs": "programs",
    "🌱  Composting": "composting",
    "🌍  Sustainability": "sustainability",
    "ℹ️  General": "general",
}

BADGE_CLASS = {
    "materials": "badge-materials",
    "locations": "badge-locations",
    "programs": "badge-programs",
    "composting": "badge-composting",
    "sustainability": "badge-sustainability",
    "general": "badge-general",
}


# ── Helper functions ──────────────────────────────────────────────────────────
def render_sources(chunks: list[dict]) -> None:
    seen: set[str] = set()
    html = ""
    for item in chunks:
        c = item["chunk"]
        url = c.get("source_url", "")
        cat = c.get("category", "general")
        title = (c.get("title") or url or "Source")[:48]
        if url and url not in seen:
            seen.add(url)
            cls = BADGE_CLASS.get(cat, "badge-general")
            html += f'<a class="src-badge {cls}" href="{url}" target="_blank">{title}</a>'
    if html:
        st.markdown(
            f'<div class="source-section"><b>Sources:</b> {html}</div>',
            unsafe_allow_html=True,
        )


def render_message(msg: dict) -> None:
    if msg["role"] == "user":
        st.markdown(
            f'<div class="chat-user"><div class="bubble">{msg["content"]}</div></div>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            f'<div class="chat-bot">'
            f'<div class="avatar">♻️</div>'
            f'<div class="bubble">{msg["content"]}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )
        if msg.get("sources"):
            render_sources(msg["sources"])


# ── Cached resource loaders ───────────────────────────────────────────────────
@st.cache_resource(show_spinner="Loading search indexes…")
def load_retriever(sem_w: float):
    from src.indexing.embedder import Embedder
    from src.retrieval.retriever import HybridRetriever
    return HybridRetriever(BM25_DIR, FAISS_DIR, Embedder(), semantic_weight=sem_w)


@st.cache_resource(show_spinner="Loading language model…")
def load_llm():
    key = os.getenv("GOOGLE_API_KEY", "")
    if not key:
        return None
    try:
        from src.llm.gemini_llm import GeminiLLM
        return GeminiLLM(api_key=key)
    except Exception:
        return None


# ── Header ────────────────────────────────────────────────────────────────────
st.markdown(
    """
<div class="umb-header">
  <img src="https://www.umb.edu/favicon.ico" alt="UMass Boston logo">
  <div>
    <h1>UMass Boston Recycling Assistant</h1>
    <p>Ask about recycling, composting, and sustainability on campus.</p>
  </div>
</div>
""",
    unsafe_allow_html=True,
)

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## ⚙️ Search Options")

    cat_label = st.selectbox("Category filter", list(CATEGORY_OPTIONS.keys()))
    category = CATEGORY_OPTIONS[cat_label]

    top_k = st.slider("Results to retrieve", 3, 10, 5)

    sem_weight = st.slider(
        "Semantic ↔ Keyword",
        0.0, 1.0, 0.6, 0.05,
        help="Left = pure BM25 keyword · Right = pure all-MiniLM semantic",
    )

    st.markdown("---")
    if st.button("🗑️ Clear conversation"):
        st.session_state.messages = []
        st.rerun()

    st.markdown(
        "<small>Search: <b>BM25</b> + <b>all-MiniLM-L6-v2</b><br>"
        "LLM: <b>Google Gemini</b></small>",
        unsafe_allow_html=True,
    )

# ── Setup gate ────────────────────────────────────────────────────────────────
indexes_ready = (BM25_DIR / "global.pkl").exists() and (FAISS_DIR / "global_meta.json").exists()

if not indexes_ready:
    st.markdown(
        """
<div class="setup-box">
<h3>⚙️ Setup Required</h3>
<p>No search indexes found. Run the pipeline first:</p>
<pre>pip install -r requirements.txt
python scripts/build_pipeline.py</pre>
<p>This scrapes UMass Boston sustainability pages, chunks the content,
and builds BM25 + FAISS indexes in the <code>index/</code> folder.</p>
</div>
""",
        unsafe_allow_html=True,
    )
    st.stop()

# ── Load components ───────────────────────────────────────────────────────────
retriever = load_retriever(sem_weight)
llm = load_llm()

if llm is None:
    st.warning(
        "**Gemini API key not set.** "
        "Add `GOOGLE_API_KEY=your_key` to a `.env` file and restart. "
        "Search results will still be shown.",
        icon="⚠️",
    )

# ── Session state ─────────────────────────────────────────────────────────────
if "messages" not in st.session_state:
    st.session_state.messages = []

# ── Render existing conversation ──────────────────────────────────────────────
for msg in st.session_state.messages:
    render_message(msg)

# ── Chat input ────────────────────────────────────────────────────────────────
query = st.chat_input("Ask about recycling, composting, or sustainability at UMass Boston…")

if query:
    st.session_state.messages.append({"role": "user", "content": query})

    results = retriever.search(query, top_k=top_k, category=category)

    if not results:
        answer = (
            "I couldn't find specific information about that. "
            "Try rephrasing your question or visit "
            "[umb.edu/sustainability](https://www.umb.edu/sustainability/) directly."
        )
        st.session_state.messages.append({"role": "assistant", "content": answer, "sources": []})

    elif llm is not None:
        history = [
            {"role": m["role"], "content": m["content"]}
            for m in st.session_state.messages[:-1]
            if m["role"] in ("user", "assistant")
        ]
        with st.spinner("Generating answer…"):
            try:
                answer = llm.answer(query, results, history=history[-6:])
            except Exception as exc:
                answer = f"_(Gemini error: {exc})_\n\nHere are the most relevant sources:"
        st.session_state.messages.append({"role": "assistant", "content": answer, "sources": results})

    else:
        # No LLM — surface raw chunks
        parts = []
        for i, item in enumerate(results, 1):
            c = item["chunk"]
            snippet = c["text"][:320].rsplit(" ", 1)[0] + "…"
            parts.append(
                f"**[{i}] {c.get('title', 'Source')}** "
                f"— *{c.get('category', '').title()}*\n\n{snippet}"
            )
        answer = "\n\n---\n\n".join(parts)
        st.session_state.messages.append({"role": "assistant", "content": answer, "sources": results})

    st.rerun()

# ── Footer ────────────────────────────────────────────────────────────────────
st.markdown(
    '<div class="umb-footer">'
    "UMass Boston Recycling Assistant · "
    'Data from <a href="https://www.umb.edu/sustainability/" target="_blank">umb.edu/sustainability</a>'
    "</div>",
    unsafe_allow_html=True,
)
