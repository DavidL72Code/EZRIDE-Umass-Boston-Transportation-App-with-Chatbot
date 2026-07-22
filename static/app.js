const messagesEl = document.getElementById("messages");
const inputForm  = document.getElementById("inputForm");
const userInput  = document.getElementById("userInput");
const sendBtn    = document.getElementById("sendBtn");
const chatWindow = document.getElementById("chatWindow");

// In-memory history for multi-turn context (role + content only)
const history = [];

const BADGE_CLASS = {
  permits:    "badge-permits",
  enforcement:"badge-enforcement",
  transit:    "badge-transit",
  visitor:    "badge-visitor",
  general:    "badge-general",
};

function scrollToBottom() {
  chatWindow.scrollTop = chatWindow.scrollHeight;
}

function addUserMessage(text) {
  const row = document.createElement("div");
  row.className = "message user";
  row.innerHTML = `<div class="bubble">${escapeHtml(text)}</div>`;
  messagesEl.appendChild(row);
  scrollToBottom();
}

function createBotRow() {
  const row = document.createElement("div");
  row.className = "message bot";
  row.innerHTML = `
    <div class="avatar">P</div>
    <div class="bubble">
      <div class="typing-dots">
        <span></span><span></span><span></span>
      </div>
    </div>`;
  messagesEl.appendChild(row);
  scrollToBottom();
  return row.querySelector(".bubble");
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

function escapeHtml(str) {
  return str
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
}

function renderMarkdown(text) {
  if (typeof marked === "undefined") return escapeHtml(text);
  const html = marked.parse(text);
  return typeof DOMPurify !== "undefined"
    ? DOMPurify.sanitize(html, { USE_PROFILES: { html: true } })
    : escapeHtml(text);
}

function setInputEnabled(enabled) {
  userInput.disabled = !enabled;
  sendBtn.disabled   = !enabled;
  if (enabled) userInput.focus();
}

function isLiveTransitQuestion(text) {
  const q = text.toLowerCase();
  return /bus|train|subway|mbta|shuttle|route|line|umass/.test(q) &&
    /when|next|arriv|depart|soon|live|schedule|what time|nearest|closest|how long|until|come/.test(q);
}

function requestLocation() {
  return new Promise((resolve) => {
    if (!navigator.geolocation) return resolve(null);
    navigator.geolocation.getCurrentPosition(
      (pos) => resolve({ latitude: pos.coords.latitude, longitude: pos.coords.longitude }),
      () => resolve(null),
      { enableHighAccuracy: true, maximumAge: 60000, timeout: 10000 }
    );
  });
}

function isDirectionsQuestion(text) {
  const q = text.toLowerCase();
  return /direction|walk|route|get to|how do i get/.test(q) && /campus center/.test(q);
}

async function sendMessage(text) {
  addUserMessage(text);
  history.push({ role: "user", content: text });

  setInputEnabled(false);
  const bubble = createBotRow();

  let accumulated = "";
  let sourcesEl = null;

  try {
    const location = (isLiveTransitQuestion(text) || isDirectionsQuestion(text)) ? await requestLocation() : null;
    const res = await fetch("/api/chat", {
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
      setInputEnabled(true);
      return;
    }

    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n");
      buffer = lines.pop(); // last incomplete line stays in buffer

      for (const line of lines) {
        if (!line.startsWith("data: ")) continue;
        let evt;
        try { evt = JSON.parse(line.slice(6)); } catch { continue; }

        if (evt.type === "token") {
          accumulated += evt.text;
          bubble.innerHTML = renderMarkdown(accumulated);
          scrollToBottom();
        } else if (evt.type === "done") {
          sourcesEl = renderSources(evt.sources);
        }
      }
    }

    // Final render pass
    bubble.innerHTML = renderMarkdown(accumulated || "_(no response)_");
    if (sourcesEl) bubble.parentElement.insertAdjacentElement("afterend", sourcesEl);
    history.push({ role: "assistant", content: accumulated });

  } catch (err) {
    bubble.textContent = "Connection error. Is the server running?";
    console.error(err);
  }

  scrollToBottom();
  setInputEnabled(true);
}

inputForm.addEventListener("submit", (e) => {
  e.preventDefault();
  const text = userInput.value.trim();
  if (!text) return;
  userInput.value = "";
  sendMessage(text);
});
