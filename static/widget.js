// Floating chat widget — injected on every page

(function () {
  // ── DOM injection ──────────────────────────────────────────────────────────

  const fabHTML = `
    <button id="chatFab" class="chat-fab" aria-label="Open transportation assistant">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"
           stroke-linecap="round" stroke-linejoin="round">
        <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
      </svg>
    </button>

    <div id="chatWidget" class="chat-widget" aria-hidden="true" role="dialog" aria-label="Transportation Assistant">
      <div class="chat-widget-header">
        <div class="chat-widget-title">
          <span class="chat-widget-avatar" aria-hidden="true">T</span>
          <span>Transportation Assistant</span>
        </div>
        <button id="closeChatWidget" class="chat-widget-close" aria-label="Close chat">✕</button>
      </div>
      <div class="chat-widget-messages" id="widgetMessages">
        <div class="message bot">
          <div class="avatar">T</div>
          <div class="bubble">Ask me when a bus, train, or UMass shuttle is coming. I can also find the closest stop and open directions on the map.</div>
        </div>
      </div>
      <div class="chat-widget-footer">
        <form class="chat-widget-form" id="widgetForm">
          <label class="sr-only" for="widgetInput">Ask a transportation question</label>
          <input type="text" id="widgetInput" placeholder="Ask about a stop or route…" autocomplete="off" aria-label="Ask a transportation question" />
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

  function renderMarkdown(text) {
    if (typeof marked === "undefined") return escapeHtml(text);
    const html = marked.parse(text);
    return typeof DOMPurify !== "undefined"
      ? DOMPurify.sanitize(html, { USE_PROFILES: { html: true } })
      : escapeHtml(text);
  }

  function addUserMsg(text) {
    const row = document.createElement("div");
    row.className = "message user";
    row.innerHTML = `<div class="bubble">${escapeHtml(text)}</div>`;
    messagesEl.appendChild(row);
    scrollBottom();
  }

  const PIPELINE_STEPS = [
    "🧠 Embedding your query…",
    "🔍 Searching BM25 keyword index…",
    "📊 Searching FAISS vector index…",
    "⚖️  Ranking with RRF fusion…",
    "📄 Building context from top chunks…",
    "🤖 Sending context to Gemini…",
    "⚡ Generating response…",
  ];

  function createBotBubble() {
    const row = document.createElement("div");
    row.className = "message bot";
    row.innerHTML = `
      <div class="avatar">T</div>
      <div class="bot-content">
        <div class="pipeline-status"></div>
        <div class="bubble">
          <div class="typing-dots"><span></span><span></span><span></span></div>
        </div>
      </div>`;
    messagesEl.appendChild(row);
    scrollBottom();

    const statusEl = row.querySelector(".pipeline-status");
    let stepIdx = 0;
    statusEl.textContent = PIPELINE_STEPS[0];
    statusEl.style.display = "";

    const cycleTimer = setInterval(() => {
      stepIdx++;
      if (stepIdx >= PIPELINE_STEPS.length) {
        clearInterval(cycleTimer);
        return;
      }
      statusEl.textContent = PIPELINE_STEPS[stepIdx];
      scrollBottom();
    }, 700);

    return {
      bubble: row.querySelector(".bubble"),
      status: statusEl,
      stopCycle: () => clearInterval(cycleTimer),
    };
  }

  function renderSources(sources) {
    if (!sources || sources.length === 0) return null;
    const el = document.createElement("div");
    el.className = "sources";
    el.innerHTML = `<span class="sources-label">Sources:</span>`;
    for (const s of sources) {
      if (!s || !/^https?:\/\//i.test(s.url || "")) continue;
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

  function isLiveTransitQuestion(text) {
    const q = text.toLowerCase();
    return /bus|train|subway|mbta|shuttle|route|line|umass/.test(q) &&
      /when|next|arriv|depart|soon|live|schedule|what time|nearest|closest|how long|until|come/.test(q);
  }

  function requestLocation() {
    return new Promise((resolve) => {
      if (!navigator.geolocation) return resolve(null);
      navigator.geolocation.getCurrentPosition(
        (pos) => {
          const location = { latitude: pos.coords.latitude, longitude: pos.coords.longitude };
          window.dispatchEvent(new CustomEvent("transit:location", { detail: location }));
          resolve(location);
        },
        () => resolve(null),
        { enableHighAccuracy: true, maximumAge: 60000, timeout: 10000 }
      );
    });
  }

  function addLocationNotice() {
    if (messagesEl.querySelector(".location-notice")) return;
    const row = document.createElement("div");
    row.className = "message bot location-notice";
    row.innerHTML = '<div class="avatar" aria-hidden="true">T</div><div class="bubble"><strong>Location helps me choose the closest stop.</strong><br>Allow location access when your browser asks. If you decline, I’ll ask you for a stop name instead.</div>';
    messagesEl.appendChild(row);
    scrollBottom();
  }

  function addTransitContext(transit) {
    if (!transit?.stop) return null;
    const el = document.createElement("div");
    el.className = "transit-context";
    const distance = transit.distance_miles != null ? ` · ${transit.distance_miles} mi away` : "";
    el.innerHTML = `<span class="transit-context-dot" aria-hidden="true"></span><span><strong>Checking ${escapeHtml(transit.stop)}</strong>${distance}<small>Map opened to this stop${transit.checked_at ? ` · updated ${escapeHtml(transit.checked_at)}` : ""}</small></span>`;
    return el;
  }

  function addQuickReplies(options) {
    const row = document.createElement("div");
    row.className = "quick-replies";
    options.forEach((label) => {
      const button = document.createElement("button");
      button.type = "button";
      button.className = "quick-reply";
      button.textContent = label;
      button.addEventListener("click", () => {
        row.remove();
        send(label);
      });
      row.appendChild(button);
    });
    messagesEl.appendChild(row);
    scrollBottom();
  }

  function destinationFromText(text) {
    const q = text.toLowerCase();
    if (/campus center/.test(q) && /direction|walk|route|get to|how do i get/.test(q)) {
      return "campus-center";
    }
    return null;
  }

  async function send(text) {
    addUserMsg(text);
    history.push({ role: "user", content: text });
    setEnabled(false);

    const needsLocation = isLiveTransitQuestion(text) || Boolean(destinationFromText(text));
    if (needsLocation) addLocationNotice();
    const { bubble, status, stopCycle } = createBotBubble();
    let accumulated = "";
    let sourcesEl = null;
    let transitContext = null;
    let cycleRunning = true;

    try {
      const destinationId = destinationFromText(text);
      const location = (isLiveTransitQuestion(text) || destinationId) ? await requestLocation() : null;
      if (destinationId) {
        window.dispatchEvent(new CustomEvent("transit:directions", {
          detail: { destinationId, location },
        }));
      }
      const res = await fetch(`${window.API_BASE || ""}/api/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: text, history: history.slice(-12), location }),
      });

      if (!res.ok) {
        bubble.textContent = res.status === 429
          ? "Too many requests right now. Please wait a moment and try again."
          : res.status === 413
            ? "That message is too long. Please shorten it and try again."
            : "Server error. Please try again.";
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

          if (evt.type === "status") {
            // server status events ignored — client cycle handles this
          } else if (evt.type === "token") {
            if (cycleRunning) { stopCycle(); cycleRunning = false; }
            status.style.display = "none";
            accumulated += evt.text;
            bubble.querySelector(".typing-dots")?.remove();
            bubble.innerHTML = renderMarkdown(accumulated);
            scrollBottom();
          } else if (evt.type === "done") {
            sourcesEl = renderSources(evt.sources);
          } else if (evt.type === "map_focus") {
            transitContext = addTransitContext(evt.transit);
            window.dispatchEvent(new CustomEvent("transit:focus-stop", {
              detail: { stopId: evt.stop_id, stop: evt.stop || null, transit: evt.transit || null },
            }));
          }
        }
      }

      const finalMd = renderMarkdown(accumulated || "_(no response)_");
      bubble.innerHTML = finalMd;
      if (transitContext) bubble.parentElement.parentElement.insertAdjacentElement("afterend", transitContext);
      if (sourcesEl) bubble.parentElement.parentElement.insertAdjacentElement("afterend", sourcesEl);
      const lower = accumulated.toLowerCase();
      if (lower.includes("inbound or outbound")) {
        addQuickReplies(["Mt. Vernon inbound", "Mt. Vernon outbound"]);
      }
      history.push({ role: "assistant", content: accumulated });

    } catch (err) {
      if (cycleRunning) { stopCycle(); cycleRunning = false; }
      status.style.display = "none";
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
