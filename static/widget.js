// Floating chat widget — injected on every page

(function () {
  // ── DOM injection ──────────────────────────────────────────────────────────

  const fabHTML = `
    <button id="chatFab" class="chat-fab" aria-label="Open parking assistant">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"
           stroke-linecap="round" stroke-linejoin="round">
        <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
      </svg>
    </button>

    <div id="chatWidget" class="chat-widget" aria-hidden="true">
      <div class="chat-widget-header">
        <div class="chat-widget-title">
          <span class="chat-widget-avatar">P</span>
          <span>Parking Assistant</span>
        </div>
        <button id="closeChatWidget" class="chat-widget-close" aria-label="Close chat">✕</button>
      </div>
      <div class="chat-widget-messages" id="widgetMessages">
        <div class="message bot">
          <div class="avatar">P</div>
          <div class="bubble">Hi! Ask me about parking permits, rates, fines, shuttles, or commuting options at UMass Boston.</div>
        </div>
      </div>
      <div class="chat-widget-footer">
        <form class="chat-widget-form" id="widgetForm">
          <input type="text" id="widgetInput" placeholder="Ask about parking…" autocomplete="off" />
          <button type="submit" id="widgetSendBtn" aria-label="Send">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2"
                 stroke-linecap="round" stroke-linejoin="round">
              <line x1="22" y1="2" x2="11" y2="13"/>
              <polygon points="22 2 15 22 11 13 2 9 22 2"/>
            </svg>
          </button>
        </form>
      </div>
    </div>`;

  const container = document.createElement("div");
  container.innerHTML = fabHTML;
  document.body.appendChild(container);

  // ── State ──────────────────────────────────────────────────────────────────

  const fab        = document.getElementById("chatFab");
  const widget     = document.getElementById("chatWidget");
  const closeBtn   = document.getElementById("closeChatWidget");
  const form       = document.getElementById("widgetForm");
  const input      = document.getElementById("widgetInput");
  const sendBtn    = document.getElementById("widgetSendBtn");
  const messagesEl = document.getElementById("widgetMessages");

  const history = [];
  const header  = widget.querySelector(".chat-widget-header");

  // ── Drag ───────────────────────────────────────────────────────────────────

  let dragging = false, dragX = 0, dragY = 0;

  header.addEventListener("mousedown", (e) => {
    if (e.target === closeBtn) return;
    dragging = true;
    const rect = widget.getBoundingClientRect();
    // Switch from bottom/right to top/left so we can freely position
    widget.style.bottom = "auto";
    widget.style.right  = "auto";
    widget.style.top    = rect.top + "px";
    widget.style.left   = rect.left + "px";
    dragX = e.clientX - rect.left;
    dragY = e.clientY - rect.top;
    widget.classList.add("dragging");
    e.preventDefault();
  });

  document.addEventListener("mousemove", (e) => {
    if (!dragging) return;
    const maxLeft = window.innerWidth  - widget.offsetWidth;
    const maxTop  = window.innerHeight - widget.offsetHeight;
    widget.style.left = Math.min(Math.max(0, e.clientX - dragX), maxLeft) + "px";
    widget.style.top  = Math.min(Math.max(0, e.clientY - dragY), maxTop)  + "px";
  });

  document.addEventListener("mouseup", () => {
    if (dragging) { dragging = false; widget.classList.remove("dragging"); }
  });

  const BADGE_CLASS = {
    permits:     "badge-permits",
    enforcement: "badge-enforcement",
    transit:     "badge-transit",
    visitor:     "badge-visitor",
    general:     "badge-general",
  };

  // ── Toggle ─────────────────────────────────────────────────────────────────

  fab.addEventListener("click", () => {
    const open = widget.classList.toggle("open");
    widget.setAttribute("aria-hidden", String(!open));
    fab.classList.toggle("hide", open);
    if (open) setTimeout(() => input.focus(), 280);
  });

  closeBtn.addEventListener("click", () => {
    widget.classList.remove("open");
    widget.setAttribute("aria-hidden", "true");
    fab.classList.remove("hide");
  });

  // ── Helpers ────────────────────────────────────────────────────────────────

  function scrollBottom() {
    messagesEl.scrollTop = messagesEl.scrollHeight;
  }

  function escapeHtml(str) {
    return str.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  }

  function addUserMsg(text) {
    const row = document.createElement("div");
    row.className = "message user";
    row.innerHTML = `<div class="bubble">${escapeHtml(text)}</div>`;
    messagesEl.appendChild(row);
    scrollBottom();
  }

  function createBotBubble() {
    const row = document.createElement("div");
    row.className = "message bot";
    row.innerHTML = `
      <div class="avatar">P</div>
      <div class="bubble">
        <div class="typing-dots"><span></span><span></span><span></span></div>
      </div>`;
    messagesEl.appendChild(row);
    scrollBottom();
    return row.querySelector(".bubble");
  }

  function renderSources(sources) {
    if (!sources || sources.length === 0) return null;
    const el = document.createElement("div");
    el.className = "sources";
    el.innerHTML = `<span class="sources-label">Sources:</span>`;
    for (const s of sources) {
      const cls = BADGE_CLASS[s.category] || "badge-general";
      const a = document.createElement("a");
      a.className = `badge ${cls}`;
      a.href = s.url;
      a.target = "_blank";
      a.rel = "noopener noreferrer";
      a.textContent = s.title;
      el.appendChild(a);
    }
    return el;
  }

  function setEnabled(on) {
    input.disabled  = !on;
    sendBtn.disabled = !on;
    if (on) input.focus();
  }

  // ── Send message ───────────────────────────────────────────────────────────

  async function send(text) {
    addUserMsg(text);
    history.push({ role: "user", content: text });
    setEnabled(false);

    const bubble = createBotBubble();
    let accumulated = "";
    let sourcesEl = null;

    try {
      const res = await fetch(`${window.API_BASE || ""}/api/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: text, history: history.slice(-12) }),
      });

      if (!res.ok) {
        bubble.textContent = "Server error. Please try again.";
        setEnabled(true);
        return;
      }

      const reader  = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop();

        for (const line of lines) {
          if (!line.startsWith("data: ")) continue;
          let evt;
          try { evt = JSON.parse(line.slice(6)); } catch { continue; }

          if (evt.type === "token") {
            accumulated += evt.text;
            const md = typeof marked !== "undefined" ? marked.parse(accumulated) : escapeHtml(accumulated);
            bubble.innerHTML = md;
            scrollBottom();
          } else if (evt.type === "done") {
            sourcesEl = renderSources(evt.sources);
          }
        }
      }

      const finalMd = typeof marked !== "undefined"
        ? marked.parse(accumulated || "_(no response)_")
        : escapeHtml(accumulated || "(no response)");
      bubble.innerHTML = finalMd;
      if (sourcesEl) bubble.parentElement.insertAdjacentElement("afterend", sourcesEl);
      history.push({ role: "assistant", content: accumulated });

    } catch (err) {
      bubble.textContent = "Connection error. Is the server running?";
      console.error(err);
    }

    scrollBottom();
    setEnabled(true);
  }

  form.addEventListener("submit", (e) => {
    e.preventDefault();
    const text = input.value.trim();
    if (!text) return;
    input.value = "";
    send(text);
  });
})();
